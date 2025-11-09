import logging
import json
import os
import shutil
from typing import List, Dict, Any, Optional
from agent.config import settings
from agent.config_manager import get_worker_config

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.storage_dir = settings.storage_dir
        self.config = get_worker_config()

        # Detect storage provider from environment
        self.storage_provider = os.getenv("STORAGE_PROVIDER", "local").lower()

        if self.storage_provider == "gcs":
            # Cloud Storage setup
            from google.cloud import storage
            self.gcs_client = storage.Client()
            self.bucket_name = os.getenv("GCS_BUCKET_NAME", "yourcast-cloudrun-competition-media")
            self.bucket = self.gcs_client.bucket(self.bucket_name)
            logger.info(f"Using Cloud Storage bucket: {self.bucket_name}")
        else:
            # Local storage setup
            self.gcs_client = None
            os.makedirs(self.storage_dir, exist_ok=True)
            os.makedirs(os.path.join(self.storage_dir, "audio"), exist_ok=True)
            os.makedirs(os.path.join(self.storage_dir, "transcripts"), exist_ok=True)
            os.makedirs(os.path.join(self.storage_dir, "vtt"), exist_ok=True)
            logger.info(f"Using local storage: {self.storage_dir}")

    def upload_audio(self, episode_id: str, audio_path: str, user_id: Optional[str] = None) -> str:
        """Upload audio file to storage (local or Cloud Storage)"""
        try:
            if self.storage_provider == "gcs":
                return self._upload_audio_gcs(episode_id, audio_path, user_id)
            else:
                return self._upload_audio_local(episode_id, audio_path, user_id)
        except Exception as e:
            logger.error(f"Failed to store audio for episode {episode_id}: {str(e)}")
            raise

    def _upload_audio_local(self, episode_id: str, audio_path: str, user_id: Optional[str] = None) -> str:
        """Copy audio file to local storage with optional user prefix"""
        if user_id:
            episode_dir = os.path.join(self.storage_dir, "users", user_id, "audio")
            url_path = f"users/{user_id}/audio/{episode_id}.mp3"
        else:
            episode_dir = os.path.join(self.storage_dir, "audio")
            url_path = f"audio/{episode_id}.mp3"

        os.makedirs(episode_dir, exist_ok=True)

        storage_path = os.path.join(episode_dir, f"{episode_id}.mp3")
        shutil.copy2(audio_path, storage_path)
        os.remove(audio_path)

        absolute_url = f"{self.config.storage_base_url}/{url_path}"
        logger.info(f"Stored audio for episode {episode_id} at {storage_path}")
        return absolute_url

    def _upload_audio_gcs(self, episode_id: str, audio_path: str, user_id: Optional[str] = None) -> str:
        """Upload audio file to Google Cloud Storage with optional user prefix"""
        # Use user prefix for better organization if user_id is provided
        if user_id:
            blob_name = f"users/{user_id}/audio/{episode_id}.mp3"
        else:
            blob_name = f"audio/{episode_id}.mp3"

        blob = self.bucket.blob(blob_name)

        blob.upload_from_filename(audio_path, content_type="audio/mpeg")
        os.remove(audio_path)

        # Return public URL
        public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
        logger.info(f"Stored audio for episode {episode_id} at {public_url}")
        return public_url

    def upload_transcript(self, episode_id: str, transcript_data: List[Dict[str, Any]]) -> str:
        """Save transcript JSON to storage"""
        try:
            if self.storage_provider == "gcs":
                return self._upload_transcript_gcs(episode_id, transcript_data)
            else:
                return self._upload_transcript_local(episode_id, transcript_data)
        except Exception as e:
            logger.error(f"Failed to store transcript for episode {episode_id}: {str(e)}")
            raise

    def _upload_transcript_local(self, episode_id: str, transcript_data: List[Dict[str, Any]]) -> str:
        """Save transcript JSON to local storage"""
        episode_dir = os.path.join(self.storage_dir, "transcripts")
        os.makedirs(episode_dir, exist_ok=True)

        storage_path = os.path.join(episode_dir, f"{episode_id}.json")
        with open(storage_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)

        absolute_url = f"{self.config.storage_base_url}/transcripts/{episode_id}.json"
        logger.info(f"Stored transcript for episode {episode_id} at {storage_path}")
        return absolute_url

    def _upload_transcript_gcs(self, episode_id: str, transcript_data: List[Dict[str, Any]]) -> str:
        """Upload transcript JSON to Google Cloud Storage"""
        blob_name = f"transcripts/{episode_id}.json"
        blob = self.bucket.blob(blob_name)

        json_str = json.dumps(transcript_data, indent=2, ensure_ascii=False)
        blob.upload_from_string(json_str, content_type="application/json")

        public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
        logger.info(f"Stored transcript for episode {episode_id} at {public_url}")
        return public_url

    def upload_vtt(self, episode_id: str, vtt_content: str) -> str:
        """Save WebVTT file to storage"""
        try:
            if self.storage_provider == "gcs":
                return self._upload_vtt_gcs(episode_id, vtt_content)
            else:
                return self._upload_vtt_local(episode_id, vtt_content)
        except Exception as e:
            logger.error(f"Failed to store VTT for episode {episode_id}: {str(e)}")
            raise

    def _upload_vtt_local(self, episode_id: str, vtt_content: str) -> str:
        """Save WebVTT file to local storage"""
        episode_dir = os.path.join(self.storage_dir, "vtt")
        os.makedirs(episode_dir, exist_ok=True)

        storage_path = os.path.join(episode_dir, f"{episode_id}.vtt")
        with open(storage_path, 'w', encoding='utf-8') as f:
            f.write(vtt_content)

        absolute_url = f"{self.config.storage_base_url}/vtt/{episode_id}.vtt"
        logger.info(f"Stored VTT for episode {episode_id} at {storage_path}")
        return absolute_url

    def _upload_vtt_gcs(self, episode_id: str, vtt_content: str) -> str:
        """Upload WebVTT file to Google Cloud Storage"""
        blob_name = f"vtt/{episode_id}.vtt"
        blob = self.bucket.blob(blob_name)

        blob.upload_from_string(vtt_content, content_type="text/vtt")

        public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
        logger.info(f"Stored VTT for episode {episode_id} at {public_url}")
        return public_url
