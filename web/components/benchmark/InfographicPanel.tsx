'use client'

import { useState } from 'react'
import { api } from '@/lib/api'

interface Props {
  runId: string
}

export function InfographicPanel({ runId }: Props) {
  const [imageB64, setImageB64] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generate = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.generateInfographic(runId)
      setImageB64(result.image_b64)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate infographic')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mt-6 p-4 bg-card rounded-lg border border-border">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">AI Infographic</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Generate a 4K visual summary via Venice AI image generation
          </p>
        </div>
        <div className="flex items-center gap-2">
          {imageB64 && (
            <a
              href={`data:image/png;base64,${imageB64}`}
              download={`benchmark_infographic_${runId}.png`}
              className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground transition-colors"
            >
              Download
            </a>
          )}
          <button
            onClick={generate}
            disabled={isLoading}
            className={`text-xs px-4 py-1.5 rounded-md font-medium transition-colors ${
              isLoading
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-primary text-primary-foreground hover:opacity-90'
            }`}
          >
            {isLoading ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin inline-block" />
                Generating…
              </span>
            ) : imageB64 ? (
              'Regenerate'
            ) : (
              'Generate Infographic'
            )}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-400 mt-2">{error}</p>
      )}

      {imageB64 && (
        <div className="mt-3 rounded-md overflow-hidden border border-border">
          <img
            src={`data:image/png;base64,${imageB64}`}
            alt="Benchmark infographic"
            className="w-full h-auto"
          />
        </div>
      )}
    </div>
  )
}
