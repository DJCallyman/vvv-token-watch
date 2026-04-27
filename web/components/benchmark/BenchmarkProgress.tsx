'use client'

import { useEffect, useRef, useState } from 'react'

interface LogLine {
  text: string
  type: 'log' | 'progress' | 'error' | 'done' | 'system'
}

interface Props {
  jobId: string
  onComplete: (runId: string) => void
  onError?: () => void
}

export function BenchmarkProgress({ jobId, onComplete, onError }: Props) {
  const [lines, setLines] = useState<LogLine[]>([])
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null)
  const [status, setStatus] = useState<'running' | 'done' | 'error'>('running')
  const bottomRef = useRef<HTMLDivElement>(null)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const es = new EventSource(`/api/benchmark/stream/${encodeURIComponent(jobId)}`)
    esRef.current = es

    setLines([{ text: `Connected — streaming job ${jobId}`, type: 'system' }])

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'log') {
          setLines((prev) => [...prev, { text: data.line, type: 'log' }])
        } else if (data.type === 'progress') {
          setLines((prev) => [...prev, { text: data.line, type: 'progress' }])
          // Parse ##PROGRESS## X/Y model_id
          const m = data.line.match(/##PROGRESS##\s+(\d+)\/(\d+)/)
          if (m) {
            setProgress({ done: parseInt(m[1], 10), total: parseInt(m[2], 10) })
          }
        } else if (data.type === 'done') {
          setStatus('done')
          setLines((prev) => [...prev, { text: `Benchmark complete. Run ID: ${data.run_id}`, type: 'done' }])
          es.close()
          onComplete(data.run_id)
        } else if (data.type === 'error') {
          setStatus('error')
          setLines((prev) => [...prev, { text: `Process exited with code ${data.exit_code}`, type: 'error' }])
          es.close()
          onError?.()
        }
      } catch {
        setLines((prev) => [...prev, { text: event.data, type: 'log' }])
      }
    }

    es.onerror = () => {
      if (status === 'running') {
        setLines((prev) => [...prev, { text: 'Stream disconnected.', type: 'error' }])
      }
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  const statusColor = status === 'done' ? 'text-green-400' : status === 'error' ? 'text-red-400' : 'text-amber-400'
  const statusLabel = status === 'done' ? 'Complete' : status === 'error' ? 'Error' : 'Running'

  return (
    <div className="mt-4 space-y-2">
      {/* Progress bar */}
      <div className="flex items-center justify-between">
        <span className={`text-xs font-medium ${statusColor}`}>
          {statusLabel}
          {status === 'running' && <span className="ml-1 animate-pulse">●</span>}
        </span>
        {progress && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {progress.done} / {progress.total} models
          </span>
        )}
      </div>
      {progress && (
        <div className="h-1.5 bg-muted/40 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${(progress.done / progress.total) * 100}%` }}
          />
        </div>
      )}

      {/* Terminal */}
      <div className="bg-black/80 rounded-lg border border-border font-mono text-xs h-64 overflow-y-auto p-3 space-y-0.5">
        {lines.map((line, i) => {
          const cls =
            line.type === 'progress'
              ? 'text-cyan-400'
              : line.type === 'done'
              ? 'text-green-400'
              : line.type === 'error'
              ? 'text-red-400'
              : line.type === 'system'
              ? 'text-muted-foreground'
              : 'text-gray-300'
          return (
            <div key={i} className={cls}>
              {line.text}
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
