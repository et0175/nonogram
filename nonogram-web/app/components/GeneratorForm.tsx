import { FormEvent, useRef, useState, useEffect } from 'react'

interface GeneratorFormProps {
  onSubmit: (formData: FormData) => void
  loading: boolean
  lastImageFile?: File | null
  onClearImage?: () => void
}

export default function GeneratorForm({ onSubmit, loading, lastImageFile, onClearImage }: GeneratorFormProps) {
  const formRef = useRef<HTMLFormElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(lastImageFile || null)
  const [originalImage, setOriginalImage] = useState<HTMLImageElement | null>(null)
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null)
  const [croppedSize, setCroppedSize] = useState<{ width: number; height: number } | null>(null)
  const [suggestedSizes, setSuggestedSizes] = useState<Array<{ label: string; width: number; height: number }>>([])
  const [width, setWidth] = useState<number>(20)
  const [height, setHeight] = useState<number>(20)
  const [customName, setCustomName] = useState<string>('')
  const [isRetry, setIsRetry] = useState<boolean>(!!lastImageFile)

  // CARD-037: Pre-populate form with cached image on retry
  useEffect(() => {
    if (lastImageFile && !selectedFile) {
      setSelectedFile(lastImageFile)
      setIsRetry(true)
      // Load the image to show preview
      const reader = new FileReader()
      reader.onloadend = () => {
        const img = new Image()
        img.onload = () => {
          setOriginalImage(img)
          setImageSize({ width: img.naturalWidth, height: img.naturalHeight })
          updateCroppedPreview(img, width, height)
        }
        img.src = reader.result as string
      }
      reader.readAsDataURL(lastImageFile)
    }
  }, [lastImageFile])

  // Detect ink bounding box (remove white margins)
  const detectInkBoundingBox = (img: HTMLImageElement): { x: number; y: number; width: number; height: number } => {
    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return { x: 0, y: 0, width: img.naturalWidth, height: img.naturalHeight }

    ctx.drawImage(img, 0, 0)
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const data = imageData.data

    // Find ink pixels (threshold 128 = mid-grey)
    const INK_THRESHOLD = 128
    let minX = canvas.width
    let minY = canvas.height
    let maxX = -1
    let maxY = -1

    for (let i = 0; i < data.length; i += 4) {
      // Convert to greyscale
      const r = data[i]
      const g = data[i + 1]
      const b = data[i + 2]
      const grey = 0.299 * r + 0.587 * g + 0.114 * b

      if (grey < INK_THRESHOLD) {
        const pixelIndex = i / 4
        const px = pixelIndex % canvas.width
        const py = Math.floor(pixelIndex / canvas.width)

        minX = Math.min(minX, px)
        minY = Math.min(minY, py)
        maxX = Math.max(maxX, px)
        maxY = Math.max(maxY, py)
      }
    }

    // If no ink found, return full extent
    if (maxX === -1) {
      return { x: 0, y: 0, width: canvas.width, height: canvas.height }
    }

    return {
      x: minX,
      y: minY,
      width: maxX - minX + 1,
      height: maxY - minY + 1,
    }
  }

  // Calculate centre-crop box
  const calculateCropBox = (
    sourceBox: { width: number; height: number },
    gridWidth: number,
    gridHeight: number
  ): { width: number; height: number } => {
    const sourceRatio = sourceBox.width / sourceBox.height
    const gridRatio = gridWidth / gridHeight

    if (sourceRatio >= gridRatio) {
      // Source is wider - crop width
      const croppedWidth = Math.round(sourceBox.height * gridRatio)
      return { width: croppedWidth, height: sourceBox.height }
    } else {
      // Source is taller - crop height
      const croppedHeight = Math.round(sourceBox.width / gridRatio)
      return { width: sourceBox.width, height: croppedHeight }
    }
  }

  const computeSuggestedSizes = (boundingBox: { width: number; height: number }) => {
    const minSize = 10
    const maxSize = 30
    const targetRatio = boundingBox.width / boundingBox.height

    // Generate suggestions matching image aspect ratio (same algorithm as Python metadata module)
    const suggestions: Array<{ label: string; width: number; height: number }> = []
    const candidates: Array<[number, number, number]> = [] // [error, w, h]

    for (let w = minSize; w <= maxSize; w++) {
      for (let h = minSize; h <= maxSize; h++) {
        const gridRatio = w / h
        const ratioError = Math.abs(gridRatio - targetRatio) / targetRatio
        candidates.push([ratioError, w, h])
      }
    }

    // Sort by error (best matches first) and take top 3
    candidates.sort((a, b) => a[0] - b[0])
    for (let i = 0; i < Math.min(3, candidates.length); i++) {
      const [, w, h] = candidates[i]
      suggestions.push({ label: `${w}×${h}`, width: w, height: h })
    }

    setSuggestedSizes(suggestions)
    if (suggestions.length > 0) {
      setWidth(suggestions[0].width)
      setHeight(suggestions[0].height)
    }
  }

  const updateCroppedPreview = (img: HTMLImageElement, gridW: number, gridH: number) => {
    const boundingBox = detectInkBoundingBox(img)
    const cropBox = calculateCropBox(boundingBox, gridW, gridH)
    setCroppedSize(cropBox)
    computeSuggestedSizes(boundingBox)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setSelectedFile(file)

      const reader = new FileReader()
      reader.onloadend = () => {
        const img = new Image()
        img.onload = () => {
          setOriginalImage(img)
          setImageSize({ width: img.naturalWidth, height: img.naturalHeight })
          updateCroppedPreview(img, width, height)
        }
        img.src = reader.result as string
      }
      reader.readAsDataURL(file)
    }
  }

  const applySuggestedSize = (w: number, h: number) => {
    setWidth(w)
    setHeight(h)
    if (originalImage) {
      updateCroppedPreview(originalImage, w, h)
    }
  }

  const handleSizeChange = (newW: number, newH: number) => {
    setWidth(newW)
    setHeight(newH)
    if (originalImage) {
      updateCroppedPreview(originalImage, newW, newH)
    }
  }

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(formRef.current!)

    if (!selectedFile) {
      alert('Please select an image')
      return
    }

    formData.set('mode', 'image')
    formData.set('image', selectedFile)
    formData.set('width', width.toString())
    formData.set('height', height.toString())

    onSubmit(formData)
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontWeight: 600,
    marginBottom: '0.25rem',
    color: '#000',
    fontSize: '0.95rem',
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.5rem',
    border: '1px solid #999',
    borderRadius: '4px',
    fontSize: '1rem',
    color: '#000',
    backgroundColor: '#fff',
    boxSizing: 'border-box',
  }

  const smallInputStyle: React.CSSProperties = {
    ...inputStyle,
    width: 'calc(50% - 0.25rem)',
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        marginTop: '2rem',
        padding: '2rem',
        border: '1px solid #ccc',
        borderRadius: '8px',
        backgroundColor: '#fff',
      }}
    >
      {/* Image Upload */}
      <>
          <div>
            <label htmlFor="image" style={labelStyle}>
              Upload Image:
            </label>
            <input
              ref={fileInputRef}
              id="image"
              type="file"
              name="image"
              accept="image/*"
              onChange={handleFileChange}
              style={{ ...inputStyle, cursor: 'pointer' }}
            />
            {selectedFile && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#666' }}>
                <div>
                  ✓ File: {selectedFile.name}
                  {isRetry && (
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#0070f3', fontWeight: 500 }}>
                      (cached from previous attempt)
                    </span>
                  )}
                </div>
                {croppedSize && (
                  <div style={{ fontWeight: 500, color: '#0070f3' }}>
                    Effective: {croppedSize.width}×{croppedSize.height} pixels (cropped to {width}×{height} grid)
                  </div>
                )}
                {isRetry && onClearImage && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFile(null)
                      setOriginalImage(null)
                      setIsRetry(false)
                      onClearImage()
                    }}
                    style={{
                      marginTop: '0.5rem',
                      padding: '0.3rem 0.6rem',
                      fontSize: '0.8rem',
                      backgroundColor: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      color: '#666',
                    }}
                  >
                    Upload new image
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Image Preview */}
          {originalImage && (
            <div
              style={{
                padding: '1rem',
                border: '1px solid #ddd',
                borderRadius: '4px',
                backgroundColor: '#f5f5f5',
              }}
            >
              <label style={labelStyle}>Preview (cropped to grid aspect ratio):</label>
              <canvas
                ref={canvasRef}
                style={{
                  maxWidth: '100%',
                  maxHeight: '150px',
                  borderRadius: '4px',
                  display: 'block',
                }}
              />
              <img
                id="image-preview"
                src={originalImage.src}
                alt="Preview"
                style={{
                  maxWidth: '100%',
                  maxHeight: '150px',
                  borderRadius: '4px',
                  objectFit: 'contain',
                }}
              />
            </div>
          )}
        </>
      }

      {/* Hidden size field for form compatibility */}
      <input
        type="hidden"
        name="size"
        value={Math.min(width, height)}
      />

      {/* Grid Size - always show if image is uploaded */}
      {selectedFile && (
        <div>
          <label style={labelStyle}>Output Grid Size:</label>
          {suggestedSizes.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: suggestedSizes.length === 1 ? '1fr' : 'repeat(3, 1fr)',
                gap: '0.4rem',
                marginBottom: '1rem',
              }}
            >
              {suggestedSizes.map((s) => (
                <button
                  key={`${s.width}x${s.height}`}
                  type="button"
                  onClick={() => applySuggestedSize(s.width, s.height)}
                  style={{
                    padding: '0.35rem 0.6rem',
                    border: width === s.width && height === s.height ? '2px solid #0070f3' : '1px solid #ccc',
                    borderRadius: '4px',
                    backgroundColor: width === s.width && height === s.height ? '#e3f2fd' : '#fff',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: width === s.width && height === s.height ? '600' : 'normal',
                    color: '#000',
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="width" style={{ ...labelStyle, fontSize: '0.85rem' }}>
                Width:
              </label>
              <input
                id="width"
                type="number"
                name="width"
                value={width}
                onChange={(e) => {
                  const newW = Math.max(5, Math.min(30, parseInt(e.target.value) || 0))
                  handleSizeChange(newW, height)
                }}
                min="5"
                max="30"
                style={inputStyle}
                placeholder="5-30"
              />
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="height" style={{ ...labelStyle, fontSize: '0.85rem' }}>
                Height:
              </label>
              <input
                id="height"
                type="number"
                name="height"
                value={height}
                onChange={(e) => {
                  const newH = Math.max(5, Math.min(30, parseInt(e.target.value) || 0))
                  handleSizeChange(width, newH)
                }}
                min="5"
                max="30"
                style={inputStyle}
                placeholder="5-30"
              />
            </div>
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#666' }}>
            Grid: {width} × {height} cells
            {croppedSize && ` (crop: ${croppedSize.width}×${croppedSize.height}px)`}
          </div>
        </div>
      )}

      {/* Puzzle Name */}
      <div>
        <label htmlFor="name" style={labelStyle}>
          Puzzle Name (optional):
        </label>
        <input
          id="name"
          type="text"
          name="name"
          value={customName}
          onChange={(e) => setCustomName(e.target.value)}
          style={inputStyle}
          placeholder="e.g., my_puzzle"
        />
        <div style={{ marginTop: '0.25rem', fontSize: '0.85rem', color: '#999' }}>
          Leave empty to use image filename
        </div>
      </div>

      {/* Output Directory */}
      <div>
        <label htmlFor="out" style={labelStyle}>
          Output Directory (optional):
        </label>
        <input
          id="out"
          type="text"
          name="out"
          style={inputStyle}
          placeholder="e.g., ./output or ~/Desktop/puzzles"
        />
        <div style={{ marginTop: '0.25rem', fontSize: '0.85rem', color: '#999' }}>
          Leave empty to use default directory
        </div>
      </div>

      {/* Common Fields */}
      <div>
        <label htmlFor="difficulty" style={labelStyle}>
          Difficulty:
        </label>
        <select id="difficulty" name="difficulty" defaultValue="any" style={inputStyle}>
          <option value="any">Any</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      <div>
        <label htmlFor="seed" style={labelStyle}>
          Seed (optional):
        </label>
        <input
          id="seed"
          type="number"
          name="seed"
          style={inputStyle}
          placeholder="Leave empty for random seed"
        />
      </div>

      <div>
        <label style={labelStyle}>Export Formats:</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
          {['json', 'csv', 'png', 'svg', 'pdf'].map((format) => (
            <label
              key={format}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer',
                color: '#000',
              }}
            >
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

      <button
        type="submit"
        disabled={loading || !selectedFile}
        style={{
          padding: '0.75rem 1.5rem',
          fontSize: '1rem',
          fontWeight: 600,
          backgroundColor: loading || !selectedFile ? '#ccc' : '#0070f3',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading || !selectedFile ? 'not-allowed' : 'pointer',
          marginTop: '0.5rem',
          transition: 'background-color 0.2s',
        }}
      >
        {loading ? 'Generating...' : 'Generate Puzzle'}
      </button>
    </form>
  )
}
