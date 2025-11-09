'use client'

import { useState, useRef, useEffect } from 'react'
import { flushSync } from 'react-dom'
import { getUIConfig, getLimitsConfig } from '@/config/app-config'
import { useAuth } from '@/contexts/AuthContext'
import { GoogleSignInButton } from './GoogleSignInButton'

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

interface CreateEpisodeRequest {
  subcategories: string[];
  duration_minutes: number;
}

interface CreateEpisodeFormProps {
  onEpisodeCreated: (episode: Episode) => void
}

interface Category {
  category: string;
  subcategories: Subcategory[];
  total_articles: number;
  avg_importance: number;
  max_importance: number;
}

// Define the desired category order to match backend
const CATEGORY_ORDER = [
  "World News",
  "Politics & Government", 
  "Business",
  "Technology",
  "Science & Environment",
  "Sports", 
  "Arts & Culture",
  "Health",
  "Lifestyle"
]

interface Subcategory {
  subcategory: string;
  article_count: number;
  avg_importance: number;
  max_importance: number;
  latest_article: string | null;
}

function getStageMessage(stage: string): string {
  switch (stage) {
    case 'Starting...':
    case 'discovering_articles':
    case 'pending':
      return 'Leafing through the newspapers...'
    case 'extracting_content':
      return 'Picking your favourite articles...'
    case 'generating_script':
      return 'Writing the perfect script...'
    case 'generating_audio':
      return 'Recording the podcast in the studio...'
    case 'generating_timestamps':
    case 'uploading_files':
    case 'finalizing':
      return 'Sending it over to you...'
    case 'completed':
      return 'Ready to listen!'
    default:
      return 'Leafing through the newspapers...'
  }
}

