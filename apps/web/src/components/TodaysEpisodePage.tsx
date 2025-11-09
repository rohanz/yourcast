'use client'

import { useState, useEffect, useRef } from 'react'
import { flushSync } from 'react-dom'
import { EpisodePlayer } from './EpisodePlayer'
import { useAuth } from '@/contexts/AuthContext'
import { useData } from '@/contexts/DataContext'
import { getLimitsConfig, getUIConfig } from '@/config/app-config'

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
  chapters?: { title: string }[];
}

function getStageMessage(stage: string): string {
  switch (stage) {
    case 'Starting...':
    case 'discovering_articles':
    case 'pending':
      return 'leafing through the newspapers...'
    case 'extracting_content':
      return 'picking your favourite articles...'
    case 'generating_script':
      return 'writing the perfect script...'
    case 'generating_audio':
      return 'recording the podcast in the studio...'
    case 'generating_timestamps':
    case 'uploading_files':
    case 'finalizing':
      return 'sending it over to you...'
    case 'completed':
      return 'ready to listen!'
    default:
      return 'leafing through the newspapers...'
  }
}

const stageProgressMap: Record<string, number> = {
  'leafing through the newspapers...': 10,
  'picking your favourite articles...': 30,
  'writing the perfect script...': 50,
  'recording the podcast in the studio...': 70,
  'sending it over to you...': 90,
  'ready to listen!': 100,
}

