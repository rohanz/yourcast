-- Fix sources table to use UUIDv7 and allow same article in multiple episodes
-- This adds article_id column to track original articles while using UUIDv7 for source records

-- Enable uuid-ossp extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add article_id column to track which article this source references
ALTER TABLE sources ADD COLUMN IF NOT EXISTS article_id TEXT;

-- Create index for faster lookups by article_id
CREATE INDEX IF NOT EXISTS idx_sources_article_id ON sources(article_id);

-- Update existing records to populate article_id (if any exist)
-- This assumes the current 'id' field contains article IDs
UPDATE sources SET article_id = id WHERE article_id IS NULL;

COMMENT ON COLUMN sources.article_id IS 'Reference to original article from RSS discovery system - allows same article in multiple episodes';
COMMENT ON COLUMN sources.id IS 'UUIDv7 identifier for this source record - unique per episode/article combination';

-- Note: To use UUIDv7, we'll need to update the application code to generate UUIDv7s
-- The database will continue using uuid_generate_v4() as default, but app should override with UUIDv7
