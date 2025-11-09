-- YourCast Database Schema for Supabase
-- Run this in your Supabase SQL editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users table (optional for MVP, but good for future)
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Episodes table
CREATE TABLE episodes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    duration_seconds INTEGER DEFAULT 0,
    subcategories JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    audio_url TEXT,
    transcript_url TEXT,
    vtt_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sources table (stores news articles)
CREATE TABLE sources (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(500) NOT NULL,
    url TEXT NOT NULL,
    published_date TIMESTAMP WITH TIME ZONE,
    excerpt TEXT,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Episode segments table (for chapter navigation)
CREATE TABLE episode_segments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    episode_id UUID REFERENCES episodes(id) ON DELETE CASCADE NOT NULL,
    start_time INTEGER NOT NULL, -- seconds from start
    end_time INTEGER NOT NULL,   -- seconds from start
    text TEXT NOT NULL,
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    order_index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Articles table - stores individual news articles with embeddings
CREATE TABLE articles (
    article_id VARCHAR(255) PRIMARY KEY, -- String ID used by clustering service
    cluster_id UUID, -- Links to story_clusters table
    uniqueness_hash VARCHAR(255) UNIQUE NOT NULL, -- For duplicate detection
    url TEXT UNIQUE NOT NULL,
    source_name VARCHAR(200) NOT NULL,
    title VARCHAR(1000) NOT NULL,
    summary TEXT, -- Article summary/excerpt
    publication_timestamp TIMESTAMP WITH TIME ZONE,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags TEXT, -- JSON string of tags array
    embedding vector(768), -- For semantic similarity search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story clusters table - groups related articles and assigns importance scores
CREATE TABLE story_clusters (
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

-- Indexes for better performance
CREATE INDEX idx_episodes_status ON episodes(status);
CREATE INDEX idx_episodes_created_at ON episodes(created_at);
CREATE INDEX idx_episodes_user_id ON episodes(user_id);
CREATE INDEX idx_sources_episode_id ON sources(episode_id);
CREATE INDEX idx_episode_segments_episode_id ON episode_segments(episode_id);
CREATE INDEX idx_episode_segments_order ON episode_segments(episode_id, order_index);

-- Articles and story clusters indexes
CREATE INDEX idx_articles_cluster_id ON articles(cluster_id);
CREATE INDEX idx_articles_publication_timestamp ON articles(publication_timestamp);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_subcategory ON articles(subcategory);
CREATE INDEX idx_articles_url ON articles(url);
CREATE INDEX idx_articles_created_at ON articles(created_at);
CREATE INDEX idx_articles_uniqueness_hash ON articles(uniqueness_hash);

CREATE INDEX idx_story_clusters_importance ON story_clusters(importance_score);
CREATE INDEX idx_story_clusters_category ON story_clusters(category);
CREATE INDEX idx_story_clusters_subcategory ON story_clusters(subcategory);
CREATE INDEX idx_story_clusters_last_updated ON story_clusters(last_updated_at);

-- Vector similarity index for semantic search
CREATE INDEX idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Update updated_at trigger for episodes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_episodes_updated_at BEFORE UPDATE ON episodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Foreign key constraint for articles
ALTER TABLE articles 
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

CREATE TRIGGER update_story_clusters_updated_at 
    BEFORE UPDATE ON story_clusters 
    FOR EACH ROW EXECUTE FUNCTION update_story_clusters_updated_at();

-- RLS (Row Level Security) policies - optional for MVP
-- Uncomment if you want to enable user-specific data access

-- ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE episode_segments ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Users can view their own episodes" ON episodes
--     FOR SELECT USING (auth.uid() = user_id);

-- CREATE POLICY "Users can create their own episodes" ON episodes
--     FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Storage bucket setup (run this via Supabase dashboard or storage API)
-- Create a bucket called 'podcasts' with public read access

-- Sample data for testing
INSERT INTO episodes (id, title, description, subcategories, status) VALUES
(
    uuid_generate_v4(),
    'Tech News Update - AI Developments',
    'Latest developments in artificial intelligence and technology',
    '["technology", "artificial intelligence"]',
    'completed'
);

COMMENT ON TABLE episodes IS 'Stores podcast episode metadata and status';
COMMENT ON TABLE sources IS 'News articles used to generate podcast episodes';
COMMENT ON TABLE episode_segments IS 'Timestamped segments for chapter navigation';
COMMENT ON TABLE articles IS 'Individual news articles with vector embeddings for semantic search';
COMMENT ON TABLE story_clusters IS 'Grouped related articles with importance scoring';
COMMENT ON COLUMN episodes.subcategories IS 'JSON array of subcategory strings';
COMMENT ON COLUMN episodes.status IS 'Current generation status of the episode';
COMMENT ON COLUMN articles.embedding IS '768-dimensional vector for semantic similarity search';
COMMENT ON COLUMN story_clusters.importance_score IS 'Article importance score from 1-100 based on multiple factors';