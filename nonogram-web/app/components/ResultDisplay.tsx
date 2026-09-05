'use client'

import { useState } from 'react'
import styles from './ResultDisplay.module.css'

interface ResultDisplayProps {
  result: {
    success: boolean
    data?: {
      name: string
      seed: number
      files: Record<string, string>
    }
  }
}

export default function ResultDisplay({ result }: ResultDisplayProps) {
  const [copiedPath, setCopiedPath] = useState<string | null>(null)

  if (!result.success) {
    return null
  }

  const { name, seed, files } = result.data!

  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path)
    setCopiedPath(path)
    setTimeout(() => setCopiedPath(null), 2000)
  }

  const handleOpenFile = async (path: string) => {
    try {
      const response = await fetch('/api/open-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!response.ok) {
        alert('Could not open file. Copy the path and open manually.')
      }
    } catch (err) {
      console.error('Error opening file:', err)
      alert('Could not open file. Copy the path and open manually.')
    }
  }

  return (
    <div
      className={styles.resultContainer}
      data-outcome="success"
    >
      <div className={styles.resultHeader}>
        <div className={styles.resultIcon}>✓</div>
        <div className={styles.resultContent}>
          <h2 className={styles.resultTitle}>Puzzle Generated Successfully</h2>

          <div className={styles.resultMetadata}>
            <p>
              <span className={styles.label}>Name:</span>
              <code>{name}</code>
            </p>
            <p>
              <span className={styles.label}>Seed:</span>
              <code>{seed}</code>
            </p>
          </div>

          <div className={styles.filesSection}>
            <h3 className={styles.filesTitle}>Generated Files</h3>
            <div className={styles.filesList}>
              {Object.entries(files).map(([format, path]) => (
                <div
                  key={format}
                  className={styles.fileItem}
                >
                  <div className={styles.fileInfo}>
                    <span className={styles.fileName}>{path}</span>
                    <span className={styles.fileFormat}>{format.toUpperCase()}</span>
                  </div>
                  <div className={styles.fileActions}>
                    <button
                      className={styles.fileButton}
                      onClick={() => handleCopyPath(path)}
                      title="Copy file path to clipboard"
                    >
                      {copiedPath === path ? '✓ Copied' : 'Copy Path'}
                    </button>
                    <button
                      className={styles.fileButton}
                      onClick={() => handleOpenFile(path)}
                      title="Open file"
                    >
                      Open
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className={styles.resultFooter}>
            Files are saved in your configured output directory. You can generate another puzzle or upload a new image.
          </p>
        </div>
      </div>
    </div>
  )
}
