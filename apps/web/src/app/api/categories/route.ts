import { NextResponse } from 'next/server'
import { getApiConfig } from '@/config/app-config'

const apiConfig = getApiConfig()
const API_BASE_URL = process.env.API_BASE_URL || apiConfig.baseUrl

// Prevent caching for dynamic data
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
export const revalidate = 0

export async function GET() {
  console.log(`🔍 Next.js API route calling: ${API_BASE_URL}/episodes/categories`)
  
  try {
    const response = await fetch(`${API_BASE_URL}/episodes/categories`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
      },
      cache: 'no-store',
    })
    
    if (!response.ok) {
      throw new Error(`API responded with status ${response.status}`)
    }
    
    const data = await response.json()
    console.log(`✅ Got ${data.categories?.length || 0} categories from backend`)
    console.log(`📊 First category: ${data.categories?.[0]?.category} with ${data.categories?.[0]?.total_articles} articles`)
    
    return NextResponse.json(data)
  } catch (error) {
    console.error('❌ Error fetching categories:', error)
    return NextResponse.json(
      { error: 'Failed to fetch categories' },
      { status: 500 }
    )
  }
}
