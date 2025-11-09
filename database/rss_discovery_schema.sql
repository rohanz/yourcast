-- RSS Discovery System Schema
-- Creates tables for article discovery, clustering, and intelligence
-- Required for the RSS discovery system to work with real news articles

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Articles table - stores individual news articles with embeddings
CREATE TABLE IF NOT EXISTS articles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    cluster_id UUID, -- Links to story_clusters table
    title VARCHAR(1000) NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    publication_timestamp TIMESTAMP WITH TIME ZONE,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags TEXT[],
    source_name VARCHAR(200),
    author VARCHAR(200),
    embedding vector(768), -- For semantic similarity search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story clusters table - groups related articles and assigns importance scores
CREATE TABLE IF NOT EXISTS story_clusters (
    cluster_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    canonical_title VARCHAR(1000) NOT NULL,
    canonical_content TEXT,
    importance_score INTEGER DEFAULT 50 CHECK (importance_score >= 1 AND importance_score <= 100),
    article_count INTEGER DEFAULT 1,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_articles_cluster_id ON articles(cluster_id);
CREATE INDEX IF NOT EXISTS idx_articles_publication_timestamp ON articles(publication_timestamp);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_subcategory ON articles(subcategory);
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);

CREATE INDEX IF NOT EXISTS idx_story_clusters_importance ON story_clusters(importance_score);
CREATE INDEX IF NOT EXISTS idx_story_clusters_category ON story_clusters(category);
CREATE INDEX IF NOT EXISTS idx_story_clusters_subcategory ON story_clusters(subcategory);
CREATE INDEX IF NOT EXISTS idx_story_clusters_last_updated ON story_clusters(last_updated_at);

-- Vector similarity index for semantic search
CREATE INDEX IF NOT EXISTS idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Foreign key constraint
ALTER TABLE articles 
DROP CONSTRAINT IF EXISTS articles_cluster_id_fkey,
ADD CONSTRAINT articles_cluster_id_fkey 
FOREIGN KEY (cluster_id) REFERENCES story_clusters(cluster_id) ON DELETE SET NULL;

-- Update trigger for articles
CREATE OR REPLACE FUNCTION update_articles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
CREATE TRIGGER update_articles_updated_at 
    BEFORE UPDATE ON articles 
    FOR EACH ROW EXECUTE FUNCTION update_articles_updated_at();

-- Update trigger for story_clusters  
CREATE OR REPLACE FUNCTION update_story_clusters_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_story_clusters_updated_at ON story_clusters;
CREATE TRIGGER update_story_clusters_updated_at 
    BEFORE UPDATE ON story_clusters 
    FOR EACH ROW EXECUTE FUNCTION update_story_clusters_updated_at();

-- Sample data for testing (optional)
-- INSERT INTO story_clusters (canonical_title, importance_score, category, subcategory) VALUES
-- ('AI Breakthrough in Medical Diagnosis', 85, 'Technology', 'AI/ML'),
-- ('Climate Change Summit Updates', 75, 'World News', 'Environment');

COMMENT ON TABLE articles IS 'Individual news articles with vector embeddings for semantic search';
COMMENT ON TABLE story_clusters IS 'Grouped related articles with importance scoring';
COMMENT ON COLUMN articles.embedding IS '768-dimensional vector for semantic similarity search';
COMMENT ON COLUMN story_clusters.importance_score IS 'Article importance score from 1-100 based on multiple factors';