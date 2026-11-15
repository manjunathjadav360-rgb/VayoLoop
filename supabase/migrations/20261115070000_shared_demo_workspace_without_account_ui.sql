-- The original authenticated care-circle schema remains available for a future
-- private, account-based release. The public hackathon app uses these separate
-- tables so it can persist synthetic demo records without a login interface.
create table if not exists public.vayoloop_demo_health_observations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null default '00000000-0000-4000-8000-000000000001',
  metric text not null check (length(metric) between 1 and 120),
  value numeric not null,
  unit text not null default '',
  observed_at timestamptz not null,
  source text not null default 'Entered by user',
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint vayoloop_demo_health_workspace_fixed
    check (workspace_id = '00000000-0000-4000-8000-000000000001')
);
create index if not exists vayoloop_demo_health_timeline_idx
  on public.vayoloop_demo_health_observations (workspace_id, metric, observed_at desc);

create table if not exists public.vayoloop_demo_prescriptions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null default '00000000-0000-4000-8000-000000000001',
  title text not null check (length(title) between 1 and 180),
  clinician_name text,
  prescribed_on date,
  document_path text not null,
  review_status text not null default 'pending_review',
  clinic_name text,
  condition_as_written text,
  notes text,
  original_file_name text not null,
  file_content_type text not null,
  file_size_bytes bigint not null check (file_size_bytes between 1 and 10485760),
  created_at timestamptz not null default now(),
  constraint vayoloop_demo_prescription_workspace_fixed
    check (workspace_id = '00000000-0000-4000-8000-000000000001')
);
create index if not exists vayoloop_demo_prescriptions_timeline_idx
  on public.vayoloop_demo_prescriptions (workspace_id, created_at desc);

alter table public.vayoloop_demo_health_observations enable row level security;
alter table public.vayoloop_demo_prescriptions enable row level security;
grant select, insert, delete on public.vayoloop_demo_health_observations to anon, authenticated;
grant select, insert, delete on public.vayoloop_demo_prescriptions to anon, authenticated;

drop policy if exists "Public VayoLoop demo reads health observations" on public.vayoloop_demo_health_observations;
create policy "Public VayoLoop demo reads health observations" on public.vayoloop_demo_health_observations
  for select to anon, authenticated using (workspace_id = '00000000-0000-4000-8000-000000000001');
drop policy if exists "Public VayoLoop demo adds health observations" on public.vayoloop_demo_health_observations;
create policy "Public VayoLoop demo adds health observations" on public.vayoloop_demo_health_observations
  for insert to anon, authenticated with check (workspace_id = '00000000-0000-4000-8000-000000000001');
drop policy if exists "Public VayoLoop demo deletes health observations" on public.vayoloop_demo_health_observations;
create policy "Public VayoLoop demo deletes health observations" on public.vayoloop_demo_health_observations
  for delete to anon, authenticated using (workspace_id = '00000000-0000-4000-8000-000000000001');

drop policy if exists "Public VayoLoop demo reads prescriptions" on public.vayoloop_demo_prescriptions;
create policy "Public VayoLoop demo reads prescriptions" on public.vayoloop_demo_prescriptions
  for select to anon, authenticated using (workspace_id = '00000000-0000-4000-8000-000000000001');
drop policy if exists "Public VayoLoop demo adds prescriptions" on public.vayoloop_demo_prescriptions;
create policy "Public VayoLoop demo adds prescriptions" on public.vayoloop_demo_prescriptions
  for insert to anon, authenticated with check (workspace_id = '00000000-0000-4000-8000-000000000001');
drop policy if exists "Public VayoLoop demo deletes prescriptions" on public.vayoloop_demo_prescriptions;
create policy "Public VayoLoop demo deletes prescriptions" on public.vayoloop_demo_prescriptions
  for delete to anon, authenticated using (workspace_id = '00000000-0000-4000-8000-000000000001');

drop policy if exists "Public VayoLoop demo reads prescription files" on storage.objects;
create policy "Public VayoLoop demo reads prescription files" on storage.objects
  for select to anon, authenticated using (
    bucket_id = 'vayoloop-prescriptions'
    and (storage.foldername(name))[1] = '00000000-0000-4000-8000-000000000001'
  );
drop policy if exists "Public VayoLoop demo uploads prescription files" on storage.objects;
create policy "Public VayoLoop demo uploads prescription files" on storage.objects
  for insert to anon, authenticated with check (
    bucket_id = 'vayoloop-prescriptions'
    and (storage.foldername(name))[1] = '00000000-0000-4000-8000-000000000001'
  );
drop policy if exists "Public VayoLoop demo deletes prescription files" on storage.objects;
create policy "Public VayoLoop demo deletes prescription files" on storage.objects
  for delete to anon, authenticated using (
    bucket_id = 'vayoloop-prescriptions'
    and (storage.foldername(name))[1] = '00000000-0000-4000-8000-000000000001'
  );
