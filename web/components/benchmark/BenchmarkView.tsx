'use client'

import { useState, useEffect } from 'react'
import { useBenchmarkRuns, useBenchmarkRun } from '@/lib/hooks'
import { api, BenchmarkStartParams } from '@/lib/api'
import { ResultsSelector } from './ResultsSelector'
import { ResultsTable } from './ResultsTable'
import { CostOverlay } from './CostOverlay'
import { RunConfig } from './RunConfig'
import { BenchmarkProgress } from './BenchmarkProgress'
import { InfographicPanel } from './InfographicPanel'

type Tab = 'results' | 'run'

export function BenchmarkView() {
  const [activeTab, setActiveTab] = useState<Tab>('results')
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [showCostOverlay, setShowCostOverlay] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const { data: runsData, isLoading: runsLoading, refetch: refetchRuns } = useBenchmarkRuns()
  const { data: runDetail, isLoading: runLoading } = useBenchmarkRun(selectedRunId)

  // Auto-select latest run
  useEffect(() => {
    if (!selectedRunId && runsData?.runs?.length) {
      setSelectedRunId(runsData.runs[0].run_id)
    }
  }, [runsData, selectedRunId])

  const handleStart = async (params: BenchmarkStartParams) => {
    setStartError(null)
    try {
      const { job_id } = await api.startBenchmark(params)
      setActiveJobId(job_id)
    } catch (e) {
      setStartError(e instanceof Error ? e.message : 'Failed to start benchmark')
    }
  }

  const handleJobComplete = (runId: string) => {
    setActiveJobId(null)
    refetchRuns().then(() => {
      setSelectedRunId(runId)
      setActiveTab('results')
    })
  }

  const handleJobError = () => {
    setActiveJobId(null)
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'results', label: 'Results' },
    { id: 'run', label: 'Run Benchmark' },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Benchmark</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Compare Venice AI text models across 8 capability dimensions
        </p>
      </div>

      {/* Tab switcher */}
      <div className="border-b border-border">
        <div className="flex gap-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
                activeTab === tab.id
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {tab.label}
              {tab.id === 'run' && activeJobId && (
                <span className="ml-2 w-2 h-2 rounded-full bg-amber-400 animate-pulse inline-block" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Results tab */}
      {activeTab === 'results' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <ResultsSelector
              runs={runsData?.runs ?? []}
              selectedRunId={selectedRunId}
              onSelect={setSelectedRunId}
              isLoading={runsLoading}
            />
            {runDetail && (
              <button
                onClick={() => setShowCostOverlay((v) => !v)}
                className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
                  showCostOverlay
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-card text-muted-foreground border-border hover:text-foreground'
                }`}
              >
                {showCostOverlay ? 'Hide Value Analysis' : 'Value Analysis'}
              </button>
            )}
          </div>

          {runLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
              <span className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
              Loading results…
            </div>
          )}

          {!runLoading && !runDetail && selectedRunId && (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Could not load run data.
            </p>
          )}

          {runDetail && (
            <>
              {showCostOverlay && (
                <CostOverlay models={runDetail.models} />
              )}
              <ResultsTable runDetail={runDetail} />
              <InfographicPanel runId={runDetail.run_id} />
            </>
          )}

          {!runsLoading && !runsData?.runs?.length && (
            <div className="py-16 text-center text-muted-foreground">
              <p className="text-sm">No benchmark results yet.</p>
              <p className="text-xs mt-1">
                Switch to the{' '}
                <button
                  onClick={() => setActiveTab('run')}
                  className="text-primary hover:underline"
                >
                  Run Benchmark
                </button>{' '}
                tab to get started.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Run Benchmark tab */}
      {activeTab === 'run' && (
        <div className="space-y-4">
          {startError && (
            <div className="p-3 bg-red-900/20 border border-red-800 rounded-md text-sm text-red-400">
              {startError}
            </div>
          )}

          {!activeJobId && (
            <RunConfig onStart={handleStart} isRunning={false} />
          )}

          {activeJobId && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">Benchmark in progress</p>
                <button
                  onClick={() => setActiveJobId(null)}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Dismiss terminal
                </button>
              </div>
              <BenchmarkProgress
                jobId={activeJobId}
                onComplete={handleJobComplete}
                onError={handleJobError}
              />
            </>
          )}
        </div>
      )}
    </div>
  )
}
