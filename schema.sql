-- Supabase PostgreSQL schema for vc-media-agent
-- Run this in the Supabase SQL Editor before first use.

CREATE TABLE IF NOT EXISTS articles (
    id            BIGSERIAL PRIMARY KEY,
    url_hash      TEXT        NOT NULL UNIQUE,   -- SHA256(url), dedup key
    url           TEXT        NOT NULL,
    source_name   TEXT        NOT NULL,
    source_region TEXT        NOT NULL,           -- 'intl' or 'cn'
    title         TEXT        NOT NULL,
    summary       TEXT,                           -- NULL until Claude generates it
    published_at  TIMESTAMPTZ,
    scraped_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pushed_at     TIMESTAMPTZ                     -- NULL until pushed to Feishu
);

CREATE INDEX IF NOT EXISTS idx_articles_url_hash     ON articles (url_hash);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_pushed_at    ON articles (pushed_at);
CREATE INDEX IF NOT EXISTS idx_articles_scraped_at   ON articles (scraped_at DESC);

-- Enable Row Level Security
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read access (for Vercel frontend calling Supabase REST API)
DROP POLICY IF EXISTS "anon_read" ON articles;
CREATE POLICY "anon_read" ON articles
    FOR SELECT
    TO anon
    USING (true);

-- Service role has full access (used by GitHub Actions via SUPABASE_KEY=service_role key)
-- No explicit policy needed; service_role bypasses RLS by default.
