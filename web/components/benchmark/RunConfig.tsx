'use client'

import { useState } from 'react'
import { ModelSelector } from './ModelSelector'
import { TestSelector } from './TestSelector'
import { BenchmarkStartParams } from '@/lib/api'

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

  const canStart = selectedTests.length > 0 && !isRunning &&
    (selectedModels === null || selectedModels.length > 0)

  const handleStart = () => {
    if (!canStart) return
    const params: BenchmarkStartParams = {
      iterations,
      workers,
      privacy,
      tests: selectedTests.length === ALL_TESTS.length ? undefined : selectedTests,
      models: selectedModels ?? undefined,
    }
    onStart(params)
  }

  const estimatedCalls =
    (selectedModels?.length ?? 70) * selectedTests.length * iterations

  return (
    <div className="space-y-6">
      {/* Model selection */}
      <div className="p-4 bg-card rounded-lg border border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Models</h3>
        <ModelSelector onSelectionChange={setSelectedModels} />
      </div>

      {/* Test selection */}
      <div className="p-4 bg-card rounded-lg border border-border">
        <TestSelector selected={selectedTests} onChange={setSelectedTests} />
      </div>

      {/* Run parameters */}
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
              onChange={(e) => setIterations(Number(e.target.value))}
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
              onChange={(e) => setWorkers(Number(e.target.value))}
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
                  onChange={() => setPrivacy(p)}
                  className="accent-primary"
                />
                <span className="text-sm text-foreground capitalize">{p}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Start button */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Est. ~{estimatedCalls.toLocaleString()} API calls
        </p>
        <button
          onClick={handleStart}
          disabled={!canStart}
          className={`px-6 py-2.5 rounded-md text-sm font-semibold transition-colors ${
            canStart
              ? 'bg-primary text-primary-foreground hover:opacity-90'
              : 'bg-muted text-muted-foreground cursor-not-allowed'
          }`}
        >
          {isRunning ? 'Running…' : 'Start Benchmark'}
        </button>
      </div>
    </div>
  )
}
