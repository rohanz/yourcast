'use client'

import { useState, useRef, useEffect } from 'react'
import { getUIConfig } from '@/config/app-config'
import { useAudio } from '@/contexts/AudioContext'

interface Episode {
  id: string;
  title: string;
  description?: string;
  duration_seconds: number;
  topics: string[];
  status: string;
  audio_url?: string;
  transcript_url?: string;
  vtt_url?: string;
  created_at: string;
}

interface EpisodeSegment {
  id: string;
  episode_id: string;
  start_time: number;
  end_time: number;
  text: string;
  source_id?: string;
  order_index: number;
}

interface Source {
  id: string;
  episode_id: string;
  title: string;
  url: string;
  published_date: string;
  excerpt?: string;
  summary?: string;
}

interface EpisodePlayerProps {
  episode: Episode
  compact?: boolean
}

export function EpisodePlayer({ episode, compact = false }: EpisodePlayerProps) {
  // Get configuration
  const uiConfig = getUIConfig()
  const { registerAudio, unregisterAudio } = useAudio()
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playbackSpeed, setPlaybackSpeed] = useState(uiConfig.player.defaultSpeed)
  const [speedAnimating, setSpeedAnimating] = useState(false)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [hoverPosition, setHoverPosition] = useState<number | null>(null)
  const [segments, setSegments] = useState<EpisodeSegment[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    // Fetch episode segments and sources
    const fetchEpisodeData = async () => {
      try {
        const [segmentsRes, sourcesRes] = await Promise.all([
          fetch(`/api/episodes/${episode.id}/segments`),
          fetch(`/api/episodes/${episode.id}/sources`)
        ])

        if (segmentsRes.ok) {
          const segmentsData = await segmentsRes.json()
          setSegments(segmentsData)
        }

        if (sourcesRes.ok) {
          const sourcesData = await sourcesRes.json()
          setSources(sourcesData)
        }
      } catch (error) {
        console.error('Failed to fetch episode data:', error)
      }
    }

    fetchEpisodeData()
  }, [episode.id, episode.transcript_url])

  // Industry standard: Register audio element with AudioContext for centralized control
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    // Register audio element for centralized pause control (like Spotify/YouTube)
    registerAudio(episode.id, audio)

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleDurationChange = () => setDuration(audio.duration)
    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('durationchange', handleDurationChange)
    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('durationchange', handleDurationChange)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      // Unregister on cleanup
      unregisterAudio(episode.id)
    }
  }, [episode.id, registerAudio, unregisterAudio])

  const togglePlayPause = () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
    } else {
      audio.play()
    }
  }

  const seekTo = (time: number) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = time
  }

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const getCurrentSegment = () => {
    return segments.find(
      segment => currentTime >= segment.start_time && currentTime <= segment.end_time
    )
  }

  const handleSpeedChange = (speed: number) => {
    const audio = audioRef.current
    if (!audio) return
    
    audio.playbackRate = speed
    setPlaybackSpeed(speed)
  }

  const cycleSpeed = () => {
    const speedOrder = uiConfig.player.speedOptions
    const currentIndex = speedOrder.indexOf(playbackSpeed)
    const nextIndex = (currentIndex + 1) % speedOrder.length
    const newSpeed = speedOrder[nextIndex]

    // Trigger fade out animation
    setSpeedAnimating(true)

    // Update speed after fade out completes, then fade in
    setTimeout(() => {
      handleSpeedChange(newSpeed)

      // End animation after fade in completes
      setTimeout(() => {
        setSpeedAnimating(false)
      }, 100)
    }, 100)
  }

  const skip = (seconds: number) => {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = Math.max(0, Math.min(audio.currentTime + seconds, duration))
  }

  const toggleMute = () => {
    const audio = audioRef.current
    if (!audio) return

    if (isMuted) {
      audio.volume = volume
      setIsMuted(false)
    } else {
      audio.volume = 0
      setIsMuted(true)
    }
  }

  const handleVolumeChange = (newVolume: number) => {
    const audio = audioRef.current
    if (!audio) return

    setVolume(newVolume)
    audio.volume = newVolume
    if (newVolume > 0 && isMuted) {
      setIsMuted(false)
    }
  }

  const currentSegment = getCurrentSegment()

  return (
    <div className={compact ? "" : "bg-cream-100 rounded-lg shadow-md overflow-hidden border border-tan-300"}>
      <div className={compact ? "" : "p-6"}>
        {!compact && (
          <>
            <h3 className="text-xl font-bold text-maroon-800 mb-2">{episode.title}</h3>
            <p className="text-tan-700 mb-4">{episode.description}</p>
          </>
        )}

        {episode.audio_url && (
          <div className={compact ? "space-y-4" : "space-y-4"}>
            <audio ref={audioRef} src={episode.audio_url} preload="metadata" />

            {/* Progress Bar */}
            <div className="w-full">
              <div
                className="w-full bg-tan-200 rounded-full h-2 cursor-pointer relative overflow-hidden"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect()
                  const x = e.clientX - rect.left
                  const percentage = x / rect.width
                  seekTo(percentage * duration)
                }}
                onMouseMove={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect()
                  const x = e.clientX - rect.left
                  const percentage = (x / rect.width) * 100
                  setHoverPosition(percentage)
                }}
                onMouseLeave={() => setHoverPosition(null)}
              >
                {/* Hover preview */}
                {hoverPosition !== null && (
                  <div
                    className="absolute top-0 left-0 h-full bg-tan-300 opacity-50 rounded-full transition-all"
                    style={{ width: `${hoverPosition}%` }}
                  />
                )}
                {/* Current progress */}
                <div
                  className="absolute top-0 left-0 bg-maroon-600 h-2 rounded-full transition-all"
                  style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Player Controls - Responsive layout */}
            <div className="flex flex-col md:flex-row md:items-center gap-3 md:gap-0">
              {/* Mobile: Centered playback controls */}
              <div className="flex items-center justify-center space-x-2 md:hidden">
                {/* Skip back 15s */}
                <button
                  onClick={() => skip(-15)}
                  className="text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 p-2 rounded-full transition-colors"
                  title="Skip back 15 seconds"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7M18 19l-7-7 7-7"/>
                  </svg>
                </button>

                {/* Play/Pause button */}
                <button
                  onClick={togglePlayPause}
                  className="bg-maroon-600 hover:bg-maroon-700 text-white p-3 rounded-full transition-colors flex-shrink-0"
                >
                  {isPlaying ? (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  )}
                </button>

                {/* Skip forward 15s */}
                <button
                  onClick={() => skip(15)}
                  className="text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 p-2 rounded-full transition-colors"
                  title="Skip forward 15 seconds"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M6 5l7 7-7 7"/>
                  </svg>
                </button>
              </div>

              {/* Desktop: All controls in one row */}
              <div className="hidden md:flex md:relative md:items-center md:w-full">
                {/* Left: Current time */}
                <div className="text-sm text-tan-600 min-w-[3rem]">
                  {formatTime(currentTime)}
                </div>

                {/* Center: Playback controls - absolutely centered relative to parent */}
                <div className="absolute left-1/2 -translate-x-1/2 flex items-center space-x-2">
                  {/* Skip back 15s */}
                  <button
                    onClick={() => skip(-15)}
                    className="text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 p-2 rounded-full transition-colors"
                    title="Skip back 15 seconds"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7M18 19l-7-7 7-7"/>
                    </svg>
                  </button>

                  {/* Play/Pause button */}
                  <button
                    onClick={togglePlayPause}
                    className="bg-maroon-600 hover:bg-maroon-700 text-white p-3 rounded-full transition-colors flex-shrink-0"
                  >
                    {isPlaying ? (
                      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                      </svg>
                    ) : (
                      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    )}
                  </button>

                  {/* Skip forward 15s */}
                  <button
                    onClick={() => skip(15)}
                    className="text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 p-2 rounded-full transition-colors"
                    title="Skip forward 15 seconds"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M6 5l7 7-7 7"/>
                    </svg>
                  </button>
                </div>

                {/* Right: Speed, Volume, and Total time */}
                <div className="ml-auto flex items-center space-x-2">
                  {/* Speed Control */}
                  <button
                    onClick={cycleSpeed}
                    className="px-2 py-1 text-sm font-bold text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 rounded cursor-pointer select-none w-[3.5rem] text-center transition-colors duration-200"
                  >
                    <span
                      className={`inline-block transition-opacity duration-100 ${
                        speedAnimating ? 'opacity-0' : 'opacity-100'
                      }`}
                    >
                      {playbackSpeed}x
                    </span>
                  </button>

                  {/* Volume Control */}
                  <div className="relative flex items-center group z-10">
                    <button
                      onClick={toggleMute}
                      className="text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 p-2 rounded transition-colors relative z-10"
                      title={isMuted ? "Unmute" : "Mute"}
                    >
                      {isMuted || volume === 0 ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                        </svg>
                      )}
                    </button>

                    {/* Hover bridge - invisible area connecting button to slider */}
                    <div className="absolute right-0 bottom-0 h-32 w-12 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto" />

                    {/* Volume slider on hover */}
                    <div className="absolute right-0 bottom-full mb-2 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-opacity duration-200">
                      <div className="bg-cream-50 border border-tan-300 rounded-lg shadow-lg p-3">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={isMuted ? 0 : volume}
                          onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                          className="h-20 w-2 cursor-pointer slider-vertical"
                          style={{
                            background: `linear-gradient(to top, rgb(120, 53, 15) ${(isMuted ? 0 : volume) * 100}%, rgb(214, 197, 178) ${(isMuted ? 0 : volume) * 100}%)`,
                            writingMode: 'vertical-lr' as any,
                            direction: 'rtl' as any,
                          }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Total time */}
                  <div className="text-sm text-tan-600 min-w-[3rem] text-right">
                    {formatTime(duration)}
                  </div>
                </div>
              </div>

              {/* Mobile: Time and controls row */}
              <div className="flex items-center justify-between md:hidden">
                <div className="text-sm text-tan-600">
                  {formatTime(currentTime)}
                </div>
                <div className="flex items-center space-x-2">
                  {/* Speed Control */}
                  <button
                    onClick={cycleSpeed}
                    className="px-2 py-1 text-sm font-bold text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 rounded cursor-pointer select-none w-[3rem] text-center transition-colors duration-200"
                  >
                    <span
                      className={`inline-block transition-opacity duration-100 ${
                        speedAnimating ? 'opacity-0' : 'opacity-100'
                      }`}
                    >
                      {playbackSpeed}x
                    </span>
                  </button>

                  {/* Volume Control - Hidden on mobile, shown on desktop */}
                  <div className="relative hidden md:flex items-center group z-10">
                    <button
                      onClick={toggleMute}
                      className="text-maroon-600 hover:text-maroon-700 hover:bg-maroon-50 p-2 rounded transition-colors relative z-10"
                      title={isMuted ? "Unmute" : "Mute"}
                    >
                      {isMuted || volume === 0 ? (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                        </svg>
                      )}
                    </button>

                    {/* Hover bridge - invisible area connecting button to slider */}
                    <div className="absolute right-0 bottom-0 h-32 w-12 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto" />

                    {/* Volume slider on hover */}
                    <div className="absolute right-0 bottom-full mb-2 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-opacity duration-200">
                      <div className="bg-cream-50 border border-tan-300 rounded-lg shadow-lg p-3">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={isMuted ? 0 : volume}
                          onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                          className="h-20 w-2 cursor-pointer slider-vertical"
                          style={{
                            background: `linear-gradient(to top, rgb(120, 53, 15) ${(isMuted ? 0 : volume) * 100}%, rgb(214, 197, 178) ${(isMuted ? 0 : volume) * 100}%)`,
                            writingMode: 'vertical-lr' as any,
                            direction: 'rtl' as any,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="text-sm text-tan-600">
                  {formatTime(duration)}
                </div>
              </div>
            </div>

            {/* Chapter Navigation */}
            {segments.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-maroon-800">Chapters</h4>
                <div className="space-y-1">
                  {segments.map((segment) => (
                    <button
                      key={segment.id}
                      onClick={() => seekTo(segment.start_time)}
                      className={`w-full text-left p-2 rounded text-sm hover:bg-cream-200 transition-colors ${
                        currentSegment?.id === segment.id ? 'bg-maroon-50 text-maroon-700' : 'text-tan-700'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="flex-1">{segment.text.slice(0, 100)}...</span>
                        <span className="text-xs ml-2">{formatTime(segment.start_time)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Sources */}
            {sources.length > 0 && (
              <div className={compact ? "pt-4 border-t border-tan-200" : "border-t border-tan-200 bg-tan-50/30 -mx-6 -mb-6 p-6 mt-6"}>
                <h4 className="font-normal text-maroon-800 mb-4">
                  Sources
                </h4>
                <div className="space-y-3">
                  {sources.map((source) => (
                    <div key={source.id} className="bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow border border-tan-100">
                      <h5 className="font-semibold text-sm text-maroon-800 mb-2">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-maroon-600 transition-colors hover:underline"
                        >
                          {source.title}
                        </a>
                      </h5>
                      <p className="text-sm text-tan-700 font-light mb-2 line-clamp-2">{source.excerpt}</p>
                      <p className="text-xs text-tan-600 font-light">
                        {new Date(source.published_date).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}