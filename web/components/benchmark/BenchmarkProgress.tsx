'use client'

import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'

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
  const seenLinesRef = useRef<Set<string>>(new Set())
  const finishedRef = useRef(false)

  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  }, [onComplete, onError])

  const pushLine = (text: string, type: LogLine['type']) => {
    const key = `${type}:${text}`
    if (seenLinesRef.current.has(key)) return
    seenLinesRef.current.add(key)
    setLines((prev) => [...prev, { text, type }])
  }

  const markDone = (runId: string | null | undefined) => {
    if (finishedRef.current) return
    finishedRef.current = true
    setStatus('done')
    pushLine(`Benchmark complete. Run ID: ${runId ?? 'unknown'}`, 'done')
    esRef.current?.close()
    if (runId) onCompleteRef.current(runId)
  }

  const markError = (message: string) => {
    if (finishedRef.current) return
    finishedRef.current = true
    setStatus('error')
    pushLine(message, 'error')
    esRef.current?.close()
    onErrorRef.current?.()
  }

  const ingestEvent = (data: {
    type?: string
    line?: string
    run_id?: string | null
    exit_code?: number
    message?: string
  }) => {
    if (data.type === 'log' && data.line) {
      pushLine(data.line, 'log')
    } else if (data.type === 'progress' && data.line) {
      pushLine(data.line, 'progress')
      const m = data.line.match(/##PROGRESS##\s+(\d+)\/(\d+)/)
      if (m) {
        setProgress({ done: parseInt(m[1], 10), total: parseInt(m[2], 10) })
      }
    } else if (data.type === 'done') {
      markDone(data.run_id)
    } else if (data.type === 'error') {
      markError(
        data.message ||
          (data.exit_code != null
            ? `Process exited with code ${data.exit_code}`
            : 'Benchmark failed'),
      )
    }
  }

  // Polling interval (only started on SSE error as fallback)
  const pollIntervalRef = useRef<number | null>(null)

  const startPolling = () => {
    if (pollIntervalRef.current != null) return
    const poll = async () => {
      if (finishedRef.current) return
      try {
        const st = await api.getBenchmarkStatus(jobId)
        if (finishedRef.current) return

        if (st.progress && st.progress.total > 0) {
          setProgress({ done: st.progress.done, total: st.progress.total })
        }

        for (const entry of st.logs ?? []) {
          if (entry.type === 'progress') {
            ingestEvent({ type: 'progress', line: entry.line })
          } else if (entry.type === 'error') {
            pushLine(entry.line, 'error')
          } else if (entry.type === 'done') {
            pushLine(entry.line, 'done')
          } else {
            pushLine(entry.line, 'log')
          }
        }

        if (st.status === 'done') {
          markDone(st.run_id)
        } else if (st.status === 'failed') {
          markError(st.error || 'Benchmark failed')
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'status poll failed'
        if (msg.includes('404') || msg.toLowerCase().includes('not found')) {
          pushLine('Job not found in backend memory (server may have reloaded). Check Results tab.', 'system')
        }
      }
    }

    // Kick once immediately, then interval
    poll()
    pollIntervalRef.current = window.setInterval(poll, 2000)
  }

  const stopPolling = () => {
    if (pollIntervalRef.current != null) {
      window.clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  useEffect(() => {
    finishedRef.current = false
    seenLinesRef.current = new Set()
    setLines([{ text: `Connected — streaming job ${jobId}`, type: 'system' }])
    setProgress(null)
    setStatus('running')

    // SSE must go through the Next.js proxy (/api/...) so the HttpOnly session cookie
    // is sent and the proxy can inject the real backend Authorization header.
    // Direct backend URLs (NEXT_PUBLIC_API_URL) are not supported for SSE because
    // cookies would not be forwarded cross-origin.
    const streamUrl = `/api/benchmark/stream/${encodeURIComponent(jobId)}`
    const es = new EventSource(streamUrl)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        ingestEvent(data)
      } catch {
        pushLine(event.data, 'log')
      }
      // If we had fallen back to polling, stop it — SSE is healthy again
      stopPolling()
    }

    es.onerror = () => {
      pushLine('SSE stream interrupted; falling back to status polling…', 'system')
      es.close()
      // Start polling ONLY on error (BUG-12)
      startPolling()
    }

    return () => {
      es.close()
      esRef.current = null
      stopPolling()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  const statusColor =
    status === 'done' ? 'text-green-400' : status === 'error' ? 'text-red-400' : 'text-amber-400'
  const statusLabel = status === 'done' ? 'Complete' : status === 'error' ? 'Error' : 'Running'

  const [cancelling, setCancelling] = useState(false)
  const onCancel = async () => {
    setCancelling(true)
    try {
      await api.cancelBenchmark(jobId)
      markError('Benchmark cancelled by user')
    } catch {
      pushLine('Failed to cancel benchmark', 'error')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="mt-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className={`text-xs font-medium ${statusColor}`}>
          {statusLabel}
          {status === 'running' && <span className="ml-1 animate-pulse">●</span>}
        </span>
        <div className="flex items-center gap-3">
          {progress && (
            <span className="text-xs text-muted-foreground tabular-nums">
              {progress.done} / {progress.total} models
            </span>
          )}
          {status === 'running' && (
            <button
              type="button"
              onClick={onCancel}
              disabled={cancelling}
              className="rounded-md border border-destructive px-2 py-0.5 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              {cancelling ? 'Cancelling…' : 'Cancel'}
            </button>
          )}
        </div>
      </div>
      {progress && (
        <div className="h-1.5 bg-muted/40 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${(progress.done / Math.max(progress.total, 1)) * 100}%` }}
          />
        </div>
      )}

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
            <div key={`${i}-${line.type}-${line.text.slice(0, 48)}`} className={cls}>
              {line.text}
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
