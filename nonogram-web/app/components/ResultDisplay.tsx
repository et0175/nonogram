'use client'

import { useState } from 'react'
import styles from './ResultDisplay.module.css'

interface ResultDisplayProps {
  result: {
    success: boolean
    data?: {
      name: string
      seed: number
      files: Record<string, { path: string; data: string; mimeType: string }>
    }
  }
}

export default function ResultDisplay({ result }: ResultDisplayProps) {
  const [copiedPath, setCopiedPath] = useState<string | null>(null)

  if (!result.success) {
    return null
  }

  const { name, seed, files } = result.data!

  const handleDownloadFile = (format: string, data: string, mimeType: string, fileName: string) => {
    try {
      const binaryString = atob(data)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      const blob = new Blob([bytes], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${fileName}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error downloading file:', err)
      alert('Could not download file')
    }
  }

  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path)
    setCopiedPath(path)
    setTimeout(() => setCopiedPath(null), 2000)
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
              {Object.entries(files).map(([format, fileInfo]) => (
                <div
                  key={format}
                  className={styles.fileItem}
                >
                  <div className={styles.fileInfo}>
                    <span className={styles.fileName}>{name}.{format}</span>
                    <span className={styles.fileFormat}>{format.toUpperCase()}</span>
                  </div>
                  <div className={styles.fileActions}>
                    <button
                      className={styles.fileButton}
                      onClick={() => handleDownloadFile(format, fileInfo.data, fileInfo.mimeType, name)}
                      title="Download file"
                    >
                      ⬇ Download
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className={styles.resultFooter}>
            Click Download to save files to your computer. You can generate another puzzle or upload a new image.
          </p>
        </div>
      </div>
    </div>
  )
}
