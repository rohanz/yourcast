-- Add article_id to sources table to track the original article from RSS system
ALTER TABLE sources
ADD COLUMN IF NOT EXISTS article_id VARCHAR(255);

-- Add index for efficient queries
CREATE INDEX IF NOT EXISTS idx_sources_article_id ON sources(article_id);

COMMENT ON COLUMN sources.article_id IS 'Reference to original article ID from RSS system';
