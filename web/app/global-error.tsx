'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-center text-foreground">
        <h2 className="mb-2 text-3xl font-bold">Application error</h2>
        <p className="mb-6 text-muted-foreground">
          {error.message || 'A critical error occurred. Please try again.'}
        </p>
        <button
          onClick={reset}
          className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
        >
          Reload
        </button>
      </body>
    </html>
  )
}
