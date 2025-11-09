'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useData } from '@/contexts/DataContext'
import { EpisodePlayer } from './EpisodePlayer'
import { getUIConfig } from '@/config/app-config'

interface EpisodeListItem {
  id: string;
  title: string;
  description: string;
  created_at: string;
  duration_seconds: number;
  audio_url: string;
}

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

export function PastEpisodesPage() {
  const { getIdToken } = useAuth()
  const { currentEpisode } = useData()
  const uiConfig = getUIConfig()
  const [allEpisodes, setAllEpisodes] = useState<EpisodeListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedEpisodeId, setExpandedEpisodeId] = useState<string | null>(null)
  const [fullEpisodeData, setFullEpisodeData] = useState<{ [key: string]: Episode }>({})
  const containerRef = useRef<HTMLDivElement>(null)
  const episodeRefs = useRef<{ [key: string]: HTMLDivElement | null }>({})

  // Filter episodes based on search query
  const episodes = useMemo(() => {
    if (!searchQuery) return allEpisodes

    return allEpisodes.filter((ep) =>
      ep.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ep.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [allEpisodes, searchQuery])

  // Fetch episodes and preload all full data
  useEffect(() => {
    fetchEpisodesAndPreload()
  }, [currentEpisode])

  const fetchEpisodesAndPreload = async () => {
    try {
      const token = await getIdToken()
      if (!token) {
        setError('Please sign in to view your episodes')
        setIsLoading(false)
        return
      }

      // Fetch 6 episodes so we have 5 after filtering out current episode
      const url = '/api/episodes/list?limit=6'

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch episodes')
      }

      const data = await response.json()
      const episodesList = data.episodes || []

      // Filter out the current episode from the homepage
      const allEpisodes = currentEpisode
        ? episodesList.filter((ep: EpisodeListItem) => ep.id !== currentEpisode.id)
        : episodesList

      // Take only first 5 after filtering
      const limitedEpisodes = allEpisodes.slice(0, 5)

      setAllEpisodes(limitedEpisodes)

      // Preload full data for all episodes in parallel
      const fullDataPromises = episodesList.map(async (episode: EpisodeListItem) => {
        try {
          const episodeResponse = await fetch(`/api/episodes/${episode.id}`)
          if (episodeResponse.ok) {
            const fullEpisode = await episodeResponse.json()
            return { id: episode.id, data: fullEpisode }
          }
        } catch (err) {
          console.error(`Failed to preload episode ${episode.id}:`, err)
        }
        return null
      })

      const fullDataResults = await Promise.all(fullDataPromises)

      // Build the full episode data map
      const preloadedData: { [key: string]: Episode } = {}
      fullDataResults.forEach(result => {
        if (result) {
          preloadedData[result.id] = result.data
        }
      })

      setFullEpisodeData(preloadedData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const pauseAllAudio = () => {
    // Find all audio elements on the page and pause them
    const audioElements = document.querySelectorAll('audio')
    audioElements.forEach(audio => {
      if (!audio.paused) {
        audio.pause()
      }
    })
  }

  const handleEpisodeClick = (episodeId: string) => {
    // Toggle expansion - data is already preloaded
    if (expandedEpisodeId === episodeId) {
      // Closing the card - pause audio first
      pauseAllAudio()
      setExpandedEpisodeId(null)
    } else {
      setExpandedEpisodeId(episodeId)
      // Scroll to top when expanding an archive card
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 pb-24" ref={containerRef}>
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-650 text-maroon-800 mb-2 lowercase">
          listen to <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">your</span> past podcasts.
        </h1>
      </div>

      {/* Search Bar - Hidden when episode expanded */}
      <div className={`mb-8 transition-all duration-500 ${
        expandedEpisodeId ? 'opacity-0 h-0 overflow-hidden' : 'opacity-100'
      }`}>
        <div className="relative z-0">
            <svg
              className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-tan-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search episodes by title or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-tan-300 focus:outline-none focus:ring-2 focus:ring-maroon-500 focus:border-transparent text-maroon-800 placeholder-tan-500"
            />
          </div>
        </div>

      {/* Episode List */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="border border-tan-200 rounded-xl p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-3 w-2/3"></div>
              <div className="h-3 bg-gray-200 rounded mb-2 w-full"></div>
              <div className="h-3 bg-gray-200 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-8 bg-maroon-50 rounded-xl text-center">
          <p className="text-maroon-700 font-medium">{error}</p>
        </div>
      ) : episodes.length === 0 ? (
        <div className="p-12 bg-gradient-to-r from-cream-100 to-tan-100 rounded-2xl text-center">
          <svg className="w-16 h-16 text-tan-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
          <h3 className="text-xl font-bold text-maroon-800 mb-2">
            {searchQuery ? 'No episodes found' : 'No past episodes yet'}
          </h3>
          <p className="text-tan-700">
            {searchQuery
              ? 'Try a different search term'
              : 'Generate your first podcast to see it here!'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {episodes.map((episode) => {
            const isExpanded = expandedEpisodeId === episode.id
            const isHidden = expandedEpisodeId && expandedEpisodeId !== episode.id
            const fullEpisode = fullEpisodeData[episode.id]

            // Don't render hidden cards at all
            if (isHidden) return null

            return (
              <div
                key={episode.id}
                ref={(el) => { episodeRefs.current[episode.id] = el }}
                className="relative z-0 bg-cream-100 rounded-xl border border-tan-200 overflow-visible transition-all duration-500 ease-in-out"
              >
                <button
                  onClick={() => handleEpisodeClick(episode.id)}
                  className="w-full p-6 text-left"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold text-maroon-800 mb-2">{episode.title}</h3>
                      <p className="text-tan-700 text-sm font-normal">{episode.description}</p>
                    </div>
                    <svg
                      className={`w-6 h-6 text-tan-500 ml-4 flex-shrink-0 transition-transform duration-500 ${
                        isExpanded ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                  {/* Always show date/time info */}
                  <div className="flex items-center space-x-4 text-xs text-tan-600">
                    <span className="flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {formatDate(episode.created_at)}
                    </span>
                    <span className="flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {formatDuration(episode.duration_seconds)}
                    </span>
                  </div>
                </button>

                {/* Player - smoothly expands with proper overflow control */}
                <div
                  className={`transition-all duration-500 ease-in-out ${
                    isExpanded
                      ? 'max-h-[3000px] opacity-100'
                      : 'max-h-0 opacity-0 overflow-hidden'
                  }`}
                >
                  <div className="border-t border-tan-200 overflow-visible">
                    {fullEpisode && (
                      <div className="px-6 pb-6 pt-4 overflow-visible">
                        <EpisodePlayer episode={fullEpisode} compact />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

