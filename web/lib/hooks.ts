'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type GetCharactersParams, type TraitModelType } from '@/lib/api'
import { useEffect } from 'react'
import { toast } from 'sonner'

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

export function useEpochUsage() {
  return useQuery({
    queryKey: ['epochUsage'],
    queryFn: api.getEpochUsage,
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

export function useAPIKeyDetail(id: string | null) {
  return useQuery({
    queryKey: ['apiKeyDetail', id],
    queryFn: () => api.getAPIKeyDetail(id!),
    enabled: !!id,
    staleTime: 30000,
  })
}

export function useCreateAPIKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createAPIKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeysUsage'] })
      toast.success('API key created')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Failed to create API key'),
  })
}

export function useUpdateAPIKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.updateAPIKey,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeysUsage'] })
      queryClient.invalidateQueries({ queryKey: ['apiKeyDetail', variables.id] })
      toast.success('API key updated')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Failed to update API key'),
  })
}

export function useDeleteAPIKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteAPIKey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeysUsage'] })
      toast.success('API key deleted')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Failed to delete API key'),
  })
}

export function useCharacters(params: GetCharactersParams = {}) {
  return useQuery({
    queryKey: ['characters', params],
    queryFn: () => api.getCharacters(params),
    staleTime: 60_000,
  })
}

export function useCharacter(slug: string | null) {
  return useQuery({
    queryKey: ['character', slug],
    queryFn: () => api.getCharacter(slug!),
    enabled: !!slug,
    staleTime: 60_000,
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
    queryFn: () => api.get<Model>(`/api/models/${modelId}`),
    enabled: !!modelId,
  })
}

export function useModelTraits(modelType: TraitModelType = 'text') {
  return useQuery({
    queryKey: ['modelTraits', modelType],
    queryFn: () => api.getModelTraits(modelType),
    staleTime: 5 * 60 * 1000,
  })
}

export function usePriceHistory(token: 'vvv' | 'diem' = 'vvv', range: string = '7d') {
  return useQuery({
    queryKey: ['priceHistory', token, range],
    queryFn: () => api.getPriceHistory(token, range),
    refetchInterval: 60_000,
  })
}

export function useUsageTrends(scope: 'epoch' | 'daily' = 'epoch') {
  return useQuery({
    queryKey: ['usageTrends', scope],
    queryFn: () => api.getUsageTrends(scope),
    refetchInterval: 60_000,
  })
}

export function useOnchainSupply() {
  return useQuery({
    queryKey: ['onchainSupply'],
    queryFn: api.getOnchainSupply,
    refetchInterval: 60_000,
  })
}

export function useOnchainStaking() {
  return useQuery({
    queryKey: ['onchainStaking'],
    queryFn: api.getOnchainStaking,
    refetchInterval: 60_000,
  })
}

export function useOnchainBalance(address: string | null) {
  return useQuery({
    queryKey: ['onchainBalance', address],
    queryFn: () => api.getOnchainBalance(address!),
    enabled: !!address,
  })
}

export function useOnchainTransfers(address: string | null, blocks = 10000) {
  return useQuery({
    queryKey: ['onchainTransfers', address, blocks],
    queryFn: () => api.getOnchainTransfers(address!, blocks),
    enabled: !!address,
    staleTime: 60_000,
  })
}

export function useAlerts(enabledOnly = false) {
  return useQuery({
    queryKey: ['alerts', enabledOnly],
    queryFn: () => api.getAlerts(enabledOnly),
    refetchInterval: 30_000,
  })
}

export function useUnacknowledgedAlertEvents() {
  return useQuery({
    queryKey: ['alertEvents', 'unacknowledged'],
    queryFn: api.getUnacknowledgedAlertEvents,
    refetchInterval: 15_000,
  })
}

export function useAlertEvents(unacknowledgedOnly = false) {
  return useQuery({
    queryKey: ['alertEvents', unacknowledgedOnly],
    queryFn: () => api.getAlertEvents(unacknowledgedOnly),
    refetchInterval: 15_000,
  })
}

export function useAlertStream() {
  const queryClient = useQueryClient()
  useEffect(() => {
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') return
    let source: EventSource | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let stopped = false
    const connect = () => {
      if (stopped) return
      source = new EventSource('/api/alerts/stream')
      source.onmessage = (event) => {
        try {
          if (JSON.parse(event.data).type === 'event') queryClient.invalidateQueries({ queryKey: ['alertEvents'] })
        } catch { /* Ignore malformed stream events. */ }
      }
      source.onerror = () => { source?.close(); retry = setTimeout(connect, 5000) }
    }
    connect()
    return () => { stopped = true; source?.close(); if (retry) clearTimeout(retry) }
  }, [queryClient])
}

export function useNews() {
  return useQuery({ queryKey: ['news'], queryFn: () => api.getNews(), staleTime: 10 * 60_000, refetchInterval: 15 * 60_000 })
}

export function useNewsArticle(url: string | null) {
  return useQuery({ queryKey: ['newsArticle', url], queryFn: () => api.getNewsArticle(url!), enabled: !!url, staleTime: 60 * 60_000 })
}

export interface Model {
  id: string
  type?: string
  model_type?: string
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
    maxVideos?: number
    quantization?: string
    [key: string]: unknown
  }
  traits?: string[] | Record<string, unknown>
  deprecation?: {
    autoRemap?: boolean
    removesAt?: string
    replacementModelId?: string
    startsAt?: string
    date?: string
  } | null
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
    maxStyleReferences?: number
    [key: string]: unknown
  }
  supportsStyleReferences?: boolean
  supportsStyleReferenceStrength?: boolean
}