export function CreateEpisodeForm({ onEpisodeCreated }: CreateEpisodeFormProps) {
  // Get authentication state
  const { user, getIdToken, loading: authLoading } = useAuth()

  // Get configuration
  const uiConfig = getUIConfig()
  const limitsConfig = getLimitsConfig()
  const [selectedSubcategories, setSelectedSubcategories] = useState<string[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoadingCategories, setIsLoadingCategories] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stageMessage, setStageMessage] = useState<string>('')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [limitWarning, setLimitWarning] = useState<{ categoryName: string; message: string } | null>(null)
  const [isWarningVisible, setIsWarningVisible] = useState(false)

  const eventSourceRef = useRef<EventSource | null>(null)
  const completedRef = useRef(false)
  const warningTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch categories on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await fetch('/api/categories')
        if (!response.ok) {
          throw new Error('Failed to fetch categories')
        }
        const data = await response.json()
        const rawCategories = data.categories || []
        
        // Sort categories according to predefined order
        const sortedCategories = [...rawCategories].sort((a, b) => {
          const indexA = CATEGORY_ORDER.indexOf(a.category)
          const indexB = CATEGORY_ORDER.indexOf(b.category)
          
          // If category not found in order, put it at the end
          if (indexA === -1 && indexB === -1) return 0
          if (indexA === -1) return 1
          if (indexB === -1) return -1
          
          return indexA - indexB
        })
        
        setCategories(sortedCategories)
      } catch (err) {
        setError('Failed to load categories. Please refresh the page.')
      } finally {
        setIsLoadingCategories(false)
      }
    }
    fetchCategories()
  }, [])

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  // Helper function to get subcategories for a category
  const getSubcategoriesForCategory = (categoryName: string): string[] => {
    const category = categories.find(cat => cat.category === categoryName)
    return category ? category.subcategories.map(sub => sub.subcategory) : []
  }

  // Check if all subcategories of a category are selected
  const isCategoryFullySelected = (categoryName: string): boolean => {
    const subcats = getSubcategoriesForCategory(categoryName)
    return subcats.length > 0 && subcats.every(sub => selectedSubcategories.includes(sub))
  }

  // Get total selection count for limit checking
  const getTotalSelectionCount = () => {
    return selectedSubcategories.length
  }

  const deselectAll = () => {
    setSelectedSubcategories([])
  }

  const toggleCategoryExpansion = (categoryName: string) => {
    setExpandedCategories(prev => {
      // If clicking the same category that's already expanded, close it
      if (prev.has(categoryName)) {
        return new Set() // Close all
      }
      
      // Always replace with the new category (closes any other and opens this one simultaneously)
      return new Set([categoryName])
    })
  }

  const toggleCategory = (categoryName: string) => {
    const subcats = getSubcategoriesForCategory(categoryName)
    const isFullySelected = isCategoryFullySelected(categoryName)
    
    if (isFullySelected) {
      // Deselect all subcategories of this category
      setSelectedSubcategories(selectedSubcategories.filter(sub => !subcats.includes(sub)))
      
      // Only clear warning if it's for this category
      if (limitWarning?.categoryName === categoryName) {
        // Clear any existing timeout
        if (warningTimeoutRef.current) {
          clearTimeout(warningTimeoutRef.current)
          warningTimeoutRef.current = null
        }
        setLimitWarning(null)
        setIsWarningVisible(false)
      }
    } else {
      // Select all subcategories of this category (if we have room)
      const newSelections = subcats.filter(sub => !selectedSubcategories.includes(sub))
      const wouldExceedLimit = selectedSubcategories.length + newSelections.length > limitsConfig.selectionLimit
      
      if (!wouldExceedLimit) {
        setSelectedSubcategories([...selectedSubcategories, ...newSelections])
        
        // Only clear warning if it's for this category
        if (limitWarning?.categoryName === categoryName) {
          // Clear any existing timeout
          if (warningTimeoutRef.current) {
            clearTimeout(warningTimeoutRef.current)
            warningTimeoutRef.current = null
          }
          setLimitWarning(null)
          setIsWarningVisible(false)
        }
      } else {
        // Clear any existing timeout first
        if (warningTimeoutRef.current) {
          clearTimeout(warningTimeoutRef.current)
        }
        
        // Show warning when limit would be exceeded
        setLimitWarning({ 
          categoryName, 
          message: `Sorry, you can't exceed 10 subcategories! ${categoryName} has ${subcats.length} subcategories, but you can only select ${10 - selectedSubcategories.length} more.`
        })
        setIsWarningVisible(true)
        
        // Fade out and remove warning after 2 seconds
        warningTimeoutRef.current = setTimeout(() => {
          setIsWarningVisible(false)
          // Remove warning completely after fade out completes
          setTimeout(() => {
            setLimitWarning(null)
            warningTimeoutRef.current = null
          }, 300)
        }, 2000)
      }
    }
  }

  const toggleSubcategory = (subcategoryName: string) => {
    if (selectedSubcategories.includes(subcategoryName)) {
      // Deselect the subcategory
      setSelectedSubcategories(selectedSubcategories.filter(sub => sub !== subcategoryName))
    } else {
      if (selectedSubcategories.length < 10) { // Allow up to 10 subcategories
        // Select the subcategory
        setSelectedSubcategories([...selectedSubcategories, subcategoryName])
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (selectedSubcategories.length === 0) {
      setError('Please select at least one subcategory')
      return
    }

    setIsGenerating(true)
    setError(null)
    setStageMessage('Leafing through the newspapers...')
    completedRef.current = false

    try {
      // Get Firebase ID token
      const token = await getIdToken()
      if (!token) {
        throw new Error('Please sign in to generate a podcast')
      }

      const request: CreateEpisodeRequest = {
        subcategories: selectedSubcategories,
        duration_minutes: limitsConfig.defaultEpisodeDuration
      }

      const response = await fetch('/api/episodes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        throw new Error('Failed to create episode')
      }

      const { episode_id } = await response.json()
      
      const eventSource = new EventSource(`/api/episodes/${episode_id}/events`)
      eventSourceRef.current = eventSource
      
      console.log('🔌 SSE connection opened for episode:', episode_id)
      
      eventSource.onopen = () => {
        console.log('✅ SSE connection established')
      }
      
      eventSource.onmessage = (event) => {
        console.log('📨 SSE message received:', event.data)

        try {
          const statusData = JSON.parse(event.data)
          
          // ✨ FIX #2: Use flushSync to force immediate React updates
          // This bypasses React 18's automatic batching for SSE updates
          if (statusData.stage) {
            console.log('🔄 Updating stage to:', statusData.stage)
            const newMessage = getStageMessage(statusData.stage)
            console.log('📝 Setting stage message to:', newMessage)
            flushSync(() => {
              setStageMessage(newMessage)
            })
            console.log('✅ Stage message updated')
          }
          
          if (statusData.status === 'completed') {
            completedRef.current = true
            flushSync(() => {
              setStageMessage('Ready to listen!')
            })
            
            fetch(`/api/episodes/${episode_id}`)
              .then(res => res.json())
              .then((episode: Episode) => {
                onEpisodeCreated(episode)
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
            return;
          }

        } catch {
          // Some SSE frames may be keepalives or non-JSON (e.g., ": ping" or "[DONE]").
          // Silently ignore non-JSON frames instead of surfacing an error.
          return
        }
      }
      
      // Handle SSE connection errors (but only show error if not completed)
      eventSource.onerror = (error) => {
        if (!completedRef.current) {
          console.log('❌ SSE connection issue (will auto-retry):', error)
          // Do not set error or hide the progress UI; let EventSource retry automatically.
          // We also do not close the connection manually here.
        }
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setIsGenerating(false)
    }
  }
  
  // Show sign-in prompt if not authenticated
  if (!user && !authLoading) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="p-8 bg-gradient-to-r from-cream-100 to-tan-100 rounded-2xl text-center">
          <h2 className="text-2xl font-bold text-maroon-800 mb-4">Sign In to Create Your Podcast</h2>
          <p className="text-maroon-700 mb-6">
            Sign in with your Google account to generate personalized news podcasts tailored to your interests.
          </p>
          <GoogleSignInButton />
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <div>
        <label className="block text-lg font-semibold text-maroon-800 mb-4">
          Choose Your News Topics
        </label>
        <p className="text-sm text-tan-700 mb-6">
          Select up to 10 categories or subcategories for your personalized news podcast. Click category headers to select all, or pick individual topics.
        </p>
          
          {isLoadingCategories ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="border rounded-lg p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded mb-3 w-1/3"></div>
                  <div className="grid grid-cols-2 gap-2">
                    {[...Array(4)].map((_, j) => (
                      <div key={j} className="h-8 bg-gray-200 rounded"></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : categories.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-2">No categories available</p>
              <p className="text-sm text-gray-400">Try running RSS discovery to populate articles</p>
            </div>
          ) : (
            <div className="space-y-4">
              {categories.map((category) => {
                const categoryFullySelected = isCategoryFullySelected(category.category)
                const hasSelectedSubcats = category.subcategories.some(sub => 
                  selectedSubcategories.includes(sub.subcategory)
                )
                const isExpanded = expandedCategories.has(category.category)
                
                // Calculate dynamic height based on subcategory count
                const subcategoryCount = category.subcategories.length
                const columnsPerRow = 2 // Use mobile grid (2 cols) for safety
                const rows = Math.ceil(subcategoryCount / columnsPerRow)
                const buttonHeight = 80 // Each button is roughly 80px with padding
                const containerPadding = 60 // px-5 pb-5 pt-4 plus spacing
                const dynamicMaxHeight = (rows * buttonHeight) + containerPadding
                
                // Calculate proportional animation duration (base 400ms + 2ms per pixel)
                const animationDuration = Math.min(Math.max(400 + (dynamicMaxHeight * 0.8), 300), 700)
                
                return (
                  <div key={category.category} className={`bg-cream-100 hover:bg-tan-100 border border-transparent hover:border-tan-300 hover:shadow-lg transition-all duration-200 ${
                    isExpanded ? 'rounded-t-xl rounded-b-xl' : 'rounded-xl'
                  }`}>
                    {/* Category Header - Entire box is clickable */}
                    <button
                      type="button"
                      onClick={() => toggleCategoryExpansion(category.category)}
                      className={`w-full p-5 text-left transition-colors duration-200 ${
                        isExpanded ? 'rounded-t-xl' : 'rounded-xl'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="font-bold text-lg text-tan-900 mb-1">{category.category}</div>
                          <div className="text-sm text-tan-700">
                            {category.total_articles} articles • Score: {category.avg_importance.toFixed(1)}
                            {hasSelectedSubcats && (
                              <span className="ml-2 text-maroon-600 font-medium">
                                • {selectedSubcategories.filter(sub => 
                                  category.subcategories.some(catSub => catSub.subcategory === sub)
                                ).length} selected
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          {categoryFullySelected && (
                            <span className="text-xs bg-maroon-100 text-maroon-700 px-2 py-1 rounded-full font-medium">All Selected</span>
                          )}
                          {/* Warning message for this category */}
                          {limitWarning && limitWarning.categoryName === category.category && (
                            <span className={`text-sm text-orange-600 font-medium transition-opacity duration-300 ease-in-out ${
                              isWarningVisible ? 'opacity-100' : 'opacity-0'
                            }`}>
                              Sorry, you can't exceed 10 subcategories!
                            </span>
                          )}
                          {/* Select All Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation() // Prevent expanding when clicking select all
                              toggleCategory(category.category)
                            }}
                            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                              categoryFullySelected
                                ? 'bg-maroon-600 text-white hover:bg-maroon-700'
                              : hasSelectedSubcats
                              ? 'bg-maroon-100 text-maroon-700 hover:bg-maroon-200'
                              : 'bg-tan-200 text-tan-800 hover:bg-tan-300'
                            }`}
                          >
                            {categoryFullySelected ? 'Deselect All' : 'Select All'}
                          </button>
                          <svg
                            className={`w-5 h-5 text-tan-500 transition-transform duration-200 ${
                              isExpanded ? 'rotate-180' : ''
                            }`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </div>
                    </button>
                    
                    {/* Slide-out Subcategories */}
                    <div 
                      className={`grid overflow-hidden ${
                        isExpanded ? 'grid-rows-[1fr] opacity-100 pointer-events-auto' : 'grid-rows-[0fr] opacity-0 pointer-events-none'
                      }`}
                      style={{
                        transition: `grid-template-rows ${animationDuration}ms cubic-bezier(0.22, 0.61, 0.36, 1), opacity ${animationDuration}ms cubic-bezier(0.22, 0.61, 0.36, 1), padding ${animationDuration}ms cubic-bezier(0.22, 0.61, 0.36, 1)`
                      }}
                    >
                      <div 
                        className="min-h-0 overflow-hidden"
                        style={{
                          paddingLeft: isExpanded ? '20px' : '0px',
                          paddingRight: isExpanded ? '20px' : '0px',
                          paddingBottom: isExpanded ? '20px' : '0px',
                          paddingTop: isExpanded ? '16px' : '0px',
                          transition: `padding ${animationDuration}ms cubic-bezier(0.22, 0.61, 0.36, 1)`
                        }}
                      >
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {category.subcategories.map((subcategory) => {
                            const subcatSelected = selectedSubcategories.includes(subcategory.subcategory)
                            
                            return (
                              <button
                                key={subcategory.subcategory}
                                type="button"
                                onClick={() => toggleSubcategory(subcategory.subcategory)}
                                className={`p-3 rounded-lg text-xs font-semibold transition-colors duration-200 text-left ${
                                  subcatSelected
                                    ? 'bg-gradient-to-r from-red-400 to-red-500 text-white shadow-md border border-red-400'
                                    : 'bg-red-50 text-red-800 hover:bg-red-100 border border-transparent hover:border-red-300'
                                } ${
                                  !subcatSelected && getTotalSelectionCount() >= 10
                                    ? 'opacity-40 cursor-not-allowed'
                                    : 'cursor-pointer'
                                }`}
                                disabled={!subcatSelected && getTotalSelectionCount() >= 10}
                              >
                                <div className="font-bold text-sm mb-1">{subcategory.subcategory}</div>
                                <div className={`text-xs font-medium ${
                                  subcatSelected ? 'text-red-100' : 'text-red-600'
                                }`}>
                                  {subcategory.article_count} articles
                                </div>
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          
          <div className="mt-6 p-4 bg-gradient-to-r from-tan-100 to-cream-200 rounded-xl">
            <div className="flex justify-between items-center text-sm mb-3">
              <span className="font-semibold text-tan-800">
                Selected: {getTotalSelectionCount()}/10 topics
              </span>
              <div className="flex items-center gap-3">
                <span className={`font-medium ${
                  getTotalSelectionCount() === 0 ? 'text-tan-600' : 'text-maroon-700'
                }`}>
                  {getTotalSelectionCount() === 0 ? 'Choose your topics' : 'Ready to create!'}
                </span>
                {getTotalSelectionCount() > 0 && (
                  <button
                    type="button"
                    onClick={deselectAll}
                    className="px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 bg-maroon-600 text-white hover:bg-maroon-700"
                  >
                    Deselect All
                  </button>
                )}
              </div>
            </div>
            {selectedSubcategories.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {selectedSubcategories.map(sub => (
                  <span key={sub} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    {sub}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

      <div>
        <label className="block text-lg font-semibold text-maroon-800 mb-3">
          Podcast Length
        </label>
        <div className="p-4 bg-gradient-to-r from-cream-200 to-tan-200 rounded-xl">
          <span className="text-sm font-medium text-maroon-800">🎧 5 minutes - Perfect for your daily commute</span>
        </div>
      </div>

      {isGenerating && (
        <div className="p-8 bg-gradient-to-r from-cream-100 to-tan-100 rounded-2xl text-center">
          <div className="space-y-6">
            <div className="animate-pulse">
              <div className="w-8 h-8 bg-gradient-to-r from-maroon-700 to-maroon-800 rounded-full mx-auto mb-6 animate-bounce">
              </div>
              <h3 className="text-2xl font-bold text-maroon-800 mb-4">Creating Your Personal News Podcast</h3>
              <div key={stageMessage} className="transition-all duration-1000 ease-in-out">
                <p className="text-maroon-700 text-lg font-semibold">
                  {stageMessage}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-maroon-50 rounded-xl">
          <p className="text-sm text-maroon-700 font-medium">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={selectedSubcategories.length === 0 || isGenerating}
        className={`w-full py-4 px-6 rounded-xl font-bold text-lg transition-all duration-200 shadow-lg ${
          selectedSubcategories.length === 0
            ? 'bg-gradient-to-r from-tan-300 to-tan-400 text-tan-700 cursor-not-allowed'
            : isGenerating
            ? 'bg-gradient-to-r from-maroon-900 to-maroon-700 text-white cursor-not-allowed'
            : 'bg-gradient-to-r from-maroon-900 to-maroon-700 text-white hover:from-maroon-800 hover:to-maroon-600 hover:shadow-xl hover:ring-2 hover:ring-maroon-300'
        }`}
      >
        {isGenerating ? 'Creating Your Podcast...' : 'Generate My Podcast'}
      </button>
    </form>
  )
}