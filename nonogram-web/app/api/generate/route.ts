import { NextRequest, NextResponse } from 'next/server'
import { writeFile, readFile, unlink } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'

export async function POST(request: NextRequest) {
  let tempImagePath: string | null = null

  try {
    const formData = await request.formData()

    // Extract form fields
    const image = formData.get('image') as File
    const width = formData.get('width') as string
    const height = formData.get('height') as string
    const name = formData.get('name') as string
    const difficulty = formData.get('difficulty') as string
    const seed = formData.get('seed') as string
    const exportFormats = formData.getAll('export_formats') as string[]

    // Validate required fields
    if (!image) {
      return NextResponse.json(
        { error: 'Image file is required' },
        { status: 400 }
      )
    }

    if (!width || !height) {
      return NextResponse.json(
        { error: 'Width and height are required' },
        { status: 400 }
      )
    }

    if (exportFormats.length === 0) {
      return NextResponse.json(
        { error: 'At least one export format must be selected' },
        { status: 400 }
      )
    }

    const puzzleName = name || image.name.replace(/\.[^.]+$/, '')

    // Save uploaded image to temp file
    const buffer = await image.arrayBuffer()
    tempImagePath = join(tmpdir(), `${Date.now()}-${image.name}`)
    await writeFile(tempImagePath, Buffer.from(buffer))

    // Prepare form data for Python handler
    const pythonFormData = new FormData()
    pythonFormData.append('image', new Blob([buffer], { type: image.type }), image.name)
    pythonFormData.append('width', width)
    pythonFormData.append('height', height)
    pythonFormData.append('name', puzzleName)
    pythonFormData.append('mode', 'image')
    if (difficulty) pythonFormData.append('difficulty', difficulty)
    if (seed) pythonFormData.append('seed', seed)
    exportFormats.forEach(fmt => pythonFormData.append('export_formats', fmt))

    // Call Python handler
    const pythonUrl = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}/api/generate`
      : 'http://localhost:3000/api/generate'

    try {
      const pythonResponse = await fetch(pythonUrl, {
        method: 'POST',
        body: pythonFormData,
      })

      if (!pythonResponse.ok) {
        const errorData = await pythonResponse.json()
        return NextResponse.json(
          { error: errorData.error || 'Puzzle generation failed' },
          { status: pythonResponse.status }
        )
      }

      // Check if response is JSON (metadata) or binary (file)
      const contentType = pythonResponse.headers.get('content-type') || ''

      if (contentType.includes('application/json')) {
        // Return metadata response from Python
        const data = await pythonResponse.json()
        return NextResponse.json(data)
      } else {
        // Return file content directly to browser as download
        const fileBuffer = await pythonResponse.arrayBuffer()
        const filename = pythonResponse.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') || `${puzzleName}.json`

        return new NextResponse(fileBuffer, {
          status: 200,
          headers: {
            'Content-Type': contentType || 'application/octet-stream',
            'Content-Disposition': `attachment; filename="${filename}"`,
          },
        })
      }
    } catch (fetchError) {
      console.error('Error calling Python handler:', fetchError)
      return NextResponse.json(
        { error: 'Failed to generate puzzle. Python service may be unavailable.' },
        { status: 503 }
      )
    }
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  } finally {
    // Clean up temp image file
    if (tempImagePath) {
      try {
        await unlink(tempImagePath)
      } catch (e) {
        // Ignore cleanup errors
      }
    }
  }
}
