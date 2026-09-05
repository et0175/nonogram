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
  if (!result.success) {
    return null
  }

  const { name, seed, files } = result.data!

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
                  <span className={styles.fileName}>{path}</span>
                  <span className={styles.fileFormat}>{format.toUpperCase()}</span>
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
