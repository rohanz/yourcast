import { NextRequest, NextResponse } from 'next/server'

const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization')

    if (!authHeader) {
      return NextResponse.json(
        { error: 'Missing authorization header' },
        { status: 401 }
      )
    }

    // Get query parameters
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '5'
    const search = searchParams.get('search')

    // Build query string
    const queryParams = new URLSearchParams({ limit })
    if (search) {
      queryParams.append('search', search)
    }

    const response = await fetch(
      `${API_BASE_URL}/episodes/list?${queryParams.toString()}`,
      {
        headers: {
          'Authorization': authHeader
        }
      }
    )

    if (!response.ok) {
      const error = await response.text()
      console.error('Failed to fetch episodes:', error)
      return NextResponse.json(
        { error: error || 'Failed to fetch episodes' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching episodes list:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
