'use client'

import React, { createContext, useContext, useRef, useCallback } from 'react'

interface AudioContextType {
  registerAudio: (id: string, audioElement: HTMLAudioElement) => void
  unregisterAudio: (id: string) => void
  pauseAllAudio: () => void
  pauseOtherAudio: (excludeId: string) => void
}

const AudioContext = createContext<AudioContextType | undefined>(undefined)

export function AudioProvider({ children }: { children: React.ReactNode }) {
  // Industry standard: Use Map to track audio refs by ID
  // This is how Spotify/YouTube manage multiple audio/video elements
  const audioRefsMap = useRef<Map<string, HTMLAudioElement>>(new Map())

  const registerAudio = useCallback((id: string, audioElement: HTMLAudioElement) => {
    audioRefsMap.current.set(id, audioElement)
  }, [])

  const unregisterAudio = useCallback((id: string) => {
    audioRefsMap.current.delete(id)
  }, [])

  const pauseAllAudio = useCallback(() => {
    audioRefsMap.current.forEach((audio) => {
      if (!audio.paused) {
        audio.pause()
      }
    })
  }, [])

  const pauseOtherAudio = useCallback((excludeId: string) => {
    audioRefsMap.current.forEach((audio, id) => {
      if (id !== excludeId && !audio.paused) {
        audio.pause()
      }
    })
  }, [])

  return (
    <AudioContext.Provider value={{ registerAudio, unregisterAudio, pauseAllAudio, pauseOtherAudio }}>
      {children}
    </AudioContext.Provider>
  )
}

export function useAudio() {
  const context = useContext(AudioContext)
  if (context === undefined) {
    throw new Error('useAudio must be used within an AudioProvider')
  }
  return context
}
