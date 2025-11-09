-- Add cluster_id to sources table to track which cluster each article came from
ALTER TABLE sources
ADD COLUMN cluster_id VARCHAR(255);

-- Add foreign key constraint
ALTER TABLE sources
ADD CONSTRAINT sources_cluster_id_fkey
FOREIGN KEY (cluster_id) REFERENCES story_clusters(cluster_id) ON DELETE SET NULL;

-- Add index for efficient queries
CREATE INDEX idx_sources_cluster_id ON sources(cluster_id);

COMMENT ON COLUMN sources.cluster_id IS 'Tracks which story cluster this source article came from to avoid repetition';
