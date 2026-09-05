import { NextRequest, NextResponse } from 'next/server'
import { writeFile, unlink } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'
import { execFile } from 'child_process'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)

/**
 * Handle puzzle generation via the nonogram CLI
 *
 * Process:
 * 1. Parse multipart form data (with optional image upload)
 * 2. Extract form fields and image file if present
 * 3. Write image to temp file if provided
 * 4. Build CLI arguments based on form fields
 * 5. Call nonogram CLI as subprocess
 * 6. Return puzzle metadata as JSON
 */
export async function POST(request: NextRequest) {
  let tempImagePath: string | null = null

  try {
    const formData = await request.formData()

    // Extract form fields - support both image and other modes for flexibility
    const mode = (formData.get('mode') as string) || 'image'
    const sizeInput = formData.get('size') as string
    const name = (formData.get('name') as string) || undefined
    const difficulty = formData.get('difficulty') as string
    const seed = formData.get('seed') as string
    const density = formData.get('density') as string
    const libraryKey = formData.get('library_key') as string
    const imageFile = formData.get('image') as File | null
    const exportFormats = formData.getAll('export_formats') as string[]

    // Parse size field (can be "20" for square or "20x30" for exact W×H)
    let width: string | null = null
    let height: string | null = null

    if (sizeInput) {
      if (sizeInput.includes('x')) {
        const [w, h] = sizeInput.split('x')
        width = w.trim()
        height = h.trim()
      } else {
        // Single number means square grid
        width = sizeInput.trim()
        height = sizeInput.trim()
      }
    }

    // Validate grid size
    if (!width || !height) {
      return NextResponse.json(
        { error: 'Grid size (width×height) is required' },
        { status: 400 }
      )
    }

    // Validate export formats
    if (exportFormats.length === 0) {
      return NextResponse.json(
        { error: 'At least one export format must be selected' },
        { status: 400 }
      )
    }

    // Build CLI arguments
    const args = ['generate']

    // Mode and size
    args.push('--mode', mode)
    args.push('--size', `${width}x${height}`)

    // Mode-specific parameters
    if (mode === 'image') {
      if (!imageFile) {
        return NextResponse.json(
          { error: 'Image file is required for image mode' },
          { status: 400 }
        )
      }
      // Save image to temp file
      const buffer = await imageFile.arrayBuffer()
      tempImagePath = join(tmpdir(), `nonogram-${Date.now()}-${imageFile.name}`)
      await writeFile(tempImagePath, Buffer.from(buffer))
      args.push('--image', tempImagePath)
    } else if (mode === 'random') {
      if (density) args.push('--density', density)
    } else if (mode === 'library') {
      if (libraryKey) args.push('--library-key', libraryKey)
    }

    // Optional parameters
    if (name) args.push('--name', name)
    if (difficulty && difficulty !== 'any') args.push('--difficulty', difficulty)
    if (seed) args.push('--seed', seed)

    // Export formats
    exportFormats.forEach(fmt => {
      args.push('--export', fmt)
    })

    console.log('[nonogram-web] Running:', 'nonogram', args.join(' '))

    // Call the CLI
    const { stdout, stderr } = await execFileAsync('nonogram', args, {
      timeout: 60000, // 60 second timeout
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer
    })

    console.log('[nonogram-web] CLI stdout:', stdout)
    if (stderr) console.log('[nonogram-web] CLI stderr:', stderr)

    // Parse CLI output to extract puzzle metadata
    // Output format:
    // seed: 12345
    // wrote /path/to/puzzle.json
    // wrote /path/to/puzzle.png
    // nudges: 0 (optional)
    const outputLines = stdout.trim().split('\n')
    const files: Record<string, string> = {}
    let seedValue: number | null = null
    let puzzleName = name || (imageFile ? imageFile.name.replace(/\.[^.]+$/, '') : 'puzzle')

    for (const line of outputLines) {
      const trimmed = line.trim()

      if (trimmed.startsWith('seed: ')) {
        seedValue = parseInt(trimmed.slice(6))
      } else if (trimmed.startsWith('wrote ')) {
        const filePath = trimmed.slice(6)
        const match = filePath.match(/\.([a-z]+)$/)
        if (match) {
          const format = match[1]
          files[format] = filePath
        }
      }
    }

    // If seed was specified by user, use it; otherwise use the printed one
    if (!seedValue) {
      seedValue = seed ? parseInt(seed) : Math.floor(Math.random() * 2147483647)
    }

    return NextResponse.json({
      name: puzzleName,
      seed: seedValue,
      files: files
    }, { status: 200 })
  } catch (error) {
    console.error('[nonogram-web] Error:', error)

    if (error instanceof Error) {
      if (error.message.includes('ENOENT')) {
        return NextResponse.json(
          { error: 'nonogram CLI not found. Install with: pip install -e .' },
          { status: 503 }
        )
      }
      if (error.message.includes('timeout')) {
        return NextResponse.json(
          { error: 'Puzzle generation timed out (exceeded 60 seconds)' },
          { status: 408 }
        )
      }
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  } finally {
    // Clean up temp image file
    if (tempImagePath) {
      try {
        await unlink(tempImagePath)
      } catch (e) {
        console.warn('[nonogram-web] Failed to clean up temp image:', e)
      }
    }
  }
}
