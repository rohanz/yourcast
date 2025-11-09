import { NextRequest, NextResponse } from 'next/server'

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

const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Disable caching for this route
export const dynamic = 'force-dynamic'
export const revalidate = 0

// Transform internal API URLs to public URLs
function transformUrls(episode: Episode): Episode {
  return {
    ...episode,
    audio_url: episode.audio_url?.replace(API_BASE_URL, PUBLIC_API_URL),
    transcript_url: episode.transcript_url?.replace(API_BASE_URL, PUBLIC_API_URL),
    vtt_url: episode.vtt_url?.replace(API_BASE_URL, PUBLIC_API_URL),
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Disable caching to get fresh data
    const response = await fetch(`${API_BASE_URL}/episodes/${params.id}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache'
      }
    })

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: 'Episode not found' }, { status: 404 })
      }
      throw new Error(`API responded with status ${response.status}`)
    }

    const episode: Episode = await response.json()
    const transformedEpisode = transformUrls(episode)
    return NextResponse.json(transformedEpisode)
  } catch (error) {
    console.error('Error fetching episode:', error)
    return NextResponse.json(
      { error: 'Failed to fetch episode' },
      { status: 500 }
    )
  }
}