'use client'

import { useState } from 'react'
import { ModelSelector } from './ModelSelector'
import { TestSelector } from './TestSelector'
import { api, BenchmarkEstimateResponse, BenchmarkStartParams } from '@/lib/api'

interface Props {
  onStart: (params: BenchmarkStartParams) => void
  isRunning: boolean
}

const ALL_TESTS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8']

export function RunConfig({ onStart, isRunning }: Props) {
  const [selectedModels, setSelectedModels] = useState<string[] | null>(null) // null = all
  const [selectedTests, setSelectedTests] = useState<string[]>(ALL_TESTS)
  const [iterations, setIterations] = useState(10)
  const [workers, setWorkers] = useState(4)
  const [privacy, setPrivacy] = useState<'both' | 'private' | 'anonymized'>('both')

  const [estimate, setEstimate] = useState<BenchmarkEstimateResponse | null>(null)
  const [pendingParams, setPendingParams] = useState<BenchmarkStartParams | null>(null)
  const [estimating, setEstimating] = useState(false)
  const [estimateError, setEstimateError] = useState<string | null>(null)

  const canEstimate =
    selectedTests.length > 0 &&
    !isRunning &&
    !estimating &&
    (selectedModels === null || selectedModels.length > 0)

  const buildParams = (): BenchmarkStartParams => ({
    iterations,
    workers,
    privacy,
    tests: selectedTests.length === ALL_TESTS.length ? undefined : selectedTests,
    models: selectedModels ?? undefined,
  })

  const invalidateEstimate = () => {
    if (estimate || pendingParams) {
      setEstimate(null)
      setPendingParams(null)
    }
  }

  const handleEstimate = async () => {
    if (!canEstimate) return
    setEstimateError(null)
    setEstimate(null)
    setPendingParams(null)
    setEstimating(true)
    const params = buildParams()
    try {
      const result = await api.estimateBenchmark(params)
      setEstimate(result)
      setPendingParams(params)
    } catch (e) {
      setEstimateError(e instanceof Error ? e.message : 'Failed to estimate cost')
    } finally {
      setEstimating(false)
    }
  }

  const handleConfirm = () => {
    if (!pendingParams || isRunning) return
    onStart(pendingParams)
  }

  const handleCancelEstimate = () => {
    setEstimate(null)
    setPendingParams(null)
    setEstimateError(null)
  }

  return (
    <div className="space-y-6">
      <div className="p-4 bg-card rounded-lg border border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Models</h3>
        <ModelSelector
          onSelectionChange={(models) => {
            setSelectedModels(models)
            invalidateEstimate()
          }}
        />
      </div>

      <div className="p-4 bg-card rounded-lg border border-border">
        <TestSelector
          selected={selectedTests}
          onChange={(tests) => {
            setSelectedTests(tests)
            invalidateEstimate()
          }}
        />
      </div>

      <div className="p-4 bg-card rounded-lg border border-border space-y-4">
        <h3 className="text-sm font-semibold text-foreground">Parameters</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Iterations per test: <span className="text-foreground font-semibold">{iterations}</span>
            </label>
            <input
              type="range"
              min={1}
              max={20}
              value={iterations}
              onChange={(e) => {
                setIterations(Number(e.target.value))
                invalidateEstimate()
              }}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-0.5">
              <span>1</span><span>20</span>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
              Parallel workers: <span className="text-foreground font-semibold">{workers}</span>
            </label>
            <input
              type="range"
              min={1}
              max={8}
              value={workers}
              onChange={(e) => {
                setWorkers(Number(e.target.value))
                invalidateEstimate()
              }}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-0.5">
              <span>1</span><span>8</span>
            </div>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1.5">
            Privacy filter
          </label>
          <div className="flex gap-3">
            {(['both', 'private', 'anonymized'] as const).map((p) => (
              <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="privacy"
                  value={p}
                  checked={privacy === p}
                  onChange={() => {
                    setPrivacy(p)
                    invalidateEstimate()
                  }}
                  className="accent-primary"
                />
                <span className="text-sm text-foreground capitalize">{p}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {estimateError && (
        <div className="p-3 bg-red-900/20 border border-red-800 rounded-md text-sm text-red-400">
          {estimateError}
        </div>
      )}

      {estimate && (
        <div className="p-4 bg-card rounded-lg border border-amber-700/50 space-y-3">
          <h3 className="text-sm font-semibold text-foreground">
            Cost estimate — confirm before running
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Models</p>
              <p className="font-semibold text-foreground">{estimate.model_count}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Tests</p>
              <p className="font-semibold text-foreground">{estimate.tests.join(', ')}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Iterations</p>
              <p className="font-semibold text-foreground">{estimate.iterations}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Est. API calls</p>
              <p className="font-semibold text-foreground">
                ~{estimate.estimated_calls.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Est. cost</p>
              <p className="font-semibold text-amber-400">
                ~${estimate.estimated_usd.toFixed(4)} USD
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Workers</p>
              <p className="font-semibold text-foreground">{estimate.workers}</p>
            </div>
          </div>
          {estimate.skipped_tests_note && (
            <p className="text-xs text-muted-foreground">{estimate.skipped_tests_note}</p>
          )}
          <p className="text-xs text-muted-foreground">{estimate.note}</p>
          {estimate.note?.toLowerCase().includes('always reasons') && (
            <p className="text-xs text-amber-400">
              Reasoning models may bill significantly more than visible output suggests.
            </p>
          )}
          {estimate.model_ids.length > 0 && estimate.model_ids.length <= 12 && (
            <p className="text-xs text-muted-foreground font-mono break-all">
              {estimate.model_ids.join(', ')}
            </p>
          )}
          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              onClick={handleCancelEstimate}
              disabled={isRunning}
              className="px-4 py-2 rounded-md text-sm border border-border text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isRunning || !pendingParams}
              className="px-6 py-2.5 rounded-md text-sm font-semibold bg-primary text-primary-foreground hover:opacity-90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed"
            >
              {isRunning ? 'Running…' : 'Confirm & Start'}
            </button>
          </div>
        </div>
      )}

      {!estimate && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Review estimated cost before the run starts.
          </p>
          <button
            onClick={handleEstimate}
            disabled={!canEstimate}
            className={`px-6 py-2.5 rounded-md text-sm font-semibold transition-colors ${
              canEstimate
                ? 'bg-primary text-primary-foreground hover:opacity-90'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            }`}
          >
            {estimating ? 'Estimating…' : isRunning ? 'Running…' : 'Estimate Cost'}
          </button>
        </div>
      )}
    </div>
  )
}
