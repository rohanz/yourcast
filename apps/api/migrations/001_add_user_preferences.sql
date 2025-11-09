-- Migration: Add preferences column to users table
-- Date: 2025-10-27
-- Description: Add JSON column to store user preferences (selected categories/subcategories)

ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSONB;

-- No rollback needed for adding nullable column, but if you need to rollback:
-- ALTER TABLE users DROP COLUMN IF EXISTS preferences;
