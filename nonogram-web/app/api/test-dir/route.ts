import { NextResponse } from 'next/server'
import { writeFile, readFile, unlink } from 'fs/promises'
import { join } from 'path'
import { cwd } from 'process'

export async function GET() {
  const workDir = cwd()
  const testFile = join(workDir, '.test-write')

  try {
    await writeFile(testFile, 'test content')
    const content = await readFile(testFile, 'utf-8')
    await unlink(testFile)

    return NextResponse.json({
      workdir: workDir,
      isWritable: true,
      testContent: content
    })
  } catch (error) {
    return NextResponse.json({
      workdir: workDir,
      isWritable: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}
