import logging
import tempfile
import os
import requests
import base64
import wave
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from google import genai
from google.genai import types
from agent.config import settings, config

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.tts_provider = settings.tts_provider.lower()

        if self.tts_provider == "google":
            self.api_key = settings.google_tts_api_key
            if not self.api_key:
                raise ValueError("Google TTS API key is required when using Google provider")
        elif self.tts_provider == "gemini":
            # Gemini TTS uses the same Gemini API key
            self.api_key = settings.gemini_api_key
            if not self.api_key:
                raise ValueError("Gemini API key is required when using Gemini TTS provider")
        elif self.tts_provider == "deepinfra":
            self.api_key = settings.deepinfra_api_key
            if not self.api_key:
                raise ValueError("DeepInfra API key is required when using DeepInfra provider")
        elif self.tts_provider == "fal":
            self.api_key = settings.fal_api_key
            if not self.api_key:
                raise ValueError("Fal.ai API key is required when using Fal provider")
        else:
            raise ValueError(f"Unsupported TTS provider: {self.tts_provider}. Use 'google', 'gemini', 'deepinfra', or 'fal'")

        logger.info(f"Initialized TTS service with provider: {self.tts_provider}")
    
    def generate_audio_chunks(self, paragraphs: List[Dict[str, Any]]) -> tuple[List[str], List[Dict[str, Any]]]:
        """Convert script paragraphs (now topic blocks) to audio chunks with batched parallel processing"""
        logger.info(f"Starting batched TTS generation for {len(paragraphs)} topic blocks")

        # Generate audio files in batches for parallel processing
        # Using DeepInfra/Kokoro which has much higher rate limits than Gemini
        audio_results = {}  # {index: {"path": audio_path, "duration": duration, "paragraph": paragraph}}
        BATCH_SIZE = 8

        def generate_single_audio(i: int, paragraph: Dict[str, Any]):
            """Generate audio for a single topic block"""
            try:
                audio_path = self._text_to_speech(paragraph["text"], f"topic_{i}")
                chunk_duration = self._get_audio_duration(audio_path)
                logger.info(f"Generated audio for topic {i+1}/{len(paragraphs)}: {chunk_duration:.2f}s - Topic: {paragraph.get('topic', 'Unknown')}")
                return i, audio_path, chunk_duration, paragraph, None
            except Exception as e:
                logger.error(f"Failed to generate audio for paragraph {i}: {str(e)}")
                # Create fallback silence
                silence_duration = 2.0
                silence_path = self._create_silence(silence_duration, f"silence_{i}")
                return i, silence_path, silence_duration, paragraph, str(e)

        # Process paragraphs in batches
        for batch_start in range(0, len(paragraphs), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(paragraphs))
            batch = paragraphs[batch_start:batch_end]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (len(paragraphs) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} paragraphs)")

            # Use ThreadPoolExecutor for parallel generation within batch
            with ThreadPoolExecutor(max_workers=min(8, len(batch))) as executor:
                # Submit all tasks in this batch
                futures = {
                    executor.submit(generate_single_audio, batch_start + j, para): batch_start + j
                    for j, para in enumerate(batch)
                }

                # Collect results as they complete
                for future in as_completed(futures):
                    i, audio_path, duration, paragraph, error = future.result()
                    audio_results[i] = {
                        "path": audio_path,
                        "duration": duration,
                        "paragraph": paragraph,
                        "error": error
                    }

            logger.info(f"Completed batch {batch_num}/{total_batches}")

            # Add delay between batches to respect rate limits (disabled for DeepInfra)
            # DeepInfra has much higher rate limits than Gemini, no delay needed
            if batch_num < total_batches:
                import time
                # logger.info(f"Waiting 0s before next batch...")
                time.sleep(0)

        # Now build ordered lists and calculate cumulative timestamps
        audio_files = []
        all_timestamps = []
        cumulative_duration = 0.0

        for i in range(len(paragraphs)):
            result = audio_results[i]
            audio_files.append(result["path"])

            chunk_timestamps = {
                "paragraph_index": i,
                "paragraph_text": result["paragraph"]["text"],
                "audio_path": result["path"],
                "start_time": cumulative_duration,
                "end_time": cumulative_duration + result["duration"],
                "duration": result["duration"],
                "topic": result["paragraph"].get("topic", "Unknown"),
                "source_ids": result["paragraph"].get("source_ids", [])
            }
            all_timestamps.append(chunk_timestamps)

            # Update cumulative duration (subtract crossfade overlap for segments after first)
            if i == 0:
                cumulative_duration += result["duration"]
            else:
                cumulative_duration += result["duration"] - 0.05  # 50ms crossfade overlap

        logger.info(f"Completed batched TTS generation. Total duration: {cumulative_duration:.2f}s")
        return audio_files, all_timestamps

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file in seconds"""
        try:
            audio = AudioSegment.from_file(audio_path)
            duration_seconds = len(audio) / 1000.0  # Convert milliseconds to seconds
            return duration_seconds
        except Exception as e:
            logger.error(f"Failed to get audio duration for {audio_path}: {str(e)}")
            # Fallback: estimate based on file size (very rough)
            return 5.0  # Default fallback duration
    
    def _text_to_speech(self, text: str, filename: str) -> str:
        """Convert text to speech using the configured TTS provider"""
        if self.tts_provider == "google":
            return self._google_text_to_speech(text, filename)
        elif self.tts_provider == "gemini":
            return self._gemini_text_to_speech(text, filename)
        elif self.tts_provider == "deepinfra":
            return self._deepinfra_text_to_speech(text, filename)
        elif self.tts_provider == "fal":
            return self._fal_text_to_speech(text, filename)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.tts_provider}")
    
    def _text_to_speech_with_timestamps(self, text: str, filename: str) -> tuple[str, List[Dict[str, Any]]]:
        """Convert text to speech and return both audio path and timestamps"""
        if self.tts_provider == "google":
            # Google doesn't support timestamps in the current implementation
            audio_path = self._google_text_to_speech(text, filename)
            return audio_path, []
        elif self.tts_provider == "deepinfra":
            return self._deepinfra_text_to_speech_with_timestamps(text, filename)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.tts_provider}")
    
    def _google_text_to_speech(self, text: str, filename: str) -> str:
        """Convert text to speech using Google Cloud TTS REST API"""
        url = f"{config.tts_google_url}?key={self.api_key}"
        
        # Request payload
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": "en-US-Neural2-F",  # High quality neural voice (female)
                "ssmlGender": "FEMALE"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0.0
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Make API request
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Get the audio content (base64 encoded)
        result = response.json()
        audio_content = result["audioContent"]
        
        # Decode base64 and save to file
        audio_data = base64.b64decode(audio_content)
        
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"{filename}.mp3")
        
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        
        logger.debug(f"Google TTS audio saved to {audio_path}")
        return audio_path

    def _gemini_text_to_speech(self, text: str, filename: str) -> str:
        """Convert text to speech using Gemini 2.5 Pro TTS via REST API"""
        try:
            logger.debug(f"Converting text to speech with Gemini TTS: {text[:50]}...")

            # Use REST API with API key (bypass Vertex AI which doesn't support API keys)
            # Try non-preview version to see if it has different quota limits
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-tts:generateContent?key={self.api_key}"

            headers = {
                "Content-Type": "application/json"
            }

            # Format following Gemini TTS pattern: instruction + content
            formatted_text = f"Read aloud in a professional tone, with an american accent: {text}"

            payload = {
                "contents": [{
                    "parts": [{
                        "text": formatted_text
                    }]
                }],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Enceladus"
                            }
                        }
                    }
                }
            }

            response = requests.post(url, json=payload, headers=headers, timeout=120)

            # Log response status for debugging
            logger.info(f"Gemini TTS response status: {response.status_code}")

            # Check for HTTP errors and log full response
            if not response.ok:
                logger.error(f"Gemini TTS HTTP error {response.status_code}")
                logger.error(f"Response body: {response.text}")
                logger.error(f"Text that failed: {text[:200]}")
                response.raise_for_status()

            result = response.json()

            # Log response structure for debugging (without the huge audio data)
            result_summary = {
                "has_candidates": bool(result.get("candidates")),
                "num_candidates": len(result.get("candidates", [])),
            }
            if result.get("candidates"):
                cand = result["candidates"][0]
                result_summary["candidate_0"] = {
                    "has_content": bool(cand.get("content")),
                    "has_parts": bool(cand.get("content", {}).get("parts")),
                    "num_parts": len(cand.get("content", {}).get("parts", [])),
                }
                if cand.get("content", {}).get("parts"):
                    part = cand["content"]["parts"][0]
                    result_summary["part_0"] = {
                        "has_inlineData": "inlineData" in part,
                        "has_text": "text" in part,
                        "data_length": len(part.get("inlineData", {}).get("data", "")) if "inlineData" in part else 0
                    }
            logger.info(f"Gemini TTS response structure: {result_summary}")

            # Extract audio data from response
            if not result.get("candidates") or not result["candidates"][0].get("content", {}).get("parts"):
                logger.error(f"No audio generated in Gemini TTS response")
                logger.error(f"Full response: {result}")
                logger.error(f"Text that failed: {text}")
                raise ValueError("No audio generated in Gemini TTS response")

            audio_part = result["candidates"][0]["content"]["parts"][0]
            if "inlineData" not in audio_part:
                logger.error(f"No inline audio data in Gemini TTS response")
                logger.error(f"Audio part: {audio_part}")
                logger.error(f"Text that failed: {text}")
                raise ValueError("No inline audio data in Gemini TTS response")

            # Get base64 audio data
            audio_b64 = audio_part["inlineData"]["data"]

            # Decode base64 PCM data
            pcm_data = base64.b64decode(audio_b64)
            logger.debug(f"Decoded {len(pcm_data)} bytes of PCM data from Gemini TTS")

            # Save PCM to WAV using wave module (following Gemini TTS docs)
            # Specs: 16-bit PCM, 24kHz, mono
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{filename}.wav")

            with wave.open(audio_path, "wb") as wf:
                wf.setnchannels(1)        # Mono
                wf.setsampwidth(2)        # 16-bit = 2 bytes
                wf.setframerate(24000)    # 24kHz
                wf.writeframes(pcm_data)

            logger.debug(f"Gemini TTS audio saved to {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Gemini TTS failed: {str(e)}")
            raise ValueError(f"Failed to generate speech using Gemini TTS: {str(e)}")

    def _deepinfra_text_to_speech(self, text: str, filename: str) -> str:
        """Convert text to speech using DeepInfra Kokoro API with WAV format"""
        try:
            logger.debug(f"Converting text to speech with DeepInfra Kokoro: {text[:50]}...")
            
            # DeepInfra Kokoro API endpoint and payload
            url = config.tts_deepinfra_url
            payload = {
                "text": text,
                "preset_voice": ["am_michael", "am_echo"],
                "output_format": "pcm",  # Use PCM format for streaming
                "speed": 1.0,
                "sample_rate": 24000,  # Use DeepInfra's preferred sample rate
                "return_timestamps": True
            }
            
            headers = {
                "Authorization": f"bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Log word timestamps if present (DeepInfra returns them as "words" field)
            if "words" in result and result["words"]:
                logger.info(f"Received {len(result['words'])} word timestamps")
                logger.debug(f"Sample word timestamps: {result['words'][:3]}...")
            else:
                logger.warning("No word timestamps received from DeepInfra API")
            
            # Check if audio is present
            if "audio" not in result or result["audio"] is None:
                raise ValueError(f"No audio in response. Full response: {result}")
            
            # DeepInfra returns audio as data URL for PCM: "data:audio/pcm;base64,<base64_data>"
            audio_data_url = result["audio"]
            logger.debug(f"Received audio data URL: {audio_data_url[:100]}...")
            
            # Extract base64 data from data URL and parse sample rate
            sample_rate = 22050  # Default
            if audio_data_url.startswith("data:audio/"):
                # Split on comma to get the base64 part
                try:
                    data_prefix, audio_b64 = audio_data_url.split(',', 1)
                    logger.debug(f"Data URL format detected: {data_prefix}")
                    
                    # Extract sample rate from data URL if present
                    # Format: "data:audio/pcm;rate=24000;base64"
                    if "rate=" in data_prefix:
                        try:
                            rate_part = data_prefix.split("rate=")[1].split(";")[0]
                            sample_rate = int(rate_part)
                            logger.debug(f"Detected sample rate from data URL: {sample_rate}Hz")
                        except (IndexError, ValueError) as e:
                            logger.warning(f"Failed to parse sample rate from data URL, using default: {e}")
                            
                except ValueError:
                    raise ValueError(f"Invalid data URL format: {audio_data_url[:100]}")
            else:
                # Fallback: assume it's raw base64
                audio_b64 = audio_data_url
                logger.debug("Assuming raw base64 format")
            
            # Decode base64 PCM data
            missing_padding = len(audio_b64) % 4
            if missing_padding:
                audio_b64 += '=' * (4 - missing_padding)
            
            pcm_data = base64.b64decode(audio_b64)
            logger.debug(f"Decoded {len(pcm_data)} bytes of PCM data")
            
            # Convert PCM to WAV using AudioSegment with detected parameters
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{filename}.wav")
            
            try:
                # Create AudioSegment from raw PCM data with detected sample rate
                audio_segment = AudioSegment(
                    data=pcm_data,
                    sample_width=2,     # 16-bit = 2 bytes
                    frame_rate=sample_rate,  # Use detected sample rate
                    channels=1          # Mono
                )
                
                # Export as WAV for compatibility
                audio_segment.export(audio_path, format="wav")
                
                logger.debug(f"DeepInfra PCM converted to WAV: {audio_path}")
                
            except Exception as e:
                logger.error(f"PCM to WAV conversion failed: {e}")
                # Fallback: save raw PCM and try to convert with ffmpeg
                raw_path = os.path.join(temp_dir, f"{filename}.pcm")
                with open(raw_path, "wb") as f:
                    f.write(pcm_data)
                
                try:
                    import subprocess
                    # Convert PCM to WAV using ffmpeg
                    cmd = [
                        'ffmpeg', '-y', '-f', 's16le', '-ar', str(sample_rate), '-ac', '1',
                        '-i', raw_path, audio_path
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    os.remove(raw_path)  # Clean up raw file
                    logger.debug(f"PCM converted to WAV using ffmpeg: {audio_path}")
                except Exception as e2:
                    logger.error(f"FFmpeg conversion also failed: {e2}")
                    raise ValueError(f"Failed to convert PCM data: {e}")
            
            return audio_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepInfra API request failed: {str(e)}")
            raise ValueError(f"Failed to generate speech using DeepInfra Kokoro: {str(e)}")
        except Exception as e:
            logger.error(f"Error in DeepInfra TTS: {str(e)}")
            raise ValueError(f"Failed to generate speech using DeepInfra Kokoro: {str(e)}")
    
    def _deepinfra_text_to_speech_with_timestamps(self, text: str, filename: str) -> tuple[str, List[Dict[str, Any]]]:
        """Convert text to speech using DeepInfra Kokoro API and return timestamps"""
        try:
            logger.debug(f"Converting text to speech with DeepInfra Kokoro: {text[:50]}...")
            
            # DeepInfra Kokoro API endpoint and payload
            url = config.tts_deepinfra_url
            payload = {
                "text": text,
                "preset_voice": ["am_michael", "am_echo"],
                "output_format": "pcm",  # Use PCM format for streaming
                "speed": 1.0,
                "sample_rate": 24000,  # Use DeepInfra's preferred sample rate
                "return_timestamps": True
            }
            
            headers = {
                "Authorization": f"bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract word timestamps
            word_timestamps = []
            if "words" in result and result["words"]:
                word_timestamps = result["words"]
                logger.info(f"Received {len(word_timestamps)} word timestamps")
                logger.debug(f"Sample word timestamps: {word_timestamps[:3]}...")
            else:
                logger.warning("No word timestamps received from DeepInfra API")
            
            # Check if audio is present
            if "audio" not in result or result["audio"] is None:
                raise ValueError(f"No audio in response. Full response: {result}")
            
            # Process audio (same logic as _deepinfra_text_to_speech)
            audio_data_url = result["audio"]
            logger.debug(f"Received audio data URL: {audio_data_url[:100]}...")
            
            # Extract base64 data from data URL and parse sample rate
            sample_rate = 22050  # Default
            if audio_data_url.startswith("data:audio/"):
                try:
                    data_prefix, audio_b64 = audio_data_url.split(',', 1)
                    logger.debug(f"Data URL format detected: {data_prefix}")
                    
                    # Extract sample rate from data URL if present
                    if "rate=" in data_prefix:
                        try:
                            rate_part = data_prefix.split("rate=")[1].split(";")[0]
                            sample_rate = int(rate_part)
                            logger.debug(f"Detected sample rate from data URL: {sample_rate}Hz")
                        except (IndexError, ValueError) as e:
                            logger.warning(f"Failed to parse sample rate from data URL, using default: {e}")
                            
                except ValueError:
                    raise ValueError(f"Invalid data URL format: {audio_data_url[:100]}")
            else:
                # Fallback: assume it's raw base64
                audio_b64 = audio_data_url
                logger.debug("Assuming raw base64 format")
            
            # Decode base64 PCM data
            missing_padding = len(audio_b64) % 4
            if missing_padding:
                audio_b64 += '=' * (4 - missing_padding)
            
            pcm_data = base64.b64decode(audio_b64)
            logger.debug(f"Decoded {len(pcm_data)} bytes of PCM data")
            
            # Convert PCM to WAV using AudioSegment with detected parameters
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{filename}.wav")
            
            try:
                # Create AudioSegment from raw PCM data with detected sample rate
                audio_segment = AudioSegment(
                    data=pcm_data,
                    sample_width=2,     # 16-bit = 2 bytes
                    frame_rate=sample_rate,  # Use detected sample rate
                    channels=1          # Mono
                )
                
                # Export as WAV for compatibility
                audio_segment.export(audio_path, format="wav")
                
                logger.debug(f"DeepInfra PCM converted to WAV: {audio_path}")
                
            except Exception as e:
                logger.error(f"PCM to WAV conversion failed: {e}")
                # Fallback: save raw PCM and try to convert with ffmpeg
                raw_path = os.path.join(temp_dir, f"{filename}.pcm")
                with open(raw_path, "wb") as f:
                    f.write(pcm_data)
                
                try:
                    import subprocess
                    # Convert PCM to WAV using ffmpeg
                    cmd = [
                        'ffmpeg', '-y', '-f', 's16le', '-ar', str(sample_rate), '-ac', '1',
                        '-i', raw_path, audio_path
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    os.remove(raw_path)  # Clean up raw file
                    logger.debug(f"PCM converted to WAV using ffmpeg: {audio_path}")
                except Exception as e2:
                    logger.error(f"FFmpeg conversion also failed: {e2}")
                    raise ValueError(f"Failed to convert PCM data: {e}")
            
            return audio_path, word_timestamps
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepInfra API request failed: {str(e)}")
            raise ValueError(f"Failed to generate speech using DeepInfra Kokoro: {str(e)}")
        except Exception as e:
            logger.error(f"Error in DeepInfra TTS: {str(e)}")
            raise ValueError(f"Failed to generate speech using DeepInfra Kokoro: {str(e)}")
    
    def _create_silence(self, duration_seconds: float, filename: str) -> str:
        """Create a silent audio segment"""
        silence = AudioSegment.silent(duration=int(duration_seconds * 1000))
        
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"{filename}.mp3")
        
        silence.export(audio_path, format="mp3")
        return audio_path
    
    def combine_audio_chunks(self, audio_files: List[str]) -> str:
        """Combine audio chunks into a single file"""
        combined_audio = AudioSegment.empty()

        logger.info(f"Combining {len(audio_files)} audio chunks")
        for i, audio_file in enumerate(audio_files):
            try:
                logger.debug(f"Loading chunk {i+1}/{len(audio_files)}: {audio_file}")

                # Check if file exists before trying to load
                if not os.path.exists(audio_file):
                    logger.error(f"CRITICAL: Audio file does not exist: {audio_file}")
                    logger.error(f"This is chunk {i+1}/{len(audio_files)}")
                    continue

                # Auto-detect format based on file extension and try appropriate loader
                if audio_file.endswith('.wav'):
                    segment = AudioSegment.from_wav(audio_file)
                elif audio_file.endswith('.mp3'):
                    segment = AudioSegment.from_mp3(audio_file)
                else:
                    # Try generic file loader as fallback
                    segment = AudioSegment.from_file(audio_file)

                # Use crossfade for smooth transitions (except for first segment)
                if len(combined_audio) > 0:
                    # 50ms crossfade for natural flow
                    combined_audio = combined_audio.append(segment, crossfade=50)
                else:
                    # First segment - no crossfade needed
                    combined_audio += segment

                logger.debug(f"Successfully combined chunk {i+1}/{len(audio_files)}")

            except Exception as e:
                logger.error(f"CRITICAL: Failed to load audio file {i+1}/{len(audio_files)}: {audio_file}")
                logger.error(f"Error: {str(e)}")
                logger.error(f"File exists: {os.path.exists(audio_file)}")
                if os.path.exists(audio_file):
                    logger.error(f"File size: {os.path.getsize(audio_file)} bytes")
                continue
        
        # Export combined audio
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "combined_podcast.mp3")
        
        combined_audio.export(output_path, format="mp3", bitrate="128k")
        
        # Clean up individual chunks
        for audio_file in audio_files:
            try:
                os.remove(audio_file)
            except:
                pass
        
        logger.info(f"Combined audio saved to {output_path}")
        return output_path

    def _fal_text_to_speech(self, text: str, filename: str) -> str:
        """Convert text to speech using Fal.ai Dia 1.6 TTS"""
        try:
            import fal_client

            logger.debug(f"Converting text to speech with Fal.ai Dia: {text[:50]}...")

            # Format text with speaker label for Dia TTS dialogue model
            # Dia expects format like "[S1] text here"
            formatted_text = f"[S1] {text}"

            # Make API request (API key is read from FAL_KEY environment variable)
            result = fal_client.submit(
                "fal-ai/dia-tts",
                arguments={"text": formatted_text}
            )

            # Wait for result
            output = result.get()

            # Get audio URL from response
            audio_url = output.get("audio", {}).get("url")
            if not audio_url:
                raise ValueError(f"No audio URL in response: {output}")

            logger.info(f"Fal.ai returned audio URL: {audio_url[:80]}...")

            # Download audio file
            audio_response = requests.get(audio_url, timeout=60)
            audio_response.raise_for_status()

            # Save to temp file (Fal returns MP3)
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{filename}.mp3")

            with open(audio_path, "wb") as f:
                f.write(audio_response.content)

            logger.debug(f"Fal.ai audio saved to: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Failed to generate speech using Fal.ai TTS: {str(e)}")
            raise ValueError(f"Failed to generate speech using Fal.ai TTS: {str(e)}")