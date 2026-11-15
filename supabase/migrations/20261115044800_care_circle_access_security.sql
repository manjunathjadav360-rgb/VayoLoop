-- VayoLoop care-circle security and access controls
-- Apply after the initial care schema and connected-living device foundation.

alter table public.care_invitations add column if not exists revoked_at timestamptz;
alter table public.care_invitations drop constraint if exists care_invitations_role_check;
alter table public.care_invitations
  add constraint care_invitations_role_check
  check (role = any (array['elder','caregiver','family','viewer']::text[]));

create unique index if not exists care_memberships_elder_user_unique
  on public.care_memberships(elder_id,user_id);
create unique index if not exists care_memberships_one_elder_per_profile
  on public.care_memberships(elder_id) where role='elder';

drop policy if exists "Owners manage invitations" on public.care_invitations;
create policy "Owners and elders read invitations"
  on public.care_invitations for select to authenticated
  using (private.is_care_member(elder_id,array['owner','elder']));

drop policy if exists "Owners manage memberships" on public.care_memberships;

drop policy if exists "care members add connected devices" on public.connected_devices;
drop policy if exists "care members update connected devices" on public.connected_devices;
create policy "owners caregivers register connected devices"
  on public.connected_devices for insert to authenticated
  with check (
    private.is_care_member(elder_id,array['owner','elder','caregiver'])
    and consent_granted_by=(select auth.uid())
  );
create policy "owners caregivers update connected devices"
  on public.connected_devices for update to authenticated
  using (private.is_care_member(elder_id,array['owner','elder','caregiver']))
  with check (private.is_care_member(elder_id,array['owner','elder','caregiver']));

drop policy if exists "care members add device readings" on public.device_readings;
create policy "authorized care members add device readings"
  on public.device_readings for insert to authenticated
  with check (private.is_care_member(elder_id,array['owner','elder','caregiver']));

drop policy if exists "care members add device events" on public.connected_device_events;
drop policy if exists "care members update device events" on public.connected_device_events;
create policy "authorized care members add device events"
  on public.connected_device_events for insert to authenticated
  with check (private.is_care_member(elder_id,array['owner','elder','caregiver']));
create policy "authorized care members update device events"
  on public.connected_device_events for update to authenticated
  using (private.is_care_member(elder_id,array['owner','elder','caregiver']))
  with check (private.is_care_member(elder_id,array['owner','elder','caregiver']));

drop policy if exists "Care members update care events" on public.care_events;
create policy "Authorized members update care events"
  on public.care_events for update to authenticated
  using (private.is_care_member(elder_id,array['owner','elder','caregiver']))
  with check (private.is_care_member(elder_id,array['owner','elder','caregiver']));

create or replace function private.create_care_invitation_impl(
  p_elder_id uuid,p_invited_email text,p_role text,p_expires_in_hours integer default 72
)
returns table(invitation_id uuid,invite_code text,expires_at timestamptz,invited_email text,invited_role text)
language plpgsql security definer set search_path=''
as $function$
declare
  v_user_id uuid:=auth.uid();
  v_email text:=lower(btrim(coalesce(p_invited_email,'')));
  v_code text;
  v_hash text;
  v_hours integer:=coalesce(p_expires_in_hours,72);
begin
  if v_user_id is null then raise exception 'Authentication required'; end if;
  if not exists(select 1 from public.care_memberships cm
    where cm.elder_id=p_elder_id and cm.user_id=v_user_id and cm.role in ('owner','elder')) then
    raise exception 'Only the elder or profile owner can invite care-circle members';
  end if;
  if v_email='' or length(v_email)>254 or v_email !~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$' then
    raise exception 'Enter a valid email address';
  end if;
  if p_role is null or p_role not in ('elder','caregiver','family','viewer') then raise exception 'Invalid invitation role'; end if;
  if v_hours<1 or v_hours>168 then raise exception 'Invitation expiry must be between 1 and 168 hours'; end if;
  if p_role='elder' and exists(select 1 from public.care_memberships cm where cm.elder_id=p_elder_id and cm.role='elder') then
    raise exception 'This care profile already has an elder account';
  end if;
  v_code:=encode(extensions.gen_random_bytes(32),'hex');
  v_hash:=encode(extensions.digest(convert_to(v_code,'UTF8'),'sha256'),'hex');
  return query
    insert into public.care_invitations as ci(elder_id,invited_email,role,invite_code_hash,expires_at,created_by)
    values(p_elder_id,v_email,p_role,v_hash,now()+make_interval(hours=>v_hours),v_user_id)
    returning ci.id,v_code,ci.expires_at,ci.invited_email,ci.role;
