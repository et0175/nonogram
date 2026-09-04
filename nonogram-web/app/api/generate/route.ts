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

    // TODO: Call Python API handler at /api/generate.py
    // For now, return mock response with selected formats only
    const files: Record<string, string> = {}

    if (exportFormats.includes('json')) {
      files.json = `${puzzleName}.json`
    }
    if (exportFormats.includes('csv')) {
      files.csv = `${puzzleName}.csv`
    }
    if (exportFormats.includes('png')) {
      files.png = `${puzzleName}.png`
    }
    if (exportFormats.includes('svg')) {
      files.svg = `${puzzleName}.svg`
    }
    if (exportFormats.includes('pdf')) {
      files.pdf = `${puzzleName}.pdf`
    }

    return NextResponse.json({
      success: true,
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
