--
-- PostgreSQL database dump
--

\restrict 5mhjdp7jCSguzaaZunMmNWIHfTp0fccBqSP9cFLjybwG4w08hnr2IBQbFpHevm5

-- Dumped from database version 16.10 (Debian 16.10-1.pgdg12+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: update_articles_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_articles_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_story_clusters_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_story_clusters_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.last_updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: articles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.articles (
    article_id character varying(255) NOT NULL,
    cluster_id uuid,
    uniqueness_hash character varying(255) NOT NULL,
    url text NOT NULL,
    source_name character varying(200) NOT NULL,
    title character varying(1000) NOT NULL,
    summary text,
    publication_timestamp timestamp with time zone,
    category character varying(100),
    subcategory character varying(100),
    tags text,
    embedding public.vector(768),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE articles; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.articles IS 'Individual news articles with vector embeddings for semantic search';


--
-- Name: COLUMN articles.embedding; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.articles.embedding IS '768-dimensional vector for semantic similarity search';


--
-- Name: episode_segments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.episode_segments (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    episode_id uuid NOT NULL,
    start_time integer NOT NULL,
    end_time integer NOT NULL,
    text text NOT NULL,
    order_index integer NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    source_id uuid
);


--
-- Name: TABLE episode_segments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.episode_segments IS 'Timestamped segments for chapter navigation';


--
-- Name: episodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.episodes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    title character varying(500) NOT NULL,
    description text,
    duration_seconds integer DEFAULT 0,
    subcategories jsonb NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    audio_url text,
    transcript_url text,
    vtt_url text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT episodes_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: TABLE episodes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.episodes IS 'Stores podcast episode metadata and status';


--
-- Name: COLUMN episodes.subcategories; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.episodes.subcategories IS 'JSON array of subcategory strings';


--
-- Name: COLUMN episodes.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.episodes.status IS 'Current generation status of the episode';


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sources (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    episode_id uuid NOT NULL,
    article_id text NOT NULL,
    title character varying(500) NOT NULL,
    url text NOT NULL,
    published_date timestamp with time zone,
    excerpt text,
    summary text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: story_clusters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.story_clusters (
    cluster_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    canonical_title character varying(1000) NOT NULL,
    canonical_content text,
    importance_score integer DEFAULT 50,
    article_count integer DEFAULT 1,
    category character varying(100),
    subcategory character varying(100),
    first_seen_at timestamp with time zone DEFAULT now(),
    last_updated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT story_clusters_importance_score_check CHECK (((importance_score >= 1) AND (importance_score <= 100)))
);


--
-- Name: TABLE story_clusters; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.story_clusters IS 'Grouped related articles with importance scoring';


--
-- Name: COLUMN story_clusters.importance_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.story_clusters.importance_score IS 'Article importance score from 1-100 based on multiple factors';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: articles articles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_pkey PRIMARY KEY (article_id);


--
-- Name: articles articles_uniqueness_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_uniqueness_hash_key UNIQUE (uniqueness_hash);


--
-- Name: articles articles_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_url_key UNIQUE (url);


--
-- Name: episode_segments episode_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.episode_segments
    ADD CONSTRAINT episode_segments_pkey PRIMARY KEY (id);


--
-- Name: episodes episodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.episodes
    ADD CONSTRAINT episodes_pkey PRIMARY KEY (id);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: story_clusters story_clusters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.story_clusters
    ADD CONSTRAINT story_clusters_pkey PRIMARY KEY (cluster_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_articles_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_category ON public.articles USING btree (category);


--
-- Name: idx_articles_cluster_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_cluster_id ON public.articles USING btree (cluster_id);


--
-- Name: idx_articles_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_created_at ON public.articles USING btree (created_at);


--
-- Name: idx_articles_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_embedding ON public.articles USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_articles_publication_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_publication_timestamp ON public.articles USING btree (publication_timestamp);


--
-- Name: idx_articles_subcategory; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_subcategory ON public.articles USING btree (subcategory);


--
-- Name: idx_articles_uniqueness_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_uniqueness_hash ON public.articles USING btree (uniqueness_hash);


--
-- Name: idx_articles_url; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_articles_url ON public.articles USING btree (url);


--
-- Name: idx_episode_segments_episode_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_episode_segments_episode_id ON public.episode_segments USING btree (episode_id);


--
-- Name: idx_episode_segments_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_episode_segments_order ON public.episode_segments USING btree (episode_id, order_index);


--
-- Name: idx_episodes_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_episodes_created_at ON public.episodes USING btree (created_at);


--
-- Name: idx_episodes_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_episodes_status ON public.episodes USING btree (status);


--
-- Name: idx_episodes_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_episodes_user_id ON public.episodes USING btree (user_id);


--
-- Name: idx_sources_article_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sources_article_id ON public.sources USING btree (article_id);


--
-- Name: idx_sources_episode_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sources_episode_id ON public.sources USING btree (episode_id);


--
-- Name: idx_story_clusters_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_story_clusters_category ON public.story_clusters USING btree (category);


--
-- Name: idx_story_clusters_importance; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_story_clusters_importance ON public.story_clusters USING btree (importance_score);


--
-- Name: idx_story_clusters_last_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_story_clusters_last_updated ON public.story_clusters USING btree (last_updated_at);


--
-- Name: idx_story_clusters_subcategory; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_story_clusters_subcategory ON public.story_clusters USING btree (subcategory);


--
-- Name: articles update_articles_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON public.articles FOR EACH ROW EXECUTE FUNCTION public.update_articles_updated_at();


--
-- Name: episodes update_episodes_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_episodes_updated_at BEFORE UPDATE ON public.episodes FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: story_clusters update_story_clusters_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_story_clusters_updated_at BEFORE UPDATE ON public.story_clusters FOR EACH ROW EXECUTE FUNCTION public.update_story_clusters_updated_at();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: articles articles_cluster_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_cluster_id_fkey FOREIGN KEY (cluster_id) REFERENCES public.story_clusters(cluster_id) ON DELETE SET NULL;


--
-- Name: episode_segments episode_segments_episode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.episode_segments
    ADD CONSTRAINT episode_segments_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES public.episodes(id) ON DELETE CASCADE;


--
-- Name: episode_segments episode_segments_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.episode_segments
    ADD CONSTRAINT episode_segments_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE SET NULL;


--
-- Name: episodes episodes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.episodes
    ADD CONSTRAINT episodes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: sources sources_episode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_episode_id_fkey FOREIGN KEY (episode_id) REFERENCES public.episodes(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 5mhjdp7jCSguzaaZunMmNWIHfTp0fccBqSP9cFLjybwG4w08hnr2IBQbFpHevm5