end;
$function$;

create or replace function private.accept_care_invitation_impl(p_invite_code text)
returns table(elder_id uuid,membership_id uuid,member_role text)
language plpgsql security definer set search_path=''
as $function$
declare
  v_user_id uuid:=auth.uid();
  v_email text;
  v_hash text;
  v_invite public.care_invitations%rowtype;
  v_membership_id uuid;
begin
  if v_user_id is null then raise exception 'Authentication required'; end if;
  if p_invite_code is null or length(p_invite_code)<>64 or p_invite_code !~ '^[0-9a-fA-F]{64}$' then
    raise exception 'Invalid or expired invitation';
  end if;
  select lower(u.email) into v_email from auth.users u
    where u.id=v_user_id and u.email_confirmed_at is not null;
  if v_email is null then raise exception 'Verify the email address on your account before accepting an invitation'; end if;
  v_hash:=encode(extensions.digest(convert_to(lower(p_invite_code),'UTF8'),'sha256'),'hex');
  select ci.* into v_invite from public.care_invitations ci where ci.invite_code_hash=v_hash for update;
  if not found or v_invite.accepted_at is not null or v_invite.revoked_at is not null or v_invite.expires_at<=now() then
    raise exception 'Invalid or expired invitation';
  end if;
  if lower(v_invite.invited_email)<>v_email then raise exception 'This invitation was issued to a different email address'; end if;
  if exists(select 1 from public.care_memberships cm where cm.elder_id=v_invite.elder_id and cm.user_id=v_user_id) then
    raise exception 'This account is already a member of the care circle';
  end if;
  if v_invite.role='elder' and exists(select 1 from public.care_memberships cm where cm.elder_id=v_invite.elder_id and cm.role='elder') then
    raise exception 'This care profile already has an elder account';
  end if;
  insert into public.care_memberships(elder_id,user_id,role,permissions)
  values(v_invite.elder_id,v_user_id,v_invite.role,
    case v_invite.role
      when 'elder' then '{"medications.read":true,"medications.write":true,"appointments.read":true,"appointments.write":true,"health.read":true,"health.write":true,"care_events.read":true,"devices.read":true,"devices.write":true}'::jsonb
      when 'caregiver' then '{"medications.read":true,"medications.write":true,"appointments.read":true,"appointments.write":true,"health.read":true,"health.write":true,"care_events.read":true,"devices.read":true,"devices.write":true}'::jsonb
      when 'family' then '{"medications.read":true,"medications.write":false,"appointments.read":true,"appointments.write":false,"health.read":true,"health.write":false,"care_events.read":true,"devices.read":true,"devices.write":false}'::jsonb
      else '{"medications.read":true,"medications.write":false,"appointments.read":false,"appointments.write":false,"health.read":false,"health.write":false,"care_events.read":false,"devices.read":false,"devices.write":false}'::jsonb
    end
  ) returning id into v_membership_id;
  update public.care_invitations set accepted_at=now(),accepted_by=v_user_id where id=v_invite.id;
  return query select v_invite.elder_id,v_membership_id,v_invite.role;
end;
$function$;

create or replace function private.revoke_care_invitation_impl(p_invitation_id uuid)
returns boolean language plpgsql security definer set search_path=''
as $function$
declare v_user_id uuid:=auth.uid(); v_updated integer;
begin
  if v_user_id is null then raise exception 'Authentication required'; end if;
  update public.care_invitations ci set revoked_at=now()
  where ci.id=p_invitation_id and ci.accepted_at is null and ci.revoked_at is null
    and exists(select 1 from public.care_memberships cm
      where cm.elder_id=ci.elder_id and cm.user_id=v_user_id and cm.role in ('owner','elder'));
  get diagnostics v_updated=row_count;
  return v_updated=1;
end;
$function$;

create or replace function private.remove_care_member_impl(p_membership_id uuid)
returns boolean language plpgsql security definer set search_path=''
as $function$
declare
  v_user_id uuid:=auth.uid();
  v_target public.care_memberships%rowtype;
  v_actor_role text;
