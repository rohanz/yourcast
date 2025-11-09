'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export function UserProfileDropdown() {
  const { user, signOut } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!user) return null

  const displayName = user.displayName || user.email?.split('@')[0] || 'User'
  const photoURL = user.photoURL

  const handleSignOut = async () => {
    try {
      await signOut()
      setIsOpen(false)
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Profile Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 p-1.5 md:p-2 rounded-xl hover:bg-cream-100 transition-colors duration-200"
      >
        {photoURL ? (
          <img
            src={photoURL}
            alt={displayName}
            className="w-8 h-8 md:w-10 md:h-10 rounded-full border-2 border-maroon-200"
          />
        ) : (
          <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-gradient-to-r from-maroon-600 to-maroon-700 flex items-center justify-center text-white font-bold text-xs md:text-sm border-2 border-maroon-200">
            {displayName[0].toUpperCase()}
          </div>
        )}
        <div className="hidden md:block text-left">
          <div className="text-sm font-semibold text-maroon-800">{displayName}</div>
        </div>
        <svg
          className={`w-3 h-3 md:w-4 md:h-4 text-tan-600 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-tan-200 overflow-hidden z-[10000]">
          {/* User Info */}
          <div className="px-4 py-3 border-b border-tan-200 bg-gradient-to-r from-cream-50 to-tan-50">
            <div className="flex items-center space-x-3">
              {photoURL ? (
                <img
                  src={photoURL}
                  alt={displayName}
                  className="w-12 h-12 rounded-full border-2 border-maroon-200"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-maroon-600 to-maroon-700 flex items-center justify-center text-white font-bold border-2 border-maroon-200">
                  {displayName[0].toUpperCase()}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-maroon-800 truncate">{displayName}</div>
                <div className="text-xs text-tan-600 truncate">{user.email}</div>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-2">
            <button
              onClick={handleSignOut}
              className="w-full px-4 py-2 text-left text-sm text-maroon-700 hover:bg-cream-100 transition-colors duration-150 flex items-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span>sign out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
