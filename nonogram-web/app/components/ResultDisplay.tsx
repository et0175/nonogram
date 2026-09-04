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
  if (!result.success) {
    return null
  }

  const { name, seed, files } = result.data!

  return (
    <div
      style={{
        marginTop: '2rem',
        padding: '2rem',
        border: '1px solid #4caf50',
        borderRadius: '8px',
        backgroundColor: '#f1f8f4',
      }}
    >
      <h2>✓ Puzzle Generated!</h2>
      <p>
        <strong>Name:</strong> {name}
      </p>
      <p>
        <strong>Seed:</strong> {seed}
      </p>

      <h3>Files:</h3>
      <ul>
        {Object.entries(files).map(([format, path]) => (
          <li key={format}>
            <strong>{format.toUpperCase()}:</strong> {path}
          </li>
        ))}
      </ul>

      <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '1rem' }}>
        Files are available at <code>/api/files/[filename]</code>
      </p>
    </div>
  )
}
