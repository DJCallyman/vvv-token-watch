'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

// ---------------------------------------------------------------------------
// Benchmark hooks
// ---------------------------------------------------------------------------

export function useBenchmarkRuns() {
  return useQuery({
    queryKey: ['benchmarkRuns'],
    queryFn: api.getBenchmarkRuns,
    refetchInterval: 10000,
  })
}

export function useBenchmarkRun(runId: string | null) {
  return useQuery({
    queryKey: ['benchmarkRun', runId],
    queryFn: () => api.getBenchmarkRun(runId!),
    enabled: !!runId,
    staleTime: 60000, // Results files don't change
  })
}

export function useBenchmarkModels() {
  return useQuery({
    queryKey: ['benchmarkModels'],
    queryFn: api.getBenchmarkModels,
    staleTime: 120000,
  })
}

export function useBenchmarkStatus(jobId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['benchmarkStatus', jobId],
    queryFn: () => api.getBenchmarkStatus(jobId!),
    enabled: enabled && !!jobId,
    refetchInterval: 3000,
  })
}

export function useBalance() {
  return useQuery({
    queryKey: ['balance'],
    queryFn: api.getBalance,
    refetchInterval: 30000,
  })
}

export function useDailyUsage(date?: string) {
  return useQuery({
    queryKey: ['dailyUsage', date],
    queryFn: () => api.getDailyUsage(date),
    refetchInterval: 30000,
  })
}

export function useAPIKeysUsage() {
  return useQuery({
    queryKey: ['apiKeysUsage'],
    queryFn: api.getAPIKeysUsage,
    refetchInterval: 60000,
  })
}

export function usePrices() {
  return useQuery({
    queryKey: ['prices'],
    queryFn: api.getPrices,
    refetchInterval: 60000,
  })
}

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: api.getModels,
    staleTime: 5 * 60 * 1000,
  })
}

export function useModel(modelId: string) {
  return useQuery({
    queryKey: ['model', modelId],
    queryFn: () => fetchAPI<Model>(`/api/models/${modelId}`),
    enabled: !!modelId,
  })
}

export interface Model {
  id: string
  type: string
  object?: string
  created?: number
  owned_by?: string
  spec?: ModelSpec
  model_spec?: ModelSpec
  [key: string]: unknown
}

export interface ModelSpec {
  context_length?: number
  max_output_tokens?: number
  availableContextTokens?: number
  maxCompletionTokens?: number
  dimensions?: number
  embeddingDimensions?: number
  voices?: string[]
  supportedVoices?: string[]
  privacy?: string
  description?: string
  name?: string
  pricing?: {
    input?: string | { usd?: number; diem?: number }
    output?: string | { usd?: number; diem?: number }
    generation?: { usd?: number }
    perImage?: { usd?: number }
    cache_input?: { usd?: number; diem?: number }
    cache_write?: { usd?: number; diem?: number }
    upscale?: { usd?: number }
    inpaint?: { usd?: number }
    resolutions?: Record<string, { usd?: number }>
  }
  capabilities?: {
    supportsVision?: boolean
    supportsFunctionCalling?: boolean
    supportsWebSearch?: boolean
    supportsReasoning?: boolean
    supportsLogProbs?: boolean
    supportsResponseSchema?: boolean
    optimizedForCode?: boolean
    supportsAudioInput?: boolean
    supportsVideoInput?: boolean
    supportsMultipleImages?: boolean
    supportsReasoningEffort?: boolean
    supportsTeeAttestation?: boolean
    quantization?: string
    [key: string]: unknown
  }
  traits?: string[] | Record<string, unknown>
  constraints?: {
    steps?: { max?: number; default?: number }
    promptCharacterLimit?: number
    resolutions?: string[]
    durations?: number[]
    aspect_ratios?: string[]
    audio?: boolean
    audio_configurable?: boolean
    model_type?: string
    upscale_factors?: string[]
    factors?: string[]
    [key: string]: unknown
  }
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}