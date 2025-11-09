import logging
import tempfile
import os
from typing import List, Dict, Any
from agent.services.llm_service import PodcastScript

logger = logging.getLogger(__name__)

class TranscriptService:
    def __init__(self):
        pass
    
    def generate_forced_alignment(self, audio_path: str, script: PodcastScript, chunk_timestamps: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate timestamps using actual TTS data or fallback to estimation"""
        
        # If we have actual TTS timestamps, use them for accurate timing
        if chunk_timestamps:
            logger.info(f"Using actual TTS timestamps from {len(chunk_timestamps)} chunks")
            return self._create_segments_from_tts_timestamps(chunk_timestamps, script)
        else:
            # Fallback to estimation if no TTS timestamps available
            logger.warning("No TTS timestamps available, using fallback timing estimation")
            return self._create_fallback_segments(script)
    
    def _group_into_sentences(self, word_entries: List[Dict]) -> List[Dict[str, Any]]:
        """Group word-level timestamps into sentence-level segments"""
        if not word_entries:
            return []
        
        segments = []
        current_segment = {
            "start": word_entries[0]["start"],
            "text": "",
            "words": []
        }
        
        for word_entry in word_entries:
            current_segment["words"].append(word_entry)
            current_segment["text"] += word_entry["text"]
            
            # End segment on sentence boundaries or after ~15 words
            if (word_entry["text"].endswith(('.', '!', '?')) or 
                len(current_segment["words"]) >= 15):
                
                current_segment["end"] = word_entry["end"]
                segments.append(current_segment)
                
                # Start new segment
                if word_entry != word_entries[-1]:  # Not the last word
                    current_segment = {
                        "start": word_entry["end"],
                        "text": "",
                        "words": []
                    }
        
        # Handle any remaining words
        if current_segment["words"]:
            current_segment["end"] = current_segment["words"][-1]["end"]
            segments.append(current_segment)
        
        return segments
    
    def _add_source_attribution(self, segments: List[Dict], script: PodcastScript) -> List[Dict[str, Any]]:
        """Add source IDs to segments based on script paragraphs"""
        attributed_segments = []
        script_text = " ".join([p["text"] for p in script.paragraphs])
        
        for i, segment in enumerate(segments):
            # Try to match segment text to script paragraphs
            source_ids = []
            segment_text = segment["text"].strip()
            
            for paragraph in script.paragraphs:
                # Simple text matching - could be improved
                if any(word in paragraph["text"].lower() for word in segment_text.lower().split()[:3]):
                    source_ids.extend(paragraph["source_ids"])
            
            attributed_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment_text,
                "source_ids": list(set(source_ids))  # Remove duplicates
            })
        
        return attributed_segments
    
    def _create_segments_from_tts_timestamps(self, chunk_timestamps: List[Dict[str, Any]], script: PodcastScript) -> List[Dict[str, Any]]:
        """Create segments from actual TTS word-level timestamps (excludes intro/outro)"""
        segments = []
        current_audio_time = 0.0  # Track time across multiple audio chunks

        for chunk_idx, chunk in enumerate(chunk_timestamps):
            paragraph_text = chunk['paragraph_text']
            word_timestamps = chunk.get('words', [])  # Safely get words, default to empty list
            paragraph_index = chunk['paragraph_index']
            topic = chunk.get('topic', 'Unknown')

            # Skip intro and outro from timestamps (they're not news segments)
            if topic in ["Introduction", "Outro"]:
                # Still need to advance time for accurate positioning
                if not word_timestamps:
                    chunk_duration = chunk.get('duration', len(paragraph_text.split()) / 2.67)
                else:
                    chunk_duration = word_timestamps[-1]['end']
                current_audio_time += chunk_duration + 0.25
                continue

            if not word_timestamps:
                # No word-level timestamps, use chunk duration from TTS
                chunk_duration = chunk.get('duration', len(paragraph_text.split()) / 2.67)  # Use actual duration or estimate
                segments.append({
                    "start": current_audio_time,
                    "end": current_audio_time + chunk_duration,
                    "text": paragraph_text,
                    "topic": topic,  # Include topic for chapter labels
                    "source_ids": script.paragraphs[paragraph_index]["source_ids"] if paragraph_index < len(script.paragraphs) else []
                })
                current_audio_time += chunk_duration  # Already includes crossfade in cumulative time
                continue

            # Calculate absolute timestamps by adding current_audio_time offset
            chunk_start = current_audio_time + word_timestamps[0]['start']
            chunk_end = current_audio_time + word_timestamps[-1]['end']

            # Create segment for this paragraph/chunk
            segments.append({
                "start": chunk_start,
                "end": chunk_end,
                "text": paragraph_text,
                "topic": topic,  # Include topic for chapter labels
                "source_ids": script.paragraphs[paragraph_index]["source_ids"] if paragraph_index < len(script.paragraphs) else [],
                "words": [  # Include word-level timing for frontend
                    {
                        "text": word['text'],
                        "start": current_audio_time + word['start'],
                        "end": current_audio_time + word['end']
                    }
                    for word in word_timestamps
                ]
            })

            # Update current time for next chunk (add chunk duration + small pause)
            chunk_duration = word_timestamps[-1]['end']
            current_audio_time += chunk_duration + 0.25  # Small pause between chunks

        logger.info(f"Created {len(segments)} segments from TTS timestamps (intro/outro excluded)")
        return segments
    
    def _create_fallback_segments(self, script: PodcastScript) -> List[Dict[str, Any]]:
        """Create segments with estimated timing as fallback"""
        segments = []
        current_time = 0.0
        words_per_second = 2.67  # 160 WPM / 60 seconds
        
        for paragraph in script.paragraphs:
            word_count = len(paragraph["text"].split())
            duration = word_count / words_per_second
            
            segments.append({
                "start": current_time,
                "end": current_time + duration,
                "text": paragraph["text"],
                "source_ids": paragraph["source_ids"]
            })
            
            current_time += duration + 0.5  # Add small pause
        
        logger.warning("Using fallback timing estimation")
        return segments
    
    def generate_webvtt(self, transcript_data: List[Dict[str, Any]]) -> str:
        """Generate WebVTT file content for chapters"""
        vtt_content = "WEBVTT\n\n"

        for i, segment in enumerate(transcript_data):
            start_time = self._format_webvtt_time(segment["start"])
            end_time = self._format_webvtt_time(segment["end"])

            # Create chapter markers for all segments
            # Get topic name if available, otherwise truncate text
            chapter_text = segment.get("topic", segment["text"][:50])
            vtt_content += f"{start_time} --> {end_time}\n"
            vtt_content += f"{chapter_text}\n\n"

        return vtt_content
    
    def _format_webvtt_time(self, seconds: float) -> str:
        """Format seconds as WebVTT timestamp"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"