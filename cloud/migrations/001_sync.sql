-- Run as project owner in Supabase SQL Editor. Clients use only publishable keys.
begin;
create table if not exists public.journal_records (
  owner_id uuid not null references auth.users(id) on delete cascade,
  id uuid not null,
  kind text not null check (kind in ('travel','ticket','food','movie','book')),
  data jsonb not null default '{}'::jsonb check (jsonb_typeof(data) = 'object'),
  deleted boolean not null default false,
  revision bigint not null default 1 check (revision > 0),
  updated_at timestamptz not null default now(),
  primary key (owner_id, id),
  check (octet_length(data::text) <= 5242880)
);
alter table public.journal_records enable row level security;
revoke all on public.journal_records from anon, authenticated;
grant select on public.journal_records to authenticated;
drop policy if exists own_records on public.journal_records;
create policy own_records on public.journal_records for select to authenticated
  using (owner_id = (select auth.uid()));

-- Writes only through compare-and-swap. No client-supplied owner or timestamp.
create or replace function public.put_journal_record(
  record_id uuid, record_kind text, payload jsonb,
  expected_revision bigint, is_deleted boolean default false
) returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  who uuid := auth.uid();
  item public.journal_records;
begin
  if who is null then raise exception 'Authentication required' using errcode='42501'; end if;
  if expected_revision < 0 or expected_revision is null then
    raise exception 'Invalid revision' using errcode='22023';
  end if;
  if expected_revision = 0 then
    insert into public.journal_records(owner_id,id,kind,data,deleted)
    values (who,record_id,record_kind,payload,is_deleted)
    on conflict do nothing returning * into item;
    if found then return jsonb_build_object('accepted',true,'record',to_jsonb(item)); end if;
  else
    update public.journal_records set data=payload,deleted=is_deleted,
      revision=revision+1,updated_at=now()
    where owner_id=who and id=record_id and revision=expected_revision and kind=record_kind
    returning * into item;
    if found then return jsonb_build_object('accepted',true,'record',to_jsonb(item)); end if;
  end if;
  select * into item from public.journal_records where owner_id=who and id=record_id;
  -- An acknowledged write may have lost its HTTP response. Retrying is harmless.
  if found and item.kind=record_kind and item.data=payload and item.deleted=is_deleted then
    return jsonb_build_object('accepted',true,'record',to_jsonb(item));
  end if;
  return jsonb_build_object('accepted',false,'record',case when item.id is null then null else to_jsonb(item) end);
end;
$$;
revoke all on function public.put_journal_record(uuid,text,jsonb,bigint,boolean) from public, anon;
grant execute on function public.put_journal_record(uuid,text,jsonb,bigint,boolean) to authenticated;

insert into storage.buckets(id,name,public,file_size_limit)
values ('journal-media','journal-media',false,10485760)
on conflict (id) do update set public=false,file_size_limit=10485760;
drop policy if exists own_media_read on storage.objects;
drop policy if exists own_media_insert on storage.objects;
create policy own_media_read on storage.objects for select to authenticated
  using (bucket_id='journal-media' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy own_media_insert on storage.objects for insert to authenticated
  with check (bucket_id='journal-media' and (storage.foldername(name))[1]=(select auth.uid())::text);
-- Content-addressed objects are immutable; clients cannot overwrite or delete
-- media referenced by another offline device. Cleanup is an administrator job.
commit;
