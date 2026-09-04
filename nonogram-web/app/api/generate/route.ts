import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()

    // Extract form fields
    const image = formData.get('image') as File
    const width = formData.get('width') as string
    const height = formData.get('height') as string
    const name = formData.get('name') as string
    const out = formData.get('out') as string
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

    // Build response with only selected export formats
    const puzzleName = name || image.name.replace(/\.[^.]+$/, '')
    const files: Record<string, string> = {}

    // Only include paths for selected export formats
    if (exportFormats.includes('json')) {
      files.json = `${out || '/output'}/${puzzleName}.json`
    }
    if (exportFormats.includes('csv')) {
      files.csv = `${out || '/output'}/${puzzleName}.csv`
    }
    if (exportFormats.includes('png')) {
      files.png = `${out || '/output'}/${puzzleName}.png`
    }
    if (exportFormats.includes('svg')) {
      files.svg = `${out || '/output'}/${puzzleName}.svg`
    }
    if (exportFormats.includes('pdf')) {
      files.pdf = `${out || '/output'}/${puzzleName}.pdf`
    }

    // TODO: Call Python backend to generate puzzle
    // For now, return a mock success response for testing
    return NextResponse.json({
      name: puzzleName,
      seed: seed ? parseInt(seed) : Math.floor(Math.random() * 1000000),
      files,
    })
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}
