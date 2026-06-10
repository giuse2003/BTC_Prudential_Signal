-- BTC Prudential Signal
-- Schema Supabase per gli iscritti alle notifiche Telegram.
--
-- Eseguire questo file nel Supabase SQL Editor.
-- Non inserire chiavi, token o password in questo script.

begin;

create table if not exists public.telegram_subscribers (
    telegram_chat_id bigint primary key,
    telegram_user_id bigint,
    telegram_username text,
    telegram_first_name text,
    telegram_language_code text,
    active boolean not null default true,
    subscribed_at timestamptz not null default now(),
    unsubscribed_at timestamptz,
    consent_version text not null default 'v1',
    consent_source text not null default 'telegram_command',
    last_delivered_at timestamptz,
    delivery_failures integer not null default 0,
    last_delivery_error text,
    last_delivery_error_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint telegram_subscribers_chat_id_not_zero
        check (telegram_chat_id <> 0),
    constraint telegram_subscribers_user_id_positive
        check (telegram_user_id is null or telegram_user_id > 0),
    constraint telegram_subscribers_delivery_failures_non_negative
        check (delivery_failures >= 0),
    constraint telegram_subscribers_username_length
        check (
            telegram_username is null
            or char_length(telegram_username) <= 64
        ),
    constraint telegram_subscribers_consent_version_not_blank
        check (btrim(consent_version) <> ''),
    constraint telegram_subscribers_consent_source_not_blank
        check (btrim(consent_source) <> '')
);

comment on table public.telegram_subscribers is
    'Iscritti Telegram alle notifiche di cambio segnale o rischio.';

comment on column public.telegram_subscribers.telegram_chat_id is
    'Identificativo della chat privata usato come destinatario Telegram.';

comment on column public.telegram_subscribers.active is
    'True quando l utente ha un iscrizione attiva.';

comment on column public.telegram_subscribers.consent_version is
    'Versione del testo di consenso accettato con il comando /iscrivimi.';

create index if not exists telegram_subscribers_active_idx
    on public.telegram_subscribers (active)
    where active = true;

create index if not exists telegram_subscribers_user_id_idx
    on public.telegram_subscribers (telegram_user_id);

create or replace function public.set_telegram_subscribers_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_telegram_subscribers_updated_at
    on public.telegram_subscribers;

create trigger set_telegram_subscribers_updated_at
before update on public.telegram_subscribers
for each row
execute function public.set_telegram_subscribers_updated_at();

alter table public.telegram_subscribers enable row level security;
alter table public.telegram_subscribers force row level security;

revoke all on table public.telegram_subscribers from anon;
revoke all on table public.telegram_subscribers from authenticated;
grant select, insert, update, delete
    on table public.telegram_subscribers
    to service_role;

commit;

-- Verifica finale: deve restituire una riga con rls_enabled=true e
-- rls_forced=true.
select
    c.relname as table_name,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname = 'telegram_subscribers';

-- Verifica finale: non devono comparire policy pubbliche.
select
    schemaname,
    tablename,
    policyname,
    roles,
    cmd
from pg_policies
where schemaname = 'public'
  and tablename = 'telegram_subscribers';
