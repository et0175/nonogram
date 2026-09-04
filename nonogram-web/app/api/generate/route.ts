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

    // Output directory: use provided or default to ./puzzles
    // Note: In web context, this is server-side path. Eventually should stream file to browser.
    const outputDir = out && out.trim() ? out.trim() : './puzzles'

    // Validate that at least one export format is selected
    if (exportFormats.length === 0) {
      return NextResponse.json(
        { error: 'At least one export format must be selected' },
        { status: 400 }
      )
    }

    // Build response with only selected export formats
    const puzzleName = name || image.name.replace(/\.[^.]+$/, '')
    const files: Record<string, string> = {}

    // Only include paths for selected export formats
    if (exportFormats.includes('json')) {
      files.json = `${outputDir}/${puzzleName}.json`
    }
    if (exportFormats.includes('csv')) {
      files.csv = `${outputDir}/${puzzleName}.csv`
    }
    if (exportFormats.includes('png')) {
      files.png = `${outputDir}/${puzzleName}.png`
    }
    if (exportFormats.includes('svg')) {
      files.svg = `${outputDir}/${puzzleName}.svg`
    }
    if (exportFormats.includes('pdf')) {
      files.pdf = `${outputDir}/${puzzleName}.pdf`
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
