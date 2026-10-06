-- SpaceFruit application data. Authentication identities are managed by Supabase Auth
-- in auth.users; this migration creates the app-owned profile and garden tables.

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  location_label text not null default '',
  timezone text not null default 'America/New_York',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.gardens (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'My SpaceFruit Garden',
  visibility text not null default 'private' check (visibility in ('private', 'community')),
  location_label text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.garden_memberships (
  id uuid primary key default gen_random_uuid(),
  garden_id uuid not null references public.gardens(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'member')),
  joined_at timestamptz not null default now(),
  constraint unique_garden_member unique (garden_id, user_id)
);

create table if not exists public.garden_plots (
  id uuid primary key default gen_random_uuid(),
  garden_id uuid not null references public.gardens(id) on delete cascade,
  label text not null,
  plant_type text not null default '',
  status text not null default 'empty' check (status in ('empty', 'planted', 'harvested')),
  health_status text not null default '',
  health_issues jsonb not null default '[]'::jsonb,
  planted_at timestamptz,
  last_monitored_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint unique_plot_label_per_garden unique (garden_id, label)
);

create table if not exists public.harvest_inventory_items (
  id uuid primary key default gen_random_uuid(),
  garden_id uuid not null references public.gardens(id) on delete cascade,
  plant_type text not null,
  quantity integer not null default 0 check (quantity >= 0),
  image_path text not null default '',
  updated_at timestamptz not null default now(),
  constraint unique_harvest_type_per_garden unique (garden_id, plant_type)
);

create table if not exists public.marketplace_listings (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  garden_id uuid not null references public.gardens(id) on delete cascade,
  section text not null check (section in ('trade', 'buy', 'donate')),
  plant_type text not null,
  quantity integer not null check (quantity > 0),
  weight numeric(8,2) not null check (weight > 0),
  weight_unit text not null default 'lb' check (weight_unit in ('lb', 'oz', 'kg', 'g')),
  asking_price numeric(8,2) check (asking_price is null or asking_price > 0),
  image_path text not null default '',
  grower_label text not null default '',
  location_label text not null default '',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists marketplace_listings_section_active_created_idx
  on public.marketplace_listings (section, active, created_at desc);
create index if not exists gardens_owner_id_idx on public.gardens (owner_id);
create index if not exists garden_memberships_user_id_idx on public.garden_memberships (user_id);
create index if not exists garden_plots_garden_id_idx on public.garden_plots (garden_id);
create index if not exists harvest_inventory_garden_id_idx on public.harvest_inventory_items (garden_id);

alter table public.user_profiles enable row level security;
alter table public.gardens enable row level security;
alter table public.garden_memberships enable row level security;
alter table public.garden_plots enable row level security;
alter table public.harvest_inventory_items enable row level security;
alter table public.marketplace_listings enable row level security;

create policy "Users can read their own profile" on public.user_profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy "Users can create their own profile" on public.user_profiles
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy "Users can update their own profile" on public.user_profiles
  for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

create policy "Garden members can view gardens" on public.gardens
  for select to authenticated using (
    owner_id = (select auth.uid()) or exists (
      select 1 from public.garden_memberships gm
      where gm.garden_id = gardens.id and gm.user_id = (select auth.uid())
    )
  );
create policy "Owners can create gardens" on public.gardens
  for insert to authenticated with check (owner_id = (select auth.uid()));
create policy "Owners can update gardens" on public.gardens
  for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "Owners can delete gardens" on public.gardens
  for delete to authenticated using (owner_id = (select auth.uid()));

create policy "Users can view their memberships" on public.garden_memberships
  for select to authenticated using (user_id = (select auth.uid()));

create policy "Garden members can view plots" on public.garden_plots
  for select to authenticated using (
    exists (select 1 from public.garden_memberships gm where gm.garden_id = garden_plots.garden_id and gm.user_id = (select auth.uid()))
  );
create policy "Garden owners can manage plots" on public.garden_plots
  for all to authenticated using (
    exists (select 1 from public.gardens g where g.id = garden_plots.garden_id and g.owner_id = (select auth.uid()))
  ) with check (
    exists (select 1 from public.gardens g where g.id = garden_plots.garden_id and g.owner_id = (select auth.uid()))
  );

create policy "Garden members can view harvest inventory" on public.harvest_inventory_items
  for select to authenticated using (
    exists (select 1 from public.garden_memberships gm where gm.garden_id = harvest_inventory_items.garden_id and gm.user_id = (select auth.uid()))
  );
create policy "Garden owners can manage harvest inventory" on public.harvest_inventory_items
  for all to authenticated using (
    exists (select 1 from public.gardens g where g.id = harvest_inventory_items.garden_id and g.owner_id = (select auth.uid()))
  ) with check (
    exists (select 1 from public.gardens g where g.id = harvest_inventory_items.garden_id and g.owner_id = (select auth.uid()))
  );

create policy "Everyone can view active marketplace listings" on public.marketplace_listings
  for select to authenticated using (active or owner_id = (select auth.uid()));
create policy "Owners can create listings for their gardens" on public.marketplace_listings
  for insert to authenticated with check (
    owner_id = (select auth.uid()) and exists (
      select 1 from public.gardens g where g.id = marketplace_listings.garden_id and g.owner_id = (select auth.uid())
    )
  );
create policy "Owners can update their listings" on public.marketplace_listings
  for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "Owners can delete their listings" on public.marketplace_listings
  for delete to authenticated using (owner_id = (select auth.uid()));

-- Create a starter profile and private garden automatically for each new Auth user.
create or replace function public.handle_new_spacefruit_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
declare
  garden_uuid uuid;
begin
  insert into public.user_profiles (user_id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)));
  insert into public.gardens (owner_id) values (new.id) returning id into garden_uuid;
  insert into public.garden_memberships (garden_id, user_id, role)
  values (garden_uuid, new.id, 'owner');
  return new;
end;
$$;

create trigger on_spacefruit_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_spacefruit_user();
