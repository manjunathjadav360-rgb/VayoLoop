alter table public.prescription_records
  add column if not exists clinic_name text,
  add column if not exists condition_as_written text,
  add column if not exists notes text,
  add column if not exists original_file_name text,
  add column if not exists file_content_type text,
  add column if not exists file_size_bytes bigint;

create index if not exists health_observations_elder_metric_observed_idx
  on public.health_observations (elder_id, metric, observed_at desc);

create index if not exists prescription_records_elder_created_idx
  on public.prescription_records (elder_id, created_at desc);

grant select, insert, update, delete on public.prescription_records to authenticated;
grant select, insert, update on public.health_observations to authenticated;
grant select, insert, update on public.elder_profiles to authenticated;
grant select on public.care_memberships to authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'vayoloop-prescriptions',
  'vayoloop-prescriptions',
  false,
  10485760,
  array['application/pdf', 'image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = excluded.allowed_mime_types;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage'
      and tablename = 'objects'
      and policyname = 'VayoLoop care circle reads prescription files'
  ) then
    create policy "VayoLoop care circle reads prescription files"
      on storage.objects for select
      to authenticated
      using (
        bucket_id = 'vayoloop-prescriptions'
        and exists (
          select 1
          from public.care_memberships cm
          where cm.elder_id::text = (storage.foldername(name))[1]
            and cm.user_id = (select auth.uid())
            and cm.role = any (array['owner','elder','caregiver','family']::text[])
        )
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage'
      and tablename = 'objects'
      and policyname = 'VayoLoop care team uploads prescription files'
  ) then
    create policy "VayoLoop care team uploads prescription files"
      on storage.objects for insert
      to authenticated
      with check (
        bucket_id = 'vayoloop-prescriptions'
        and exists (
          select 1
          from public.care_memberships cm
          where cm.elder_id::text = (storage.foldername(name))[1]
            and cm.user_id = (select auth.uid())
            and cm.role = any (array['owner','elder','caregiver']::text[])
        )
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage'
      and tablename = 'objects'
      and policyname = 'VayoLoop care team deletes prescription files'
  ) then
    create policy "VayoLoop care team deletes prescription files"
      on storage.objects for delete
      to authenticated
      using (
        bucket_id = 'vayoloop-prescriptions'
        and exists (
          select 1
          from public.care_memberships cm
          where cm.elder_id::text = (storage.foldername(name))[1]
            and cm.user_id = (select auth.uid())
            and cm.role = any (array['owner','elder','caregiver']::text[])
        )
      );
  end if;
end
$$;
