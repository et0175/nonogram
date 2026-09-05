'use client'

import { useState } from 'react'
import GeneratorForm from './components/GeneratorForm'
import ResultDisplay from './components/ResultDisplay'
import styles from './page.module.css'

export default function Home() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastImageFile, setLastImageFile] = useState<File | null>(null)

  const handleSubmit = async (formData: FormData) => {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const imageFile = formData.get('image') as File | null
      if (imageFile) {
        setLastImageFile(imageFile)
      }

      const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (response.ok && data.name && data.seed !== undefined) {
        setResult({ success: true, data })
      } else {
        setError(data.error || 'Generation failed. Please try again.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleClearImage = () => {
    setLastImageFile(null)
    setResult(null)
    setError('')
  }

  return (
    <div className={styles.pageContainer}>
      <main className={styles.mainContent}>
        {/* Header */}
        <div className={styles.header}>
          <h1 className={styles.title}>🎨 Nonogram</h1>
          <p className={styles.subtitle}>
            Generate uniquely-solvable puzzles from your images
          </p>
        </div>

        {/* Main Card */}
        <div className={styles.card}>
          <GeneratorForm
            onSubmit={handleSubmit}
            loading={loading}
            lastImageFile={lastImageFile}
            onClearImage={handleClearImage}
          />
        </div>

        {/* Error Message */}
        {error && (
          <div
            className={styles.errorContainer}
            data-outcome="failure"
          >
            <div className={styles.errorHeader}>
              <div className={styles.errorIcon}>✕</div>
              <div className={styles.errorContent}>
                <h3 className={styles.errorTitle}>Error</h3>
                <p className={styles.errorMessage}>{error}</p>
                <p className={styles.errorHint}>
                  Try adjusting your settings or upload a different image.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Success Message */}
        {result && <ResultDisplay result={result} />}

        {/* Footer Info */}
        {!result && !error && (
          <div className={styles.footerInfo}>
            <p>💡 Upload an image to get started</p>
          </div>
        )}
      </main>
    </div>
  )
}
