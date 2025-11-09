-- Fix sources table to allow same article in multiple episodes
-- This migration changes the primary key to be (episode_id, article_id)

-- Step 1: Create new sources table with correct schema
CREATE TABLE sources_new (
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE NOT NULL,
    article_id TEXT NOT NULL,  -- Reference to articles.article_id from RSS system
    title VARCHAR(500) NOT NULL,
    url TEXT NOT NULL,
    published_date TIMESTAMP WITH TIME ZONE,
    excerpt TEXT,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (episode_id, article_id)  -- Composite primary key allows same article in different episodes
);

-- Step 2: Copy existing data (if any)
INSERT INTO sources_new (episode_id, article_id, title, url, published_date, excerpt, summary, created_at)
SELECT episode_id, id, title, url, published_date, excerpt, summary, created_at
FROM sources;

-- Step 3: Update episode_segments to use composite key
-- First add article_id column
ALTER TABLE episode_segments ADD COLUMN article_id TEXT;

-- Update existing references (this might need manual intervention depending on data)
UPDATE episode_segments 
SET article_id = (SELECT id FROM sources WHERE sources.id = episode_segments.source_id);

-- Step 4: Drop old foreign key constraint and add new one
ALTER TABLE episode_segments DROP CONSTRAINT IF EXISTS episode_segments_source_id_fkey;
ALTER TABLE episode_segments DROP COLUMN source_id;

-- Add foreign key to new composite key
ALTER TABLE episode_segments 
ADD CONSTRAINT episode_segments_source_fkey 
FOREIGN KEY (episode_id, article_id) REFERENCES sources_new(episode_id, article_id) ON DELETE SET NULL;

-- Step 5: Replace old table
DROP TABLE sources;
ALTER TABLE sources_new RENAME TO sources;

-- Step 6: Recreate indexes
CREATE INDEX idx_sources_episode_id ON sources(episode_id);
CREATE INDEX idx_sources_article_id ON sources(article_id);

COMMENT ON TABLE sources IS 'News articles used in podcast episodes - same article can appear in multiple episodes';
COMMENT ON COLUMN sources.article_id IS 'Reference to article from RSS discovery system';
