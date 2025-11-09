'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { DataProvider, useData } from '@/contexts/DataContext'
import { AudioProvider } from '@/contexts/AudioContext'
import { LandingPage } from '@/components/LandingPage'
import { Navigation } from '@/components/Navigation'
import { TodaysEpisodePage } from '@/components/TodaysEpisodePage'
import { PastEpisodesPage } from '@/components/PastEpisodesPage'
import { PreferencesPage } from '@/components/PreferencesPage'

type Page = 'today' | 'past' | 'preferences'

function AppContent() {
  const { generateEpisode, isGenerating, isCheckingInitialLoad } = useData()
  const [currentPage, setCurrentPage] = useState<Page>('today')
  const swipeContainerRef = useRef<HTMLDivElement>(null)

  // Touch swipe state for mobile navigation
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)
  const touchEndRef = useRef<{ x: number; y: number } | null>(null)

  const handleNavigate = (page: Page) => {
    setCurrentPage(page)
  }

  // Industry standard: Scroll to top when page changes
  // Using useEffect ensures scroll happens after DOM updates
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [currentPage])

  // Industry standard: Non-passive touch event listeners for swipe gestures
  // This is how Twitter/Instagram handle swipes - allows preventDefault() to work
  useEffect(() => {
    const container = swipeContainerRef.current
    if (!container) return

    const minSwipeDistance = 50

    const handleTouchStart = (e: TouchEvent) => {
      touchEndRef.current = null
      touchStartRef.current = {
        x: e.touches[0].clientX,
        y: e.touches[0].clientY
      }
    }

    const handleTouchMove = (e: TouchEvent) => {
      touchEndRef.current = {
        x: e.touches[0].clientX,
        y: e.touches[0].clientY
      }

      // Prevent vertical scrolling during horizontal swipes
      if (touchStartRef.current) {
        const horizontalDistance = Math.abs(touchStartRef.current.x - e.touches[0].clientX)
        const verticalDistance = Math.abs(touchStartRef.current.y - e.touches[0].clientY)

        // If horizontal movement is greater than vertical, prevent default scroll
        if (horizontalDistance > verticalDistance && horizontalDistance > 10) {
          e.preventDefault()
        }
      }
    }

    const handleTouchEnd = () => {
      if (!touchStartRef.current || !touchEndRef.current) return

      const horizontalDistance = touchStartRef.current.x - touchEndRef.current.x
      const verticalDistance = touchStartRef.current.y - touchEndRef.current.y

      // Only trigger horizontal navigation if horizontal movement is greater than vertical
      const isHorizontalSwipe = Math.abs(horizontalDistance) > Math.abs(verticalDistance)

      if (isHorizontalSwipe) {
        const isLeftSwipe = horizontalDistance > minSwipeDistance
        const isRightSwipe = horizontalDistance < -minSwipeDistance

        if (isLeftSwipe || isRightSwipe) {
          // Swipe left = next page, swipe right = previous page
          const pages: Page[] = ['past', 'today', 'preferences']
          const currentIndex = pages.indexOf(currentPage)

          if (isLeftSwipe && currentIndex < pages.length - 1) {
            handleNavigate(pages[currentIndex + 1])
          } else if (isRightSwipe && currentIndex > 0) {
            handleNavigate(pages[currentIndex - 1])
          }
        }
      }
    }

    // Attach non-passive event listeners (allows preventDefault to work)
    container.addEventListener('touchstart', handleTouchStart, { passive: false })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [currentPage])

  const handleGeneratePodcast = async () => {
    // Prevent multiple clicks
    if (isGenerating) return

    setCurrentPage('today')
    // Call the generate function from context
    if (generateEpisode) {
      await generateEpisode()
    }
  }

  return (
    <div className="min-h-screen bg-white pb-24 pt-20">
      {/* Navigation - Hidden during initial load, fades in */}
      {!isCheckingInitialLoad && (
        <Navigation currentPage={currentPage} onNavigate={handleNavigate} />
      )}

      <div
        ref={swipeContainerRef}
        className="bg-gradient-to-b from-white to-cream-50 min-h-[calc(100vh-4rem)]"
      >
        {/* Industry standard tab navigation: Keep all tabs mounted but hidden */}
        {/* Preserves component state, scroll handled by useEffect above */}
        <div className={currentPage === 'today' ? 'block' : 'hidden'}>
          <TodaysEpisodePage />
        </div>
        <div className={currentPage === 'past' ? 'block' : 'hidden'}>
          <PastEpisodesPage />
        </div>
        <div className={currentPage === 'preferences' ? 'block' : 'hidden'}>
          <PreferencesPage />
        </div>
      </div>

      {/* Persistent Generate Button - Hidden during initial load, fades in */}
      {!isCheckingInitialLoad && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-tan-200 shadow-lg z-[9999] animate-fadeIn">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <button
              onClick={handleGeneratePodcast}
              disabled={isGenerating}
              className={`w-full font-semibold py-4 rounded-xl transition-all duration-200 shadow-md lowercase text-lg ${
                isGenerating
                  ? 'bg-tan-300 text-tan-600 cursor-not-allowed'
                  : 'bg-red-400 hover:bg-red-500 text-white hover:shadow-lg'
              }`}
            >
              {isGenerating ? 'generating...' : 'generate new podcast'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Home() {
  const { user, loading: authLoading } = useAuth()
  const [isCheckingPreferences, setIsCheckingPreferences] = useState(true)

  // Check if user has preferences when they log in
  useEffect(() => {
    const checkPreferences = async () => {
      if (!user || authLoading) {
        setIsCheckingPreferences(false)
        return
      }

      try {
        const token = await user.getIdToken()
        const response = await fetch('/api/users/preferences', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (response.ok) {
          // Just checking preferences exist, AppContent manages navigation
        }
      } catch (error) {
        console.error('Error checking preferences:', error)
      } finally {
        setIsCheckingPreferences(false)
      }
    }

    checkPreferences()
  }, [user, authLoading])

  // Show loading spinner while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center animate-fadeIn">
        <div>
          <div className="w-8 h-8 bg-gradient-to-r from-maroon-700 to-maroon-800 rounded-full mx-auto mb-6 animate-bounce"></div>
          <p className="text-maroon-700 text-lg font-semibold">loading...</p>
        </div>
      </div>
    )
  }

  // Show landing page if not authenticated
  if (!user) {
    return <LandingPage />
  }

  // Show loading while checking preferences
  if (isCheckingPreferences) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center animate-fadeIn">
        <div>
          <div className="w-8 h-8 bg-gradient-to-r from-maroon-700 to-maroon-800 rounded-full mx-auto mb-6 animate-bounce"></div>
          <p className="text-maroon-700 text-lg font-semibold">Setting up your account...</p>
        </div>
      </div>
    )
  }

  // Show authenticated app with navigation
  return (
    <AudioProvider>
      <DataProvider>
        <AppContent />
      </DataProvider>
    </AudioProvider>
  )
}