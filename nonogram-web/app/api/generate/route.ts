import { NextRequest, NextResponse } from 'next/server'
import { writeFile, readFile, unlink, mkdtemp, rm } from 'fs/promises'
import { join } from 'path'
import { tmpdir } from 'os'
import { execFile } from 'child_process'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)

export async function POST(request: NextRequest) {
  let tempImagePath: string | null = null
  let tempOutputDir: string | null = null

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
    const sizeArg = `${width}x${height}`

    // Save uploaded image to temp file
    const buffer = await image.arrayBuffer()
    tempImagePath = join(tmpdir(), `${Date.now()}-${image.name}`)
    await writeFile(tempImagePath, Buffer.from(buffer))

    // Create temp output directory
    tempOutputDir = await mkdtemp(join(tmpdir(), 'nonogram-'))

    // Build CLI command
    const args = [
      'generate',
      '--mode', 'image',
      '--image', tempImagePath,
      '--size', sizeArg,
      '--out', tempOutputDir,
    ]

    // Add optional parameters
    if (difficulty && difficulty !== 'any') {
      args.push('--difficulty', difficulty)
    }
    if (seed) {
      args.push('--seed', seed)
    }

    // Add export formats
    exportFormats.forEach(fmt => {
      args.push('--export', fmt)
    })

    console.log('Running nonogram CLI:', args.join(' '))

    // Call Python CLI via subprocess
    const { stdout, stderr } = await execFileAsync('nonogram', args, {
      timeout: 60000, // 60 second timeout
    })

    console.log('Nonogram CLI output:', stdout)

    // Read the first generated file and return it
    // Try each format in order until we find one
    for (const format of exportFormats) {
      const filePath = join(tempOutputDir, `${puzzleName}.${format}`)
      try {
        const fileContent = await readFile(filePath)
        let contentType = 'application/octet-stream'

        switch (format) {
          case 'json':
            contentType = 'application/json'
            break
          case 'csv':
            contentType = 'text/csv'
            break
          case 'png':
            contentType = 'image/png'
            break
          case 'svg':
            contentType = 'image/svg+xml'
            break
          case 'pdf':
            contentType = 'application/pdf'
            break
        }

        return new NextResponse(fileContent, {
          status: 200,
          headers: {
            'Content-Type': contentType,
            'Content-Disposition': `attachment; filename="${puzzleName}.${format}"`,
          },
        })
      } catch (e) {
        // File not found, try next format
        continue
      }
    }

    // If no file was generated
    throw new Error('No puzzle files were generated')
  } catch (error) {
    console.error('API error:', error)
    const errorMessage = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    )
  } finally {
    // Clean up temp files
    if (tempImagePath) {
      try {
        await unlink(tempImagePath)
      } catch (e) {
        // Ignore cleanup errors
      }
    }
    if (tempOutputDir) {
      try {
        await rm(tempOutputDir, { recursive: true })
      } catch (e) {
        // Ignore cleanup errors
      }
    }
  }
}
