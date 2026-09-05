import { NextRequest, NextResponse } from 'next/server'
import { execFile } from 'child_process'
import { promisify } from 'util'
import { dirname } from 'path'

const execFileAsync = promisify(execFile)

/**
 * Open a file or directory using the system default application
 *
 * Supports:
 * - macOS: `open` command
 * - Linux: `xdg-open` command
 * - Windows: `start` command
 */
export async function POST(request: NextRequest) {
  try {
    const { path } = await request.json()

    if (!path || typeof path !== 'string') {
      return NextResponse.json(
        { error: 'Invalid path provided' },
        { status: 400 }
      )
    }

    // Determine platform and appropriate command
    const platform = process.platform
    let command: string
    let args: string[]

    if (platform === 'darwin') {
      // macOS
      command = 'open'
      args = [path]
    } else if (platform === 'linux') {
      // Linux
      command = 'xdg-open'
      args = [path]
    } else if (platform === 'win32') {
      // Windows
      command = 'start'
      args = [path]
    } else {
      return NextResponse.json(
        { error: `Unsupported platform: ${platform}` },
        { status: 501 }
      )
    }

    // Execute the command to open the file
    try {
      await execFileAsync(command, args, {
        timeout: 5000,
      })

      return NextResponse.json(
        { success: true, message: `Opened ${path}` },
        { status: 200 }
      )
    } catch (execError) {
      // If opening the file fails, try opening the directory
      console.warn('[open-file] Failed to open file, trying directory:', execError)

      const dirPath = dirname(path)
      try {
        await execFileAsync(command, [dirPath], {
          timeout: 5000,
        })

        return NextResponse.json(
          { success: true, message: `Opened directory ${dirPath}` },
          { status: 200 }
        )
      } catch (dirError) {
        console.error('[open-file] Failed to open both file and directory:', dirError)
        return NextResponse.json(
          { error: 'Could not open file or directory' },
          { status: 500 }
        )
      }
    }
  } catch (error) {
    console.error('[open-file] Error:', error)

    if (error instanceof Error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