export function TodaysEpisodePage() {
  const { getIdToken } = useAuth()
  const { userPreferences, setGenerateEpisode, isGenerating, setIsGenerating, pastEpisodes, setPastEpisodes, currentEpisode: contextCurrentEpisode, setCurrentEpisode: setContextCurrentEpisode, isCheckingInitialLoad, setIsCheckingInitialLoad } = useData()
  const limitsConfig = getLimitsConfig()
  const uiConfig = getUIConfig()

  const [currentEpisode, setCurrentEpisode] = useState<Episode | null>(null)
  const [isChecking, setIsChecking] = useState(true)
  const [stageMessage, setStageMessage] = useState<string>('leafing through the newspapers...')
  const [error, setError] = useState<string | null>(null)
  const [hasPreferences, setHasPreferences] = useState(false)
  const [showChapters, setShowChapters] = useState(false)
  const [playerReady, setPlayerReady] = useState(false)

  const eventSourceRef = useRef<EventSource | null>(null)
  const completedRef = useRef(false)
  const maxProgressRef = useRef(0)

  // Reset player ready state when episode changes
  useEffect(() => {
    if (currentEpisode?.id) {
      setPlayerReady(false)
      // Give player time to mount and load data
      const timer = setTimeout(() => setPlayerReady(true), 300)
      return () => clearTimeout(timer)
    }
  }, [currentEpisode?.id])

  // Check if user has episode for today and preferences on mount
  useEffect(() => {
    const checkTodaysEpisode = async () => {
      // Don't check if we're currently generating an episode
      if (isGenerating) {
        return
      }

      try {
        const token = await getIdToken()
        if (!token) {
          setError('Please sign in to view your episode')
          setIsChecking(false)
          return
        }

        // Check preferences first
        const prefsResponse = await fetch('/api/users/preferences', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (prefsResponse.ok) {
          const prefsData = await prefsResponse.json()
          const hasSubcategories = prefsData.preferences?.subcategories?.length > 0
          const hasCustomTags = prefsData.preferences?.custom_tags?.length > 0

          if (hasSubcategories || hasCustomTags) {
            setHasPreferences(true)

            // Check for today's episode
            const response = await fetch('/api/episodes/today/check', {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            })

            if (!response.ok) {
              throw new Error('Failed to check today\'s episode')
            }

            const data = await response.json()

            if (data.has_episode) {
              console.log('✅ Episode found for today:', data)
              // Episode exists, check its status
              if (data.status === 'completed') {
                // Fetch full episode details
                console.log('📥 Fetching completed episode:', data.episode_id)
                const episodeResponse = await fetch(`/api/episodes/${data.episode_id}`)
                if (episodeResponse.ok) {
                  const episode = await episodeResponse.json()
                  console.log('✅ Episode loaded:', episode)
                  setCurrentEpisode(episode)
                  setContextCurrentEpisode(episode) // Also update context so archive can filter it
                } else {
                  console.error('❌ Failed to fetch episode:', episodeResponse.status)
                }
              } else {
                console.log('⏳ Episode still generating, starting monitoring')
                // Episode is still generating, start listening to updates
                startGenerationMonitoring(data.episode_id)
              }
            } else {
              console.log('ℹ️ No episode found for today')
            }
            // No auto-generation - user must click button to generate
          } else {
            setHasPreferences(false)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred')
      } finally {
        setIsChecking(false)
        setIsCheckingInitialLoad(false)
      }
    }

    checkTodaysEpisode()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [getIdToken, userPreferences])

  // Register generate episode function with context
  useEffect(() => {
    const handleGenerateEpisode = async () => {
      try {
        // Set generating state immediately to prevent flicker
        setIsGenerating(true)

        // Reset progress bar to 0 to prevent sliding back from 100%
        maxProgressRef.current = 0

        // Reset stage message immediately to prevent showing old "ready to listen" message
        setStageMessage('leafing through the newspapers...')

        // Close any existing SSE connection before starting new generation
        if (eventSourceRef.current) {
          console.log('Closing existing SSE connection before new generation')
          eventSourceRef.current.close()
          eventSourceRef.current = null
        }

        // Move current episode to past episodes if it exists (regardless of status)
        if (currentEpisode) {
          const updatedPastEpisodes = pastEpisodes ? [currentEpisode, ...pastEpisodes] : [currentEpisode]
          setPastEpisodes(updatedPastEpisodes)
        }

        // Clear current episode and reset states
        setCurrentEpisode(null)
        setIsChecking(false)
        setError(null)

        const token = await getIdToken()
        if (!token) {
          setError('Please sign in to generate a podcast')
          setIsGenerating(false)
          return
        }

        // Fetch latest preferences
        const prefsResponse = await fetch('/api/users/preferences', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (prefsResponse.ok) {
          const prefsData = await prefsResponse.json()
          const hasSubcategories = prefsData.preferences?.subcategories?.length > 0
          const hasCustomTags = prefsData.preferences?.custom_tags?.length > 0

          if (hasSubcategories || hasCustomTags) {
            setHasPreferences(true)
            await startGeneration(prefsData.preferences.subcategories || [])
          } else {
            setError('Please set your preferences first')
            setIsGenerating(false)
          }
        }
      } catch (err) {
        setError('Failed to start generation. Please try again.')
        setIsGenerating(false)
      }
    }

    setGenerateEpisode(handleGenerateEpisode)

    return () => {
      setGenerateEpisode(null)
    }
  }, [getIdToken, setGenerateEpisode, currentEpisode, pastEpisodes, setPastEpisodes])

  const startGeneration = async (subcategories: string[]) => {
    setIsGenerating(true)
    setError(null)
    setStageMessage('leafing through the newspapers...')
    completedRef.current = false
    maxProgressRef.current = 0  // Reset progress for new generation

    try {
      const token = await getIdToken()
      if (!token) {
        throw new Error('Please sign in to generate a podcast')
      }

      const response = await fetch('/api/episodes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          subcategories: subcategories,
          duration_minutes: limitsConfig.defaultEpisodeDuration
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create episode')
      }

      const { episode_id } = await response.json()
      startGenerationMonitoring(episode_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setIsGenerating(false)
    }
  }

  const startGenerationMonitoring = (episodeId: string) => {
    setIsGenerating(true)
    setStageMessage('leafing through the newspapers...')

    const eventSource = new EventSource(`/api/episodes/${episodeId}/events`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log('✅ SSE connection established')
    }

    eventSource.onmessage = (event) => {
      try {
        const statusData = JSON.parse(event.data)

        if (statusData.stage) {
          const newMessage = getStageMessage(statusData.stage)
          flushSync(() => {
            setStageMessage(newMessage)
          })
        }

        if (statusData.status === 'completed') {
          completedRef.current = true
          flushSync(() => {
            setStageMessage('Ready to listen!')
          })

          fetch(`/api/episodes/${episodeId}`)
            .then(res => res.json())
            .then((episode: Episode) => {
              setCurrentEpisode(episode)
              setContextCurrentEpisode(episode) // Also update context so archive can filter it
              setIsGenerating(false)
              if (eventSourceRef.current) {
                eventSourceRef.current.close()
                eventSourceRef.current = null
              }
            })
            .catch((err) => {
              setError('Episode completed but failed to load details')
              setIsGenerating(false)
              if (eventSourceRef.current) {
                eventSourceRef.current.close()
                eventSourceRef.current = null
              }
            })
        } else if (statusData.status === 'failed') {
          flushSync(() => {
            setError(statusData.error || 'Failed to generate podcast. Please try again.')
            setIsGenerating(false)
          })
          if (eventSourceRef.current) {
            eventSourceRef.current.close()
            eventSourceRef.current = null
          }
        }
      } catch {
        // Ignore non-JSON frames
        return
      }
    }

    eventSource.onerror = (error) => {
      if (!completedRef.current) {
        console.log('❌ SSE connection issue (will auto-retry):', error)
      }
    }
  }

  const progressPercent = stageProgressMap[stageMessage] ?? 0
  // Track max progress to prevent bar from going backwards during fade out
  maxProgressRef.current = Math.max(maxProgressRef.current, progressPercent)
  const displayProgress = maxProgressRef.current

  const renderEmptyState = () => {
    let icon = null
    let title = ''
    let message = ''

    // Check both local state and context for preferences
    const hasPrefs = hasPreferences || (userPreferences?.subcategories && userPreferences.subcategories.length > 0)

    if (isChecking) {
      // Welcome screen is handled by the fixed overlay above
      return null
    } else if (!hasPrefs) {
      title = 'welcome!'
      message = 'to get started, go to the personalize tab, save your topics, then click generate!'
    } else if (error) {
      title = 'Error'
      message = error
    } else if (hasPrefs && !currentEpisode && !isGenerating) {
      // User has preferences but no episode today (didn't listen to yesterday's or first time)
      title = 'no podcast today yet.'
      message = 'click the button below to generate your daily podcast!'
    }

    return (
      <div className="max-w-2xl mx-auto px-6 py-10 bg-gradient-to-r from-cream-100 to-tan-100 rounded-2xl shadow-md text-center">
        {title && <h2 className="text-3xl font-semibold text-maroon-800 mb-4">{title}</h2>}
        {message && <p className="text-maroon-700 text-base font-light">{message}</p>}
      </div>
    )
  }

  // Format current date for hero header
  const currentDate = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).toLowerCase()

  return (
    <>
      {/* Welcome Screen - Fades in, fades out when ready */}
      <div className={`fixed inset-0 flex items-center justify-center z-50 bg-white transition-opacity duration-500 ease-out ${isChecking ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
        <div className="text-center px-6 animate-fadeIn">
          <h2 className="text-5xl font-650 text-maroon-800 mb-6 lowercase">
            welcome to <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">your</span>cast!
          </h2>
          <p className="text-maroon-700 text-lg font-light animate-pulse">getting things ready for you...</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-12 pb-16">
        {/* Unified Empty State */}
        {!isGenerating && !currentEpisode && renderEmptyState()}

        {/* Hero Header - Only show when episode exists */}
        {currentEpisode && (
          <section className={`text-center mb-8 transition-opacity duration-500 ${
            isGenerating ? 'opacity-0' : isCheckingInitialLoad ? 'opacity-100 animate-fadeIn' : 'opacity-100'
          }`}>
            <h1 className="text-4xl font-650 text-maroon-800 mb-2 lowercase">
              here's <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">your</span> latest podcast.
            </h1>
            <p className="text-tan-700 text-lg font-light">{currentDate}</p>
          </section>
        )}

        {/* Content area - always rendered when generating or episode exists */}
        {(isGenerating || currentEpisode) && (
          <div className="relative min-h-[60vh]">
            {/* Generating Section - Absolutely positioned, vertically centered, fades in */}
            {isGenerating && (
              <div className="absolute inset-0 flex items-center justify-center animate-fadeIn">
                <div className={`w-full max-w-2xl bg-cream-100 rounded-xl border border-tan-200 overflow-hidden p-8 transition-opacity duration-500 ${
                  displayProgress < 100 ? 'opacity-100' : 'opacity-0'
                }`}>
                  <h3 className="text-2xl font-semibold text-maroon-800 mb-6 text-center lowercase">creating your personal podcast!</h3>
                  <div className="w-full bg-red-100 rounded-full h-4 overflow-hidden mb-4 relative shadow-inner">
                    <div
                      className="bg-red-400 h-4 rounded-full transition-all animate-pulse"
                      style={{
                        width: `${displayProgress}%`,
                        transitionDuration: `${uiConfig.animations.slow}ms`,
                      }}
                    />
                  </div>
                  <p className="text-center text-maroon-700 font-light text-lg animate-pulse">{stageMessage}</p>
                </div>
              </div>
            )}

            {/* Episode Player Card - Removed from layout when generating */}
            {currentEpisode && !isGenerating && (
              <div className={`relative z-0 bg-cream-100 rounded-xl border border-tan-200 overflow-hidden transition-opacity duration-500 ${
                playerReady ? 'opacity-100' : 'opacity-0'
              }`}>
          <div className="p-6">
            <h3 className="text-xl font-semibold text-maroon-800 mb-2">{currentEpisode.title}</h3>
            <p className="text-tan-700 text-sm font-normal">{currentEpisode.description}</p>
          </div>
          <div className="border-t border-tan-200 px-6 pb-6 pt-4 min-h-[280px]">
            <EpisodePlayer episode={currentEpisode} compact />
          </div>

          {/* Chapters Section */}
          {currentEpisode.chapters && currentEpisode.chapters.length > 0 && (
            <div className="border-t border-tan-200 bg-tan-50/50">
              <button
                onClick={() => setShowChapters(!showChapters)}
                className="flex items-center justify-between w-full text-left px-6 py-4 hover:bg-tan-50 transition-colors"
                aria-expanded={showChapters}
                aria-controls="chapters-section"
              >
                <span className="text-lg font-semibold text-maroon-800 flex items-center space-x-2">
                  <span aria-hidden="true">🎧</span>
                  <span>Chapters</span>
                </span>
                <svg
                  className={`w-5 h-5 text-maroon-600 transition-transform ease-[cubic-bezier(0.22,0.61,0.36,1)]`}
                  style={{
                    transform: showChapters ? 'rotate(180deg)' : 'rotate(0deg)',
                    transitionDuration: `${uiConfig.animations.slow}ms`
                  }}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div
                id="chapters-section"
                className={`overflow-hidden transition-all ease-[cubic-bezier(0.22,0.61,0.36,1)] ${
                  showChapters ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
                }`}
                style={{
                  transitionDuration: `${uiConfig.animations.slow}ms`
                }}
              >
                <ul className="px-6 pb-6 space-y-2">
                  {currentEpisode.chapters.map((chapter, idx) => (
                    <li
                      key={idx}
                      className="flex items-start bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow"
                    >
                      <span className="flex-shrink-0 w-7 h-7 rounded-full bg-maroon-100 text-maroon-700 flex items-center justify-center text-sm font-semibold mr-3">
                        {idx + 1}
                      </span>
                      <span className="text-maroon-700 font-light pt-0.5">{chapter.title}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
