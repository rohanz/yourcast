
const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
export const revalidate = 0

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const episodeId = params.id

  const encoder = new TextEncoder()
  
  const customReadable = new ReadableStream({
    async start(controller) {
      let reader: ReadableStreamDefaultReader<Uint8Array> | undefined
      try {
        console.log(`🔌 SSE proxy connecting to backend for episode ${episodeId}`)
        
        const response = await fetch(`${API_BASE_URL}/episodes/${episodeId}/events`, {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
        })

        if (!response.ok) {
          throw new Error(`Backend responded with ${response.status}`)
        }

        console.log(`✅ Backend SSE connection established for episode ${episodeId}`)

        reader = response.body?.getReader()
        // Close upstream if the client disconnects
        request.signal.addEventListener('abort', () => {
          try { reader?.cancel() } catch {}
          try { controller.close() } catch {}
        })
        if (!reader) {
          throw new Error('No readable stream from backend')
        }

        const decoder = new TextDecoder()

        try {
          while (true) {
            const { done, value } = await reader.read()
            
            if (done) {
              console.log(`🏁 SSE stream completed for episode ${episodeId}`)
              break
            }

            const chunk = decoder.decode(value, { stream: true })
            console.log(`📡 Forwarding SSE chunk for episode ${episodeId}:`, chunk.trim())
            
            // Forward the chunk to the client
            controller.enqueue(encoder.encode(chunk))
          }
        } finally {
          reader.releaseLock()
        }

      } catch (error) {
        console.error(`❌ SSE proxy error for episode ${episodeId}:`, error)
        
        const errorEvent = `data: ${JSON.stringify({
          episode_id: episodeId,
          status: 'error', 
          error: error instanceof Error ? error.message : 'Unknown error'
        })}\n\n`
        
        controller.enqueue(encoder.encode(errorEvent))
      } finally {
        controller.close()
      }
    }
  })

  return new Response(customReadable, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no' // Disable nginx buffering
    }
  })
}
