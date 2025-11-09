export interface User {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface Episode {
  id: string;
  user_id: string;
  title: string;
  description: string;
  duration_seconds: number;
  subcategories: string[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
  audio_url?: string;
  transcript_url?: string;
  vtt_url?: string;
  created_at: string;
  updated_at: string;
}

export interface EpisodeSegment {
  id: string;
  episode_id: string;
  start_time: number;
  end_time: number;
  text: string;
  source_id?: string;
  order_index: number;
}

export interface Source {
  id: string;
  episode_id: string;
  title: string;
  url: string;
  published_date: string;
  excerpt: string;
  summary: string;
}

export interface CreateEpisodeRequest {
  subcategories: string[];
  duration_minutes: number;
}

export interface CreateEpisodeResponse {
  episode_id: string;
  status: string;
}

export interface EpisodeStatusEvent {
  episode_id: string;
  status: string;
  stage?: string;
  progress?: number;
  error?: string;
}

export interface TranscriptEntry {
  start: number;
  end: number;
  text: string;
  source_id?: string;
}

export interface PodcastScript {
  paragraphs: {
    text: string;
    source_ids: string[];
  }[];
  estimated_duration: number;
}