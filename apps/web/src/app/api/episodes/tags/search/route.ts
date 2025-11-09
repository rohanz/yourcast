import { NextRequest, NextResponse } from 'next/server'

const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'

export async function GET(request: NextRequest) {
  try {
    // Get query parameter
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('query')

    if (!query) {
      return NextResponse.json(
        { tags: [] },
        { status: 200 }
      )
    }

    const response = await fetch(
      `${API_BASE_URL}/episodes/tags/search?query=${encodeURIComponent(query)}`
    )

    if (!response.ok) {
      const error = await response.text()
      console.error('Failed to search tags:', error)
      return NextResponse.json(
        { error: error || 'Failed to search tags' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error searching tags:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
