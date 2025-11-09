-- Make published_date nullable in sources table
-- Some articles may not have a published date available

ALTER TABLE sources
ALTER COLUMN published_date DROP NOT NULL;
