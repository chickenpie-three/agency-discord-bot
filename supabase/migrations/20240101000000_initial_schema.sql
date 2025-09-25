-- Enable necessary extensions
create extension if not exists "uuid-ossp";
create extension if not exists "vector";

-- Create knowledge_base table for storing scraped content and documents
create table public.knowledge_base (
    id uuid default uuid_generate_v4() primary key,
    source_type text not null check (source_type in ('url', 'document', 'manual')),
    source_url text,
    title text not null,
    content text not null,
    metadata jsonb default '{}'::jsonb,
    embedding vector(1536), -- For semantic search
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create index for full-text search
create index knowledge_base_content_fts_idx on public.knowledge_base using gin(to_tsvector('english', content));

-- Create index for embedding similarity search
create index knowledge_base_embedding_idx on public.knowledge_base using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Create function to update updated_at timestamp
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Create trigger to automatically update updated_at
create trigger handle_knowledge_base_updated_at
    before update on public.knowledge_base
    for each row
    execute procedure public.handle_updated_at();

-- Create uploaded_documents table for tracking document uploads
create table public.uploaded_documents (
    id uuid default uuid_generate_v4() primary key,
    filename text not null,
    file_type text not null,
    file_size bigint not null,
    storage_path text not null,
    processed boolean default false,
    knowledge_base_id uuid references public.knowledge_base(id),
    uploaded_by text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create scraped_urls table for tracking scraped websites
create table public.scraped_urls (
    id uuid default uuid_generate_v4() primary key,
    url text not null unique,
    title text,
    meta_description text,
    last_scraped timestamp with time zone default timezone('utc'::text, now()) not null,
    scrape_count integer default 1,
    knowledge_base_id uuid references public.knowledge_base(id),
    status text default 'success' check (status in ('success', 'failed', 'pending'))
);

-- Create bot_interactions table for tracking bot usage
create table public.bot_interactions (
    id uuid default uuid_generate_v4() primary key,
    discord_user_id text not null,
    discord_username text,
    command_used text not null,
    parameters jsonb default '{}'::jsonb,
    response_length integer,
    knowledge_sources_used text[],
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create indexes for better performance
create index scraped_urls_url_idx on public.scraped_urls(url);
create index bot_interactions_user_idx on public.bot_interactions(discord_user_id);
create index bot_interactions_command_idx on public.bot_interactions(command_used);
create index bot_interactions_created_at_idx on public.bot_interactions(created_at);

-- Row Level Security (RLS) policies
alter table public.knowledge_base enable row level security;
alter table public.uploaded_documents enable row level security;
alter table public.scraped_urls enable row level security;
alter table public.bot_interactions enable row level security;

-- Allow read access to all authenticated users
create policy "Allow read access to knowledge_base" on public.knowledge_base
    for select using (true);

create policy "Allow read access to uploaded_documents" on public.uploaded_documents
    for select using (true);

create policy "Allow read access to scraped_urls" on public.scraped_urls
    for select using (true);

-- Allow insert/update for service role (bot operations)
create policy "Allow service role to manage knowledge_base" on public.knowledge_base
    for all using (auth.role() = 'service_role');

create policy "Allow service role to manage uploaded_documents" on public.uploaded_documents
    for all using (auth.role() = 'service_role');

create policy "Allow service role to manage scraped_urls" on public.scraped_urls
    for all using (auth.role() = 'service_role');

create policy "Allow service role to manage bot_interactions" on public.bot_interactions
    for all using (auth.role() = 'service_role');

-- Create storage bucket for uploaded documents
insert into storage.buckets (id, name, public) values ('documents', 'documents', false);

-- Create storage policy for documents
create policy "Allow service role to manage documents" on storage.objects
    for all using (bucket_id = 'documents' and auth.role() = 'service_role');

-- Create function to search knowledge base with embeddings
create or replace function public.search_knowledge_base(
    query_embedding vector(1536),
    similarity_threshold float default 0.5,
    match_count int default 10
)
returns table (
    id uuid,
    source_type text,
    title text,
    content text,
    similarity float
)
language sql stable
as $$
    select
        kb.id,
        kb.source_type,
        kb.title,
        kb.content,
        1 - (kb.embedding <=> query_embedding) as similarity
    from public.knowledge_base kb
    where 1 - (kb.embedding <=> query_embedding) > similarity_threshold
    order by kb.embedding <=> query_embedding
    limit match_count;
$$;

-- Create function to get knowledge base stats
create or replace function public.get_knowledge_stats()
returns json
language sql stable
as $$
    select json_build_object(
        'total_entries', count(*),
        'url_sources', count(*) filter (where source_type = 'url'),
        'document_sources', count(*) filter (where source_type = 'document'),
        'manual_sources', count(*) filter (where source_type = 'manual'),
        'last_updated', max(updated_at)
    )
    from public.knowledge_base;
$$;
