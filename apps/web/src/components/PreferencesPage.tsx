'use client'

import { useState, useRef, useEffect } from 'react'
import { getLimitsConfig, getUIConfig } from '@/config/app-config'
import { useAuth } from '@/contexts/AuthContext'
import { useData } from '@/contexts/DataContext'

interface Category {
  category: string;
  subcategories: Subcategory[];
  total_articles: number;
  avg_importance: number;
  max_importance: number;
}

interface Subcategory {
  subcategory: string;
  article_count: number;
  avg_importance: number;
  max_importance: number;
  latest_article: string | null;
}

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

export function PreferencesPage() {
  const { getIdToken } = useAuth()
  const limitsConfig = getLimitsConfig()
  const uiConfig = getUIConfig()
  const { categories: cachedCategories, setCategories: setCachedCategories, userPreferences, setUserPreferences } = useData()

  const [selectedSubcategories, setSelectedSubcategories] = useState<string[]>([])
  const [originalSubcategories, setOriginalSubcategories] = useState<string[]>([])
  const [customTags, setCustomTags] = useState<string[]>([])
  const [originalCustomTags, setOriginalCustomTags] = useState<string[]>([])
  const [tagSearchQuery, setTagSearchQuery] = useState('')
  const [tagSearchResults, setTagSearchResults] = useState<string[]>([])
  const [isSearchingTags, setIsSearchingTags] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoadingCategories, setIsLoadingCategories] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [limitWarning, setLimitWarning] = useState<{ categoryName: string; message: string } | null>(null)
  const [isWarningVisible, setIsWarningVisible] = useState(false)

  const warningTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const searchDebounceRef = useRef<NodeJS.Timeout | null>(null)
  const searchContainerRef = useRef<HTMLDivElement | null>(null)

  // Search tags with debouncing
  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current)
    }

    if (tagSearchQuery.length < 2) {
      setTagSearchResults([])
      setIsSearchingTags(false)
      return
    }

    setIsSearchingTags(true)

    searchDebounceRef.current = setTimeout(async () => {
      try {
        const response = await fetch(`/api/episodes/tags/search?query=${encodeURIComponent(tagSearchQuery)}`)
        if (response.ok) {
          const data = await response.json()
          // Filter out already selected tags
          const filteredTags = (data.tags || []).filter((tag: string) => !customTags.includes(tag))
          setTagSearchResults(filteredTags)
        }
      } catch (error) {
        console.error('Failed to search tags:', error)
      } finally {
        setIsSearchingTags(false)
      }
    }, 300)

    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current)
      }
    }
  }, [tagSearchQuery, customTags])

  // Click outside handler to close search results
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setTagSearchResults([])
        setTagSearchQuery('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Fetch categories and user preferences on mount (with caching)
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Use cached categories if available
        if (cachedCategories) {
          setCategories(cachedCategories)
          setIsLoadingCategories(false)
        } else {
          // Fetch categories
          const categoriesResponse = await fetch('/api/categories')
          if (!categoriesResponse.ok) {
            throw new Error('Failed to fetch categories')
          }
          const categoriesData = await categoriesResponse.json()
          const rawCategories = categoriesData.categories || []

          // Sort categories
          const sortedCategories = [...rawCategories].sort((a, b) => {
            const indexA = CATEGORY_ORDER.indexOf(a.category)
            const indexB = CATEGORY_ORDER.indexOf(b.category)
            if (indexA === -1 && indexB === -1) return 0
            if (indexA === -1) return 1
            if (indexB === -1) return -1
            return indexA - indexB
          })

          setCategories(sortedCategories)
          setCachedCategories(sortedCategories)
          setIsLoadingCategories(false)
        }

        // Use cached preferences if available
        if (userPreferences) {
          setSelectedSubcategories(userPreferences.subcategories)
          setOriginalSubcategories(userPreferences.subcategories)
          setCustomTags(userPreferences.custom_tags || [])
          setOriginalCustomTags(userPreferences.custom_tags || [])
        } else {
          // Fetch user preferences
          const token = await getIdToken()
          if (token) {
            const prefsResponse = await fetch('/api/users/preferences', {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            })
            if (prefsResponse.ok) {
              const prefsData = await prefsResponse.json()
              if (prefsData.preferences && prefsData.preferences.subcategories) {
                const tags = prefsData.preferences.custom_tags || []
                setSelectedSubcategories(prefsData.preferences.subcategories)
                setOriginalSubcategories(prefsData.preferences.subcategories)
                setCustomTags(tags)
                setOriginalCustomTags(tags)
                setUserPreferences({
                  subcategories: prefsData.preferences.subcategories,
                  custom_tags: tags
                })
              }
            }
          }
        }
      } catch (err) {
        setError('Failed to load data. Please refresh the page.')
        setIsLoadingCategories(false)
      }
    }
    fetchData()
  }, [getIdToken, cachedCategories, userPreferences, setCachedCategories, setUserPreferences])

  const getSubcategoriesForCategory = (categoryName: string): string[] => {
    const category = categories.find(cat => cat.category === categoryName)
    return category ? category.subcategories.map(sub => sub.subcategory) : []
  }

  const isCategoryFullySelected = (categoryName: string): boolean => {
    const subcats = getSubcategoriesForCategory(categoryName)
    return subcats.length > 0 && subcats.every(sub => selectedSubcategories.includes(sub))
  }

  const deselectAll = () => {
    setSelectedSubcategories([])
    setCustomTags([])
  }

  const addTag = (tag: string) => {
    if (!customTags.includes(tag)) {
      // Check combined limit: display count + custom tags ≤ 8
      const currentDisplayCount = getDisplayCount(selectedSubcategories)
      const totalTopics = currentDisplayCount + customTags.length

      if (totalTopics < limitsConfig.selectionLimit) {
        setCustomTags([...customTags, tag])
        setTagSearchQuery('')
        setTagSearchResults([])
      } else {
        // Show warning that limit is reached
        if (warningTimeoutRef.current) {
          clearTimeout(warningTimeoutRef.current)
        }
        setLimitWarning({
          categoryName: 'custom-tags',
          message: `Sorry, you can't exceed ${limitsConfig.selectionLimit} topics total!`
        })
        setIsWarningVisible(true)
        warningTimeoutRef.current = setTimeout(() => {
          setIsWarningVisible(false)
          setTimeout(() => {
            setLimitWarning(null)
            warningTimeoutRef.current = null
          }, 300)
        }, 2000)
      }
    }
  }

  const removeTag = (tag: string) => {
    setCustomTags(customTags.filter(t => t !== tag))
  }

  const hasChanges = () => {
    // Check subcategories changes
    if (selectedSubcategories.length !== originalSubcategories.length) return true
    const sorted1 = [...selectedSubcategories].sort()
    const sorted2 = [...originalSubcategories].sort()
    if (!sorted1.every((val, idx) => val === sorted2[idx])) return true

    // Check custom tags changes
    if (customTags.length !== originalCustomTags.length) return true
    const sortedTags1 = [...customTags].sort()
    const sortedTags2 = [...originalCustomTags].sort()
    return !sortedTags1.every((val, idx) => val === sortedTags2[idx])
  }

  const toggleCategoryExpansion = (categoryName: string) => {
    setExpandedCategories(prev => {
      if (prev.has(categoryName)) {
        return new Set()
      }
      return new Set([categoryName])
    })
  }

  // Helper function to calculate the actual count for display, treating World News as 1
  const getDisplayCount = (selections: string[]): number => {
    const worldNewsSubcats = getSubcategoriesForCategory("World News")
    const hasAnyWorldNews = worldNewsSubcats.some(sub => selections.includes(sub))
    const nonWorldNewsCount = selections.filter(sub => !worldNewsSubcats.includes(sub)).length
    return hasAnyWorldNews ? nonWorldNewsCount + 1 : nonWorldNewsCount
  }

  const toggleCategory = (categoryName: string) => {
    const subcats = getSubcategoriesForCategory(categoryName)
    const isFullySelected = isCategoryFullySelected(categoryName)
    const isWorldNews = categoryName === "World News"

    if (isFullySelected) {
      setSelectedSubcategories(selectedSubcategories.filter(sub => !subcats.includes(sub)))
      if (limitWarning?.categoryName === categoryName) {
        if (warningTimeoutRef.current) {
          clearTimeout(warningTimeoutRef.current)
          warningTimeoutRef.current = null
        }
        setLimitWarning(null)
        setIsWarningVisible(false)
      }
    } else {
      const newSelections = subcats.filter(sub => !selectedSubcategories.includes(sub))

      // Calculate the cost: World News counts as 1, others count as their actual number
      const costOfSelection = isWorldNews ? 1 : newSelections.length

      // Calculate current count using display logic + custom tags
      const currentDisplayCount = getDisplayCount(selectedSubcategories)
      const totalTopics = currentDisplayCount + customTags.length

      const wouldExceedLimit = totalTopics + costOfSelection > limitsConfig.selectionLimit

      if (!wouldExceedLimit) {
        setSelectedSubcategories([...selectedSubcategories, ...newSelections])
        if (limitWarning?.categoryName === categoryName) {
          if (warningTimeoutRef.current) {
            clearTimeout(warningTimeoutRef.current)
            warningTimeoutRef.current = null
          }
          setLimitWarning(null)
          setIsWarningVisible(false)
        }
      } else {
        if (warningTimeoutRef.current) {
          clearTimeout(warningTimeoutRef.current)
        }
        setLimitWarning({
          categoryName,
          message: `Sorry, you can't exceed 8 topics total!`
        })
        setIsWarningVisible(true)
        warningTimeoutRef.current = setTimeout(() => {
          setIsWarningVisible(false)
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
      setSelectedSubcategories(selectedSubcategories.filter(sub => sub !== subcategoryName))
    } else {
      // Check combined limit: display count + custom tags ≤ 8
      const currentDisplayCount = getDisplayCount(selectedSubcategories)
      const totalTopics = currentDisplayCount + customTags.length

      if (totalTopics < limitsConfig.selectionLimit) {
        setSelectedSubcategories([...selectedSubcategories, subcategoryName])
      }
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()

    if (selectedSubcategories.length === 0 && customTags.length === 0) {
      setError('Please select at least one topic or add a custom topic')
      return
    }

    setIsSaving(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const token = await getIdToken()
      if (!token) {
        throw new Error('Please sign in to save preferences')
      }

      const response = await fetch('/api/users/preferences', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          subcategories: selectedSubcategories,
          custom_tags: customTags
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to save preferences')
      }

      setOriginalSubcategories(selectedSubcategories)
      setOriginalCustomTags(customTags)
      setUserPreferences({ subcategories: selectedSubcategories, custom_tags: customTags })
      setSuccessMessage('Topics saved successfully!')
      // Don't navigate away - just show success message
      setTimeout(() => {
        setSuccessMessage(null)
      }, 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8 text-center space-y-2">
        <h1 className="text-4xl font-650 text-maroon-800 mb-2 lowercase">
          select the topics <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">you'd</span> like to hear about.
        </h1>
        <p className="text-tan-700 text-lg font-light">select up to 8 topics so we can craft a podcast tailored to you.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        <div>
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
                const isWorldNews = category.category === "World News"
                const categoryFullySelected = isCategoryFullySelected(category.category)
                const hasSelectedSubcats = category.subcategories.some(sub =>
                  selectedSubcategories.includes(sub.subcategory)
                )
                const isExpanded = expandedCategories.has(category.category)

                const subcategoryCount = category.subcategories.length
                const columnsPerRow = 2
                const rows = Math.ceil(subcategoryCount / columnsPerRow)
                const buttonHeight = 80
                const containerPadding = 60
                const dynamicMaxHeight = (rows * buttonHeight) + containerPadding
                const animationDuration = Math.min(Math.max(400 + (dynamicMaxHeight * 0.8), 300), 700)

                // Special rendering for World News - single clickable card
                if (isWorldNews) {
                  // Check if at limit (same logic as subcategories)
                  const currentDisplayCount = getDisplayCount(selectedSubcategories)
                  const totalTopics = currentDisplayCount + customTags.length
                  const isAtLimit = totalTopics >= limitsConfig.selectionLimit && !categoryFullySelected

                  return (
                    <button
                      key={category.category}
                      type="button"
                      onClick={() => toggleCategory(category.category)}
                      disabled={isAtLimit}
                      className={`w-full p-6 text-left rounded-xl border transition-all duration-200 ${
                        categoryFullySelected
                          ? 'bg-gradient-to-r from-red-400 to-red-500 border-red-400 text-white shadow-lg'
                          : 'bg-cream-100 hover:bg-tan-100 border-tan-200 hover:border-tan-300 hover:shadow-lg'
                      } ${
                        isAtLimit
                          ? 'opacity-40 cursor-not-allowed'
                          : 'cursor-pointer'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className={`font-bold text-lg mb-1 ${
                            categoryFullySelected ? 'text-white' : 'text-maroon-800'
                          }`}>
                            {category.category}
                          </div>
                          <div className={`text-sm min-h-[1.25rem] ${
                            categoryFullySelected ? 'text-red-100' : 'text-tan-700'
                          }`}>
                            {/* {category.total_articles} articles • Score: {category.avg_importance.toFixed(1)} */}
                            &nbsp;
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                }

                return (
                  <div key={category.category} className={`bg-cream-100 hover:bg-tan-100 border border-tan-200 hover:border-tan-300 hover:shadow-lg transition-all duration-200 ${
                    isExpanded ? 'rounded-t-xl rounded-b-xl' : 'rounded-xl'
                  }`}>
                    <button
                      type="button"
                      onClick={() => toggleCategoryExpansion(category.category)}
                      className={`w-full p-6 text-left transition-colors duration-200 ${
                        isExpanded ? 'rounded-t-xl' : 'rounded-xl'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="font-bold text-lg text-maroon-800 mb-1">{category.category}</div>
                          <div className="text-sm text-tan-700 min-h-[1.25rem]">
                            {/* {category.total_articles} articles • Score: {category.avg_importance.toFixed(1)} */}
                            {!hasSelectedSubcats && <>&nbsp;</>}
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
                          {limitWarning && limitWarning.categoryName === category.category && (
                            <span className={`text-sm text-orange-600 font-medium transition-opacity duration-300 ease-in-out ${
                              isWarningVisible ? 'opacity-100' : 'opacity-0'
                            }`}>
                              Sorry, you can't exceed 10 subcategories!
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
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
                            className={`w-5 h-5 text-tan-500 transition-transform ${
                              isExpanded ? 'rotate-180' : ''
                            }`}
                            style={{
                              transitionDuration: `${uiConfig.animations.arrowRotation}ms`
                            }}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </div>
                    </button>

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
                            const currentDisplayCount = getDisplayCount(selectedSubcategories)
                            const totalTopics = currentDisplayCount + customTags.length
                            const isAtLimit = totalTopics >= limitsConfig.selectionLimit

                            return (
                              <button
                                key={subcategory.subcategory}
                                type="button"
                                onClick={() => toggleSubcategory(subcategory.subcategory)}
                                className={`p-4 rounded-lg text-xs font-semibold transition-colors duration-200 text-left ${
                                  subcatSelected
                                    ? 'bg-gradient-to-r from-red-400 to-red-500 text-white shadow-md border border-red-400'
                                    : 'bg-red-50 text-red-800 hover:bg-red-100 border border-transparent hover:border-red-300'
                                } ${
                                  !subcatSelected && isAtLimit
                                    ? 'opacity-40 cursor-not-allowed'
                                    : 'cursor-pointer'
                                }`}
                                disabled={!subcatSelected && isAtLimit}
                              >
                                <div className="font-bold text-sm mb-1">{subcategory.subcategory}</div>
                                <div className={`text-xs font-medium min-h-[1rem] ${
                                  subcatSelected ? 'text-red-100' : 'text-red-600'
                                }`}>
                                  {/* {subcategory.article_count} articles */}
                                  &nbsp;
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
        </div>

        {/* Custom Tags Section */}
        <div className="mt-8">
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-maroon-800 mb-2 lowercase">
              add custom topics <span className="text-tan-600 text-sm font-normal">(optional)</span>
            </h2>
            <p className="text-tan-700 text-sm font-light">
              search for specific people, companies, sports teams or niche topics you want to follow (e.g., "Cristiano Ronaldo", "Tesla", "Manchester United")
            </p>
          </div>

          {/* Tag Search Input */}
          <div className="relative" ref={searchContainerRef}>
            {limitWarning && limitWarning.categoryName === 'custom-tags' && (
              <p className={`text-sm text-orange-600 font-medium text-center absolute -top-6 left-0 right-0 transition-opacity duration-300 ease-in-out ${
                isWarningVisible ? 'opacity-100' : 'opacity-0'
              }`}>
                {limitWarning.message}
              </p>
            )}
            <div className="relative">
              <input
                type="text"
                value={tagSearchQuery}
                onChange={(e) => setTagSearchQuery(e.target.value)}
                placeholder="search for topics... (e.g., Cristiano Ronaldo, Tesla)"
                className="w-full px-4 py-3 rounded-xl border-2 border-tan-200 focus:border-red-400 focus:outline-none bg-white text-maroon-800 placeholder-tan-500"
              />
              {isSearchingTags && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="w-5 h-5 border-2 border-red-400 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
            </div>

            {/* Search Results Dropdown */}
            {tagSearchQuery.length >= 2 && tagSearchResults.length > 0 && (
              <div className="absolute z-10 w-full mt-2 bg-white border-2 border-tan-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                {tagSearchResults.map(tag => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => addTag(tag)}
                    className="w-full px-4 py-3 text-left hover:bg-tan-50 transition-colors border-b border-tan-100 last:border-b-0 text-maroon-800"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}

            {/* No Results Message */}
            {tagSearchQuery.length >= 2 && !isSearchingTags && tagSearchResults.length === 0 && (
              <div className="absolute z-10 w-full mt-2 bg-white border-2 border-tan-200 rounded-xl shadow-lg p-4">
                <p className="text-sm text-tan-600 text-center">No topics found matching "{tagSearchQuery}"</p>
              </div>
            )}
          </div>

          {/* Selected Topics Card - Shows both subcategories and custom tags */}
          {(selectedSubcategories.length > 0 || customTags.length > 0) && (
            <div className="mt-6 p-4 bg-gradient-to-r from-tan-100 to-cream-200 rounded-xl">
              <div className="flex justify-between items-center text-sm mb-3">
                <span className="font-semibold text-tan-800">
                  selected: {getDisplayCount(selectedSubcategories) + customTags.length}/8 topics
                </span>
                <div className="flex items-center gap-3">
                  {hasChanges() && (
                    <span className="font-medium text-maroon-700">
                      Ready to save!
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={deselectAll}
                    className="px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 bg-maroon-600 text-white hover:bg-maroon-700"
                  >
                    deselect all
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(() => {
                  const worldNewsSubcats = getSubcategoriesForCategory("World News")
                  const hasWorldNews = worldNewsSubcats.some(sub => selectedSubcategories.includes(sub))
                  const nonWorldNews = selectedSubcategories.filter(sub => !worldNewsSubcats.includes(sub))

                  return (
                    <>
                      {/* Regular subcategories in red with X buttons */}
                      {hasWorldNews && (
                        <div
                          key="World News"
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                        >
                          <span>World News</span>
                          <button
                            type="button"
                            onClick={() => toggleCategory("World News")}
                            className="ml-1.5 hover:bg-red-200 rounded-full p-0.5 transition-colors"
                            aria-label="Remove World News"
                          >
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        </div>
                      )}
                      {nonWorldNews.map(sub => (
                        <div
                          key={sub}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                        >
                          <span>{sub}</span>
                          <button
                            type="button"
                            onClick={() => toggleSubcategory(sub)}
                            className="ml-1.5 hover:bg-red-200 rounded-full p-0.5 transition-colors"
                            aria-label={`Remove ${sub}`}
                          >
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        </div>
                      ))}

                      {/* Custom tags in dark brown/maroon */}
                      {customTags.map(tag => (
                        <div
                          key={tag}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-maroon-700 text-white shadow-sm"
                        >
                          <span>{tag}</span>
                          <button
                            type="button"
                            onClick={() => removeTag(tag)}
                            className="ml-1.5 hover:bg-maroon-800 rounded-full p-0.5 transition-colors"
                            aria-label={`Remove ${tag}`}
                          >
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </>
                  )
                })()}
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="p-4 bg-maroon-50 rounded-xl">
            <p className="text-sm text-maroon-700 font-medium">{error}</p>
          </div>
        )}

        <div className="relative">
          {successMessage && (
            <p className={`text-sm text-green-600 font-medium text-center absolute -top-6 left-0 right-0 transition-opacity duration-300 ease-in-out ${
              successMessage ? 'opacity-100' : 'opacity-0'
            }`}>topics saved!</p>
          )}
          <button
            type="submit"
            disabled={(selectedSubcategories.length === 0 && customTags.length === 0) || isSaving || !hasChanges()}
            className={`w-full py-4 px-6 rounded-xl font-bold text-lg transition-all duration-200 shadow-lg lowercase ${
              (selectedSubcategories.length === 0 && customTags.length === 0) || !hasChanges()
                ? 'bg-gradient-to-r from-tan-300 to-tan-400 text-tan-700 cursor-not-allowed'
                : isSaving
                ? 'bg-gradient-to-r from-maroon-900 to-maroon-700 text-white cursor-not-allowed'
                : 'bg-gradient-to-r from-maroon-900 to-maroon-700 text-white hover:from-maroon-800 hover:to-maroon-600 hover:shadow-xl hover:ring-2 hover:ring-maroon-300'
            }`}
          >
            {isSaving ? 'saving topics...' : 'save topics'}
          </button>
        </div>
      </form>
    </div>
  )
}
