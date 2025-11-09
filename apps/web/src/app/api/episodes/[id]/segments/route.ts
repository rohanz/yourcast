import { NextRequest, NextResponse } from 'next/server'

interface EpisodeSegment {
  id: string;
  episode_id: string;
  start_time: number;
  end_time: number;
  text: string;
  source_id?: string;
  order_index: number;
}

const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${API_BASE_URL}/episodes/${params.id}/segments`)
    
    if (!response.ok) {
      throw new Error(`API responded with status ${response.status}`)
    }
    
    const segments: EpisodeSegment[] = await response.json()
    return NextResponse.json(segments)
  } catch (error) {
    console.error('Error fetching segments:', error)
    return NextResponse.json(
      { error: 'Failed to fetch segments' },
      { status: 500 }
    )
  }
}