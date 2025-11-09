'use client'

import { createContext, useContext, useState, useRef, useCallback, ReactNode } from 'react'

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

interface UserPreferences {
  subcategories: string[];
  custom_tags?: string[];
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

interface DataContextType {
  // Categories cache
  categories: Category[] | null;
  setCategories: (categories: Category[]) => void;

  // User preferences cache
  userPreferences: UserPreferences | null;
  setUserPreferences: (prefs: UserPreferences) => void;

  // Current episode cache
  currentEpisode: Episode | null;
  setCurrentEpisode: (episode: Episode | null) => void;

  // Past episodes cache
  pastEpisodes: Episode[] | null;
  setPastEpisodes: (episodes: Episode[]) => void;

  // Generate episode callback
  generateEpisode: () => Promise<void>;
  setGenerateEpisode: (fn: (() => Promise<void>) | null) => void;

  // Generation state
  isGenerating: boolean;
  setIsGenerating: (generating: boolean) => void;

  // Checking state (for initial load)
  isCheckingInitialLoad: boolean;
  setIsCheckingInitialLoad: (checking: boolean) => void;

  // Clear all cache
  clearCache: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined)

export function DataProvider({ children }: { children: ReactNode }) {
  const [categories, setCategories] = useState<Category[] | null>(null)
  const [userPreferences, setUserPreferences] = useState<UserPreferences | null>(null)
  const [currentEpisode, setCurrentEpisode] = useState<Episode | null>(null)
  const [pastEpisodes, setPastEpisodes] = useState<Episode[] | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isCheckingInitialLoad, setIsCheckingInitialLoad] = useState(true)

  // Use ref to store the function, avoiding useState issues with functions
  const generateEpisodeRef = useRef<(() => Promise<void>) | null>(null)

  const setGenerateEpisode = useCallback((fn: (() => Promise<void>) | null) => {
    generateEpisodeRef.current = fn
  }, [])

  const generateEpisode = useCallback(async () => {
    if (generateEpisodeRef.current) {
      await generateEpisodeRef.current()
    }
  }, [])

  const clearCache = () => {
    setCategories(null)
    setUserPreferences(null)
    setCurrentEpisode(null)
    setPastEpisodes(null)
  }

  return (
    <DataContext.Provider
      value={{
        categories,
        setCategories,
        userPreferences,
        setUserPreferences,
        currentEpisode,
        setCurrentEpisode,
        pastEpisodes,
        setPastEpisodes,
        generateEpisode,
        setGenerateEpisode,
        isGenerating,
        setIsGenerating,
        isCheckingInitialLoad,
        setIsCheckingInitialLoad,
        clearCache
      }}
    >
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider')
  }
  return context
}