begin
  if v_user_id is null then raise exception 'Authentication required'; end if;
  select cm.* into v_target from public.care_memberships cm where cm.id=p_membership_id for update;
  if not found then return false; end if;
  select cm.role into v_actor_role from public.care_memberships cm
    where cm.elder_id=v_target.elder_id and cm.user_id=v_user_id;
  if v_target.user_id=v_user_id then
    if v_target.role='owner' then raise exception 'The profile owner cannot remove their own access'; end if;
  elsif v_actor_role not in ('owner','elder') then
    raise exception 'Only the elder or profile owner can remove another member';
  end if;
  if v_target.role='owner' then raise exception 'The profile owner cannot be removed'; end if;
  if v_target.role='elder' and v_target.user_id<>v_user_id then raise exception 'Only the elder can remove their own elder access'; end if;
  delete from public.care_memberships where id=p_membership_id;
  return true;
end;
$function$;

grant usage on schema private to authenticated;
revoke all on function private.create_care_invitation_impl(uuid,text,text,integer) from public,anon,authenticated;
revoke all on function private.accept_care_invitation_impl(text) from public,anon,authenticated;
revoke all on function private.revoke_care_invitation_impl(uuid) from public,anon,authenticated;
revoke all on function private.remove_care_member_impl(uuid) from public,anon,authenticated;
grant execute on function private.create_care_invitation_impl(uuid,text,text,integer) to authenticated;
grant execute on function private.accept_care_invitation_impl(text) to authenticated;
grant execute on function private.revoke_care_invitation_impl(uuid) to authenticated;
grant execute on function private.remove_care_member_impl(uuid) to authenticated;

create or replace function public.create_care_invitation(p_elder_id uuid,p_invited_email text,p_role text,p_expires_in_hours integer default 72)
returns table(invitation_id uuid,invite_code text,expires_at timestamptz,invited_email text,invited_role text)
language sql security invoker set search_path=''
as $function$ select * from private.create_care_invitation_impl($1,$2,$3,$4); $function$;
create or replace function public.accept_care_invitation(p_invite_code text)
returns table(elder_id uuid,membership_id uuid,member_role text)
language sql security invoker set search_path=''
as $function$ select * from private.accept_care_invitation_impl($1); $function$;
create or replace function public.revoke_care_invitation(p_invitation_id uuid)
returns boolean language sql security invoker set search_path=''
as $function$ select private.revoke_care_invitation_impl($1); $function$;
create or replace function public.remove_care_member(p_membership_id uuid)
returns boolean language sql security invoker set search_path=''
as $function$ select private.remove_care_member_impl($1); $function$;

revoke all on function public.create_care_invitation(uuid,text,text,integer) from public,anon,authenticated;
revoke all on function public.accept_care_invitation(text) from public,anon,authenticated;
revoke all on function public.revoke_care_invitation(uuid) from public,anon,authenticated;
revoke all on function public.remove_care_member(uuid) from public,anon,authenticated;
grant execute on function public.create_care_invitation(uuid,text,text,integer) to authenticated;
grant execute on function public.accept_care_invitation(text) to authenticated;
grant execute on function public.revoke_care_invitation(uuid) to authenticated;
grant execute on function public.remove_care_member(uuid) to authenticated;

revoke all on all tables in schema public from anon;
revoke all on public.profiles,public.elder_profiles,public.care_memberships,public.care_invitations,
  public.medications,public.dose_events,public.appointments,public.health_observations,
  public.prescription_records,public.prescription_flags,public.care_events,
  public.notification_preferences,public.connected_devices,public.device_readings,
  public.connected_device_events from authenticated;
grant select,insert,update on public.profiles,public.elder_profiles to authenticated;
grant select on public.care_memberships to authenticated;
grant select(id,elder_id,invited_email,role,expires_at,accepted_at,accepted_by,created_by,created_at,revoked_at)
  on public.care_invitations to authenticated;
grant select,insert,update on public.medications,public.dose_events,public.appointments,
  public.health_observations,public.prescription_records,public.prescription_flags,
  public.care_events,public.notification_preferences,public.connected_devices,
  public.connected_device_events to authenticated;
grant select,insert on public.device_readings to authenticated;
