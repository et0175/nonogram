import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Nonogram Generator",
  description: "Generate uniquely-solvable nonogram puzzles",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
