'use client'

import { UserProfileDropdown } from './UserProfileDropdown'
import { useEffect, useRef, useState } from 'react'
import { useAudio } from '@/contexts/AudioContext'

interface NavigationProps {
  currentPage: 'today' | 'past' | 'preferences'
  onNavigate: (page: 'today' | 'past' | 'preferences') => void
}

export function Navigation({ currentPage, onNavigate }: NavigationProps) {
  const [indicatorStyle, setIndicatorStyle] = useState<{ left: number; width: number } | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const navRefs = useRef<{ [key: string]: HTMLButtonElement | null }>({
    past: null,
    today: null,
    preferences: null
  })

  // Industry standard: Use AudioContext instead of document.querySelectorAll
  const { pauseAllAudio } = useAudio()

  const handleNavigate = (page: 'today' | 'past' | 'preferences') => {
    pauseAllAudio()
    onNavigate(page)
  }

  useEffect(() => {
    const updateIndicator = () => {
      const currentButton = navRefs.current[currentPage]
      const container = containerRef.current
      if (currentButton && container) {
        // Get positions relative to the container
        const buttonLeft = currentButton.offsetLeft
        const buttonWidth = currentButton.offsetWidth

        // Calculate center of button
        const buttonCenter = buttonLeft + (buttonWidth / 2)

        // Fixed indicator width
        const indicatorWidth = 48

        setIndicatorStyle({
          left: buttonCenter - (indicatorWidth / 2),
          width: indicatorWidth
        })

        if (!isInitialized) {
          setIsInitialized(true)
        }
      }
    }

    // Update immediately and on resize
    updateIndicator()
    window.addEventListener('resize', updateIndicator)

    return () => {
      window.removeEventListener('resize', updateIndicator)
    }
  }, [currentPage, isInitialized])

  return (
    <nav className="bg-white fixed top-0 left-0 right-0 z-[9999] shadow-sm animate-fadeIn">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="relative flex items-center justify-between h-20">
          {/* Logo - hidden on mobile, shown on desktop */}
          <div className="hidden md:flex items-center">
            <span className="text-3xl font-bold lowercase">
              <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">your</span>
              <span className="bg-gradient-to-r from-maroon-900 to-maroon-700 bg-clip-text text-transparent">cast!</span>
            </span>
          </div>

          {/* Navigation Menu - Takes full width on mobile (except user icon space), centered on desktop */}
          <div ref={containerRef} className="flex-1 md:absolute md:left-0 md:right-0 grid grid-cols-[1fr_auto_1fr] items-center md:pointer-events-none">
            <button
              ref={(el) => { navRefs.current.past = el }}
              onClick={() => handleNavigate('past')}
              className={`justify-self-end px-3 md:px-6 py-3 text-sm md:text-lg font-normal transition-colors duration-200 lowercase md:pointer-events-auto ${
                currentPage === 'past'
                  ? 'text-maroon-800'
                  : 'text-tan-600 hover:text-maroon-700'
              }`}
            >
              <span>archive</span>
            </button>
            <button
              ref={(el) => { navRefs.current.today = el }}
              onClick={() => handleNavigate('today')}
              className={`px-3 md:px-6 py-3 text-sm md:text-lg font-normal transition-colors duration-200 lowercase md:pointer-events-auto ${
                currentPage === 'today'
                  ? 'text-maroon-800'
                  : 'text-tan-600 hover:text-maroon-700'
              }`}
            >
              <span>home</span>
            </button>
            <button
              ref={(el) => { navRefs.current.preferences = el }}
              onClick={() => handleNavigate('preferences')}
              className={`justify-self-start px-3 md:px-6 py-3 text-sm md:text-lg font-normal transition-colors duration-200 lowercase md:pointer-events-auto ${
                currentPage === 'preferences'
                  ? 'text-maroon-800'
                  : 'text-tan-600 hover:text-maroon-700'
              }`}
            >
              <span>personalize</span>
            </button>
            {/* Sliding indicator */}
            {indicatorStyle && (
              <div
                className={`absolute bottom-0 h-0.5 bg-gradient-to-r from-maroon-600 to-maroon-800 ${
                  isInitialized ? 'transition-all duration-300 ease-in-out' : ''
                }`}
                style={{
                  left: indicatorStyle.left,
                  width: indicatorStyle.width
                }}
              />
            )}
          </div>

          {/* User Profile Dropdown - stays on the right on all screen sizes */}
          <div className="flex items-center ml-2">
            <UserProfileDropdown />
          </div>
        </div>
      </div>
    </nav>
  )
}
