import { FormEvent, useRef, useState } from 'react'

interface GeneratorFormProps {
  onSubmit: (formData: FormData) => void
  loading: boolean
}

export default function GeneratorForm({ onSubmit, loading }: GeneratorFormProps) {
  const formRef = useRef<HTMLFormElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [originalImage, setOriginalImage] = useState<HTMLImageElement | null>(null)
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null)
  const [croppedSize, setCroppedSize] = useState<{ width: number; height: number } | null>(null)
  const [suggestedSizes, setSuggestedSizes] = useState<Array<{ label: string; width: number; height: number }>>([])
  const [size, setSize] = useState<number>(20)
  const [customName, setCustomName] = useState<string>('')

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
    const minSize = Math.min(boundingBox.width, boundingBox.height)
    const maxSize = 30 // Maximum grid size
    const suggestions: Array<{ label: string; width: number; height: number }> = []

    // Algorithm-based suggestions: scale to optimal grid size
    // Aim for 2-4 readable sizes between 10 and 30

    if (minSize >= 10) {
      // Small: ~1/4 of content, min 10
      const smallSize = Math.max(10, Math.min(maxSize, Math.round(minSize / 4)))
      suggestions.push({ label: `Small (${smallSize}×${smallSize})`, width: smallSize, height: smallSize })
    }

    if (minSize >= 15) {
      // Medium: ~1/2.5 of content
      const mediumSize = Math.max(10, Math.min(maxSize, Math.round(minSize / 2.5)))
      if (mediumSize !== suggestions[suggestions.length - 1]?.width) {
        suggestions.push({ label: `Medium (${mediumSize}×${mediumSize})`, width: mediumSize, height: mediumSize })
      }
    }

    if (minSize >= 20) {
      // Large: ~1/1.5 of content
      const largeSize = Math.max(10, Math.min(maxSize, Math.round(minSize / 1.5)))
      if (largeSize !== suggestions[suggestions.length - 1]?.width) {
        suggestions.push({ label: `Large (${largeSize}×${largeSize})`, width: largeSize, height: largeSize })
      }
    }

    if (minSize >= 25) {
      // Extra Large: ~content size, capped at max
      const xlSize = Math.min(maxSize, Math.round(minSize * 0.8))
      if (xlSize !== suggestions[suggestions.length - 1]?.width && xlSize >= 10) {
        suggestions.push({ label: `Extra Large (${xlSize}×${xlSize})`, width: xlSize, height: xlSize })
      }
    }

    // Fallback if no suggestions generated
    if (suggestions.length === 0) {
      suggestions.push(
        { label: 'Small (10×10)', width: 10, height: 10 },
        { label: 'Medium (15×15)', width: 15, height: 15 },
        { label: 'Large (20×20)', width: 20, height: 20 },
        { label: 'Extra Large (30×30)', width: 30, height: 30 }
      )
    }

    setSuggestedSizes(suggestions)
    if (suggestions.length > 0) {
      setSize(suggestions[0].width)
    }
  }

  const updateCroppedPreview = (img: HTMLImageElement, gridSize: number) => {
    const boundingBox = detectInkBoundingBox(img)
    const cropBox = calculateCropBox(boundingBox, gridSize, gridSize)
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
          updateCroppedPreview(img, size)
        }
        img.src = reader.result as string
      }
      reader.readAsDataURL(file)
    }
  }

  const applySuggestedSize = (s: number) => {
    setSize(s)
    if (originalImage) {
      updateCroppedPreview(originalImage, s)
    }
  }

  const handleSizeChange = (newSize: number) => {
    setSize(newSize)
    if (originalImage) {
      updateCroppedPreview(originalImage, newSize)
    }
  }

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(formRef.current!)

    if (!selectedFile) {
      alert('Please select an image')
      return
    }

    formData.set('image', selectedFile)
    formData.set('mode', 'image')
    formData.set('size', size.toString())

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
          required
        />
        {selectedFile && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#666' }}>
            <div>✓ File: {selectedFile.name}</div>
            {croppedSize && (
              <div style={{ fontWeight: 500, color: '#0070f3' }}>
                Effective: {croppedSize.width}×{croppedSize.height} pixels (cropped to {width}×{height} grid)
              </div>
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
              maxHeight: '300px',
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
              maxHeight: '300px',
              borderRadius: '4px',
              objectFit: 'contain',
            }}
          />
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

      {/* Grid Size */}
      {suggestedSizes.length > 0 && (
        <div>
          <label style={labelStyle}>Output Grid Size:</label>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: suggestedSizes.length === 1 ? '1fr' : 'repeat(2, 1fr)',
              gap: '0.5rem',
              marginBottom: '1rem',
            }}
          >
            {suggestedSizes.map((s) => (
              <button
                key={`${s.width}x${s.height}`}
                type="button"
                onClick={() => applySuggestedSize(s.width)}
                style={{
                  padding: '0.5rem',
                  border: size === s.width ? '2px solid #0070f3' : '1px solid #ccc',
                  borderRadius: '4px',
                  backgroundColor: size === s.width ? '#e3f2fd' : '#fff',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: size === s.width ? '600' : 'normal',
                  color: '#000',
                }}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div>
            <label htmlFor="size" style={{ ...labelStyle, fontSize: '0.85rem' }}>
              Size:
            </label>
            <input
              id="size"
              type="number"
              name="size"
              value={size}
              onChange={(e) => {
                const newSize = Math.max(5, Math.min(30, parseInt(e.target.value) || 0))
                handleSizeChange(newSize)
              }}
              min="5"
              max="30"
              style={inputStyle}
              placeholder="5-30"
            />
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#666' }}>
            Grid: {size} × {size} cells
            {croppedSize && ` (crop: ${croppedSize.width}×${croppedSize.height}px)`}
          </div>
        </div>
      )}

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
                defaultChecked={format !== 'pdf'}
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
