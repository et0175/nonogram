'use client'

import { useState } from 'react'
import GeneratorForm from './components/GeneratorForm'
import ResultDisplay from './components/ResultDisplay'

export default function Home() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (formData: FormData) => {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      // Check if form has file (image upload) - always use multipart for image mode
      const hasFile = formData.has('image') && formData.get('image') instanceof File

      const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData, // Always use FormData which handles both file and non-file fields
      })

      const data = await response.json()

      if (response.ok) {
        setResult({ success: true, data })
      } else {
        setError(data.error || 'Generation failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem' }}>
      <h1>Nonogram Generator</h1>
      <GeneratorForm onSubmit={handleSubmit} loading={loading} />
      {error && (
        <div
          data-outcome="failure"
          style={{
            color: '#d32f2f',
            backgroundColor: '#ffebee',
            border: '1px solid #ef5350',
            padding: '1rem',
            borderRadius: '4px',
            marginTop: '1rem',
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}
      {result && (
        <div
          data-outcome="success"
          style={{
            color: '#1976d2',
            backgroundColor: '#e3f2fd',
            border: '1px solid #64b5f6',
            padding: '1rem',
            borderRadius: '4px',
            marginTop: '1rem',
          }}
        >
          <strong>Success!</strong> Puzzle generated successfully.
          <ResultDisplay result={result} />
        </div>
      )}
    </main>
  )
}
