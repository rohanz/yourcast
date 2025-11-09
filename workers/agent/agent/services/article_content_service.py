"""
Article Content Fetcher Service - Extracts full article content from URLs
Uses requests for fetching with timeout, trafilatura for extraction
"""
import logging
import requests
import trafilatura
from typing import Optional

logger = logging.getLogger(__name__)

class ArticleContentService:
    def __init__(self):
        self.timeout_seconds = 15  # 15 second timeout for requests

    def fetch_article_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract the main article content from a URL
        Uses requests with 15-second timeout, then trafilatura for extraction

        Args:
            url: Article URL to fetch

        Returns:
            Extracted article text, or None if extraction failed
        """
        try:
            logger.info(f"Fetching article content from: {url}")

            # Download the webpage using requests with timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, timeout=self.timeout_seconds, headers=headers)
            response.raise_for_status()  # Raise exception for bad status codes

            html = response.text
            if not html:
                logger.warning(f"Empty response from {url}")
                return None

            # Extract the main article content using trafilatura
            # include_comments=False removes comment sections
            # include_tables=True keeps data tables
            # include_links=False removes navigation links
            extracted_text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                include_links=False,
                output_format='txt'
            )

            if not extracted_text or len(extracted_text.strip()) < 100:
                logger.warning(f"Extracted text too short or empty from {url}")
                return None

            logger.info(f"Successfully extracted {len(extracted_text)} characters from {url}")
            return extracted_text.strip()

        except requests.Timeout:
            logger.warning(f"Timeout ({self.timeout_seconds}s) fetching article from {url}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error extracting article content from {url}: {str(e)}")
            return None

    def fetch_multiple_articles(self, urls: list[str]) -> dict[str, Optional[str]]:
        """
        Fetch content from multiple article URLs

        Args:
            urls: List of article URLs

        Returns:
            Dictionary mapping URL to extracted content (or None if failed)
        """
        results = {}
        for url in urls:
            content = self.fetch_article_content(url)
            results[url] = content

        success_count = sum(1 for content in results.values() if content is not None)
        logger.info(f"Successfully fetched {success_count}/{len(urls)} articles")

        return results
