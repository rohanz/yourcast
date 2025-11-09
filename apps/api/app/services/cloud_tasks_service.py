"""
Cloud Tasks Service - Replace Redis queue with Google Cloud Tasks
"""
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from typing import List
import json
import datetime
from app.config import settings, config

class CloudTasksService:
    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.project = 'yourcast-cloudrun-competition'
        self.location = 'us-central1'
        self.queue_name = 'episode-generation-v2'

        # Queue path
        self.queue_path = self.client.queue_path(
            self.project,
            self.location,
            self.queue_name
        )

    def queue_episode_generation(
        self,
        episode_id: str,
        subcategories: List[str],
        duration_minutes: int,
        worker_url: str = None,
        custom_tags: List[str] = None
    ):
        """
        Queue episode generation job using Cloud Tasks

        Args:
            episode_id: UUID of episode to generate
            subcategories: List of subcategories to include
            duration_minutes: Target duration
            worker_url: Worker endpoint URL (defaults to Cloud Run worker service)
            custom_tags: Optional list of custom tags for article filtering
        """
        # Default to Cloud Run worker service
        if not worker_url:
            import os
            worker_url = os.getenv('WORKER_URL', 'https://yourcast-worker-zprpg5fm2a-uc.a.run.app/generate')

        # Create task payload
        payload = {
            "episode_id": episode_id,
            "subcategories": subcategories,
            "duration_minutes": duration_minutes,
            "custom_tags": custom_tags or []
        }

        # Create the task with OIDC authentication for Cloud Run
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': worker_url,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps(payload).encode(),
                'oidc_token': {
                    'service_account_email': '798612619811-compute@developer.gserviceaccount.com'
                }
            }
        }

        # Optional: Schedule task for future execution
        # d = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
        # timestamp = timestamp_pb2.Timestamp()
        # timestamp.FromDatetime(d)
        # task['schedule_time'] = timestamp

        try:
            # Add task to queue
            response = self.client.create_task(
                request={
                    "parent": self.queue_path,
                    "task": task
                }
            )

            print(f"✅ Created Cloud Task: {response.name}")
            return response.name

        except Exception as e:
            print(f"❌ Failed to create Cloud Task: {str(e)}")
            raise
