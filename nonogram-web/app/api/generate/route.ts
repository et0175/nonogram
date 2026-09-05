import { NextRequest, NextResponse } from 'next/server'
import { writeFile, unlink, readFile } from 'fs/promises'
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

  console.log('[DIAGNOSTIC] API /generate called')
  console.log('[DIAGNOSTIC] NODE_ENV:', process.env.NODE_ENV)
  console.log('[DIAGNOSTIC] PYTHONPATH:', process.env.PYTHONPATH)
  console.log('[DIAGNOSTIC] PATH:', process.env.PATH)

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
    const outDir = formData.get('out') as string

    // Parse size field (optional, can be "20" for square or "20x30" for exact W×H)
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
    // Size is optional - CLI will use defaults if not provided

    // Validate export formats
    console.log('[DIAGNOSTIC] exportFormats received:', exportFormats, 'length:', exportFormats.length)
    if (exportFormats.length === 0) {
      return NextResponse.json(
        { error: 'At least one export format must be selected' },
        { status: 400 }
      )
    }

    // Build CLI arguments
    const args = ['generate']

    // Mode
    args.push('--mode', mode)

    // Size (optional)
    if (width && height) {
      args.push('--size', `${width}x${height}`)
    }

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
    // Only pass seed if it's a valid integer (not "random" or empty)
    if (seed && seed.trim() !== '' && seed.trim() !== 'random') {
      const seedInt = parseInt(seed, 10)
      if (!isNaN(seedInt)) {
        args.push('--seed', String(seedInt))
      }
    }

    // Export formats
    exportFormats.forEach(fmt => {
      args.push('--export', fmt)
    })

    // Output directory (optional)
    if (outDir && outDir.trim() !== '') {
      args.push('--out', outDir.trim())
    }

    // Call nonogram CLI with diagnostics
    const fullCommand = ['python3', '-m', 'nonogram', ...args]
    console.log('[DIAGNOSTIC] About to execute:', fullCommand.join(' '))
    console.log('[DIAGNOSTIC] Args array:', args)
    console.log('[DIAGNOSTIC] Full command array:', fullCommand)

    const env = {
      ...process.env,
      PYTHONPATH: '/app/src',
    } as NodeJS.ProcessEnv

    console.log('[DIAGNOSTIC] Environment:', { PYTHONPATH: env.PYTHONPATH, PATH: env.PATH?.substring(0, 100) })

    const { stdout, stderr } = await execFileAsync('python3', ['-m', 'nonogram', ...args], {
      timeout: 60000,
      maxBuffer: 10 * 1024 * 1024,
      env,
    })

    console.log('[DIAGNOSTIC] Python execution succeeded')
    console.log('[DIAGNOSTIC] stdout length:', stdout.length)
    console.log('[DIAGNOSTIC] stdout:', stdout)
    console.log('[DIAGNOSTIC] stderr:', stderr)

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

    console.log('[DIAGNOSTIC] Output lines:', outputLines)
    console.log('[DIAGNOSTIC] Export formats requested:', exportFormats)

    for (const line of outputLines) {
      const trimmed = line.trim()
      console.log('[DIAGNOSTIC] Processing line:', trimmed)

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

    console.log('[DIAGNOSTIC] Parsed files:', files)

    // If seed was specified by user, use it; otherwise use the printed one
    if (!seedValue) {
      seedValue = seed ? parseInt(seed) : Math.floor(Math.random() * 2147483647)
    }

    // Read file contents for download
    const filesWithContent: Record<string, { path: string; data: string; mimeType: string }> = {}
    const mimeTypes: Record<string, string> = {
      json: 'application/json',
      csv: 'text/csv',
      png: 'image/png',
      svg: 'image/svg+xml',
      pdf: 'application/pdf'
    }

    for (const [format, filePath] of Object.entries(files)) {
      try {
        const fileContent = await readFile(filePath)
        const base64Data = fileContent.toString('base64')
        filesWithContent[format] = {
          path: filePath,
          data: base64Data,
          mimeType: mimeTypes[format] || 'application/octet-stream'
        }
      } catch (readError) {
        console.error(`[nonogram-web] Failed to read file ${filePath}:`, readError)
        filesWithContent[format] = {
          path: filePath,
          data: '',
          mimeType: mimeTypes[format] || 'application/octet-stream'
        }
      }
    }

    return NextResponse.json({
      name: puzzleName,
      seed: seedValue,
      files: filesWithContent,
      _debug: {
        cliArgs: fullCommand,
        exportFormats: exportFormats,
        filesFound: Object.keys(files),
        cliStdoutLines: outputLines.slice(0, 20)
      }
    }, { status: 200 })
  } catch (error) {
    console.error('[nonogram-web] Full error object:', JSON.stringify(error, Object.getOwnPropertyNames(error)))

    if (error instanceof Error) {
      const errorMsg = error.message
      console.error('[nonogram-web] Error message:', errorMsg)

      if (errorMsg.includes('ENOENT')) {
        return NextResponse.json(
          { error: `ENOENT - Command not found: ${errorMsg}` },
          { status: 503 }
        )
      }
      if (errorMsg.includes('timeout')) {
        return NextResponse.json(
          { error: 'Puzzle generation timed out (exceeded 60 seconds)' },
          { status: 408 }
        )
      }
      return NextResponse.json(
        { error: `API Error: ${errorMsg}` },
        { status: 500 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error - unknown error type' },
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
