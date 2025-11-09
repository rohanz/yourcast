import logging
import numpy as np
import os
from typing import List, Optional
import google.genai as genai
from agent.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        """Initialize the Google GenAI client for embeddings via Vertex AI"""
        # Initialize the google-genai client configured for Vertex AI
        # We need to explicitly pass the vertex AI configuration
        
        project = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
        
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
        
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
        self.model_name = "text-embedding-004"
        
        # We're using 768 dimensions to match our database schema
        self.output_dimensionality = 768
        
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a single text using Google's text-embedding-004
        
        Args:
            text: The text to embed (title + summary)
            
        Returns:
            numpy array of 768 dimensions or None if failed
        """
        try:
            # Clean and prepare text
            clean_text = self._clean_text(text)
            if not clean_text:
                logger.warning("Empty text provided for embedding")
                return None
            
            # Use the new google-genai client for embeddings
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=clean_text,
                config={
                    "output_dimensionality": self.output_dimensionality,
                    "task_type": "RETRIEVAL_DOCUMENT"  # Appropriate for news article retrieval
                }
            )
            
            if response and response.embeddings and len(response.embeddings) > 0:
                # Convert to numpy array (get the first embedding)
                embedding_vector = np.array(response.embeddings[0].values)
                logger.debug(f"Generated embedding with shape: {embedding_vector.shape}")
                return embedding_vector
            else:
                logger.error("No embeddings returned from API")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple texts in a batch
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of numpy arrays (or None for failed embeddings)
        """
        try:
            # Clean all texts
            clean_texts = [self._clean_text(text) for text in texts]
            valid_indices = [i for i, text in enumerate(clean_texts) if text]
            
            if not valid_indices:
                logger.warning("No valid texts provided for batch embedding")
                return [None] * len(texts)
            
            valid_texts = [clean_texts[i] for i in valid_indices]
            
            # Process each text individually for now
            # Note: Check if google-genai supports true batch processing
            results = [None] * len(texts)
            
            for i, text in enumerate(valid_texts):
                original_index = valid_indices[i]
                try:
                    response = self.client.models.embed_content(
                        model=self.model_name,
                        contents=text,
                        config={
                            "output_dimensionality": self.output_dimensionality,
                            "task_type": "RETRIEVAL_DOCUMENT"
                        }
                    )
                    
                    if response and response.embeddings and len(response.embeddings) > 0:
                        results[original_index] = np.array(response.embeddings[0].values)
                        
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text {i}: {str(e)}")
                    results[original_index] = None
            
            logger.info(f"Generated {len([r for r in results if r is not None])} embeddings out of {len(texts)} texts")
            return results
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            return [None] * len(texts)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize
        cleaned = " ".join(text.strip().split())
        
        # Truncate if too long (text-embedding-004 has limits)
        max_length = 8192  # Conservative limit for text-embedding-004
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
            logger.debug(f"Truncated text to {max_length} characters")
        
        return cleaned
