'use client'

import { FormEvent, useRef, useState, useEffect } from 'react'
import styles from './GeneratorForm.module.css'

interface GeneratorFormProps {
  onSubmit: (formData: FormData) => void
  loading: boolean
  lastImageFile?: File | null
  onClearImage?: () => void
}

interface ImageMetadata {
  width: number
  height: number
  aspectRatio: {
    width: number
    height: number
    decimal: number
  }
}

export default function GeneratorForm({ onSubmit, loading, lastImageFile, onClearImage }: GeneratorFormProps) {
  const formRef = useRef<HTMLFormElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(lastImageFile || null)
  const [previewSrc, setPreviewSrc] = useState<string>('')
  const [metadata, setMetadata] = useState<ImageMetadata | null>(null)
  const [suggestions, setSuggestions] = useState<Array<[number, number]>>([])
  const [sizeInput, setSizeInput] = useState<string>('')
  const [customName, setCustomName] = useState<string>('')
  const [isRetry, setIsRetry] = useState<boolean>(!!lastImageFile)

  // GCD algorithm for ratio simplification
  const gcd = (a: number, b: number): number => {
    return b === 0 ? a : gcd(b, a % b)
  }

  // Extract image metadata and calculate suggestions
  const extractImageMetadata = (file: File): Promise<ImageMetadata> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const img = new Image()
        img.onload = () => {
          const width = img.naturalWidth
          const height = img.naturalHeight
          const divisor = gcd(width, height)
          const aspectRatio = {
            width: width / divisor,
            height: height / divisor,
            decimal: Math.round((width / height) * 100) / 100,
          }
          resolve({ width, height, aspectRatio })
        }
        img.onerror = () => reject(new Error('Could not load image'))
        img.src = e.target?.result as string
      }
      reader.onerror = () => reject(new Error('Could not read file'))
      reader.readAsDataURL(file)
    })
  }

  // Generate 2-3 suggested dimensions matching image aspect ratio
  const suggestDimensions = (metadata: ImageMetadata): Array<[number, number]> => {
    const minSize = 10
    const maxSize = 30
    const targetRatio = metadata.aspectRatio.width / metadata.aspectRatio.height

    const candidates: Array<[number, number, number]> = []

    for (let w = minSize; w <= maxSize; w++) {
      for (let h = minSize; h <= maxSize; h++) {
        const gridRatio = w / h
        const ratioError = Math.abs(gridRatio - targetRatio) / targetRatio
        candidates.push([ratioError, w, h])
      }
    }

    candidates.sort((a, b) => a[0] - b[0])
    const top3 = candidates.slice(0, 3).map(([, w, h]) => [w, h] as [number, number])
    return top3
  }

  // Handle file selection
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) {
      setSelectedFile(null)
      setPreviewSrc('')
      setMetadata(null)
      setSuggestions([])
      setSizeInput('')
      return
    }

    // Verify it's an image
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file (PNG, JPEG, GIF, WebP, BMP)')
      e.target.value = ''
      return
    }

    try {
      // Extract metadata and create preview
      const meta = await extractImageMetadata(file)
      const sugg = suggestDimensions(meta)

      setSelectedFile(file)
      setMetadata(meta)
      setSuggestions(sugg)
      setSizeInput('')
      setIsRetry(false)

      // Create preview
      const reader = new FileReader()
      reader.onload = (evt) => {
        setPreviewSrc(evt.target?.result as string)
      }
      reader.readAsDataURL(file)
    } catch (error) {
      alert('Could not process image: ' + (error instanceof Error ? error.message : 'Unknown error'))
      e.target.value = ''
      setSelectedFile(null)
      setMetadata(null)
      setSuggestions([])
    }
  }

  // Handle suggestion button click
  const handleSuggestionClick = (w: number, h: number) => {
    setSizeInput(`${w}x${h}`)
  }

  // Handle form submission
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    if (!selectedFile) {
      alert('Please select an image')
      return
    }

    const formData = new FormData(formRef.current!)
    formData.set('image', selectedFile)
    formData.set('mode', 'image')

    onSubmit(formData)
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className={styles.form}
    >
      {/* Image Upload Section */}
      <div className={styles.formGroup}>
        <label>Image</label>
        <input
          ref={fileInputRef}
          type="file"
          name="image"
          accept="image/*"
          onChange={handleFileChange}
        />
        <small>Select the picture to convert (PNG, JPEG, GIF, WebP, BMP)</small>
      </div>

      {/* Image Metadata & Preview */}
      {selectedFile && metadata && (
        <div className={styles.previewSection}>
          {/* Preview Image */}
          <div className={styles.previewContainer}>
            {previewSrc && (
              <img
                src={previewSrc}
                alt="Preview"
                className={styles.previewImage}
              />
            )}
          </div>

          {/* Metadata & Suggestions */}
          <div className={styles.metadataContainer}>
            <div className={styles.metadataBox}>
              <h3>Image Info</h3>
              <p>
                <strong>{metadata.width} × {metadata.height}</strong> pixels
              </p>
              <p>
                Aspect ratio: <strong>{Math.round(metadata.aspectRatio.width)}:{Math.round(metadata.aspectRatio.height)}</strong> ({metadata.aspectRatio.decimal})
              </p>
            </div>

            {/* Suggestion Buttons */}
            {suggestions.length > 0 && (
              <div className={styles.suggestionsBox}>
                <h4>Suggested sizes (click to set)</h4>
                <div className={styles.suggestionButtons}>
                  {suggestions.map(([w, h]) => (
                    <button
                      key={`${w}x${h}`}
                      type="button"
                      onClick={() => handleSuggestionClick(w, h)}
                      className={`${styles.suggestionButton} ${
                        sizeInput === `${w}x${h}` ? styles.suggestionButtonActive : ''
                      }`}
                    >
                      {w}×{h}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isRetry && onClearImage && (
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null)
                  setPreviewSrc('')
                  setMetadata(null)
                  setSuggestions([])
                  setSizeInput('')
                  setIsRetry(false)
                  if (fileInputRef.current) fileInputRef.current.value = ''
                  onClearImage()
                }}
                className={styles.clearButton}
              >
                ↺ Upload new image
              </button>
            )}
          </div>
        </div>
      )}

      {/* Size Input */}
      <div className={styles.formGroup}>
        <label>Size</label>
        <input
          type="text"
          name="size"
          value={sizeInput}
          onChange={(e) => setSizeInput(e.target.value)}
          placeholder="e.g., 20 or 20x30"
        />
        <small>Optional. One number for square grid (e.g., 20), or WxH for exact dimensions (e.g., 20x30)</small>
      </div>

      {/* Export Formats */}
      <div className={styles.formGroup}>
        <label>Export Formats</label>
        <div className={styles.checkboxGroup}>
          {['json', 'csv', 'png', 'svg', 'pdf'].map((format) => (
            <label key={format} className={styles.checkboxLabel}>
              <input
                type="checkbox"
                name="export_formats"
                value={format}
                defaultChecked={format === 'pdf'}
              />
              <span>{format.toUpperCase()}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Configuration Grid */}
      <div className={styles.configGrid}>
        {/* Difficulty */}
        <div className={styles.formGroup}>
          <label>Difficulty</label>
          <select name="difficulty" defaultValue="any">
            <option value="any">(any)</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        {/* Seed */}
        <div className={styles.formGroup}>
          <label>Seed</label>
          <input
            type="text"
            name="seed"
            inputMode="numeric"
            placeholder="random"
          />
        </div>

        {/* Puzzle Name */}
        <div className={styles.formGroup}>
          <label>Name</label>
          <input
            type="text"
            name="name"
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
            placeholder="auto-generated"
          />
        </div>

        {/* Output Directory */}
        <div className={styles.formGroup}>
          <label>Output Directory</label>
          <input
            type="text"
            name="out"
            placeholder="."
          />
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading || !selectedFile}
        className={styles.submitButton}
        style={{
          opacity: loading || !selectedFile ? 0.6 : 1,
          cursor: loading || !selectedFile ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? 'Generating...' : 'Generate Puzzle'}
      </button>
    </form>
  )
}
