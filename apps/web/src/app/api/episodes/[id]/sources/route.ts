import { NextRequest, NextResponse } from 'next/server'

interface Source {
  id: string;
  episode_id: string;
  title: string;
  url: string;
  published_date: string;
  excerpt?: string;
  summary?: string;
}

const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${API_BASE_URL}/episodes/${params.id}/sources`)
    
    if (!response.ok) {
      throw new Error(`API responded with status ${response.status}`)
    }
    
    const sources: Source[] = await response.json()
    return NextResponse.json(sources)
  } catch (error) {
    console.error('Error fetching sources:', error)
    return NextResponse.json(
      { error: 'Failed to fetch sources' },
      { status: 500 }
    )
  }
}