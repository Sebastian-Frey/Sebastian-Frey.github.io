-- Wiki Pulse: Supabase schema. Paste into SQL editor.

create table cluster_snapshots (
  period text not null check (period in ('day','week','month')),
  period_start date not null,
  cluster_id int not null,
  label text not null,
  size int not null,
  rep_titles text[] not null,
  top_terms text[] not null,
  momentum float,
  centroid_x float,
  centroid_y float,
  generated_at timestamptz not null default now(),
  primary key (period, period_start, cluster_id)
);

create table cluster_members (
  period text not null,
  period_start date not null,
  title text not null,
  cluster_id int not null,
  umap_x float not null,
  umap_y float not null,
  edit_count int not null,
  primary key (period, period_start, title)
);

create index on cluster_members (period, period_start, cluster_id);

create table ingest_stats (
  ts timestamptz primary key,
  edits_per_min int not null,
  active_articles int not null,
  cluster_count int not null
);

-- RLS: public read-only for the anon key
alter table cluster_snapshots enable row level security;
alter table cluster_members   enable row level security;
alter table ingest_stats      enable row level security;

create policy "anon read" on cluster_snapshots for select to anon using (true);
create policy "anon read" on cluster_members   for select to anon using (true);
create policy "anon read" on ingest_stats      for select to anon using (true);
