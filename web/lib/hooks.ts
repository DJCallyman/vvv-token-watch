'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type GetCharactersParams, type TraitModelType } from '@/lib/api'
import { useEffect, useRef, useState } from 'react'
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
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['balance'],
    queryFn: api.getBalance,
    refetchInterval: refreshInterval,
  })
}

export function useSettings(enabled = true) {
  return useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

function useRefreshInterval() {
  const { data: settings } = useSettings()
  return (settings?.refresh_interval_seconds ?? 60) * 1000
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.updateSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      queryClient.invalidateQueries({ queryKey: ['prices'] })
      queryClient.invalidateQueries({ queryKey: ['benchmarkModels'] })
      queryClient.invalidateQueries({ queryKey: ['balance'] })
      toast.success('Settings saved')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Failed to save settings'),
  })
}

export function useResetSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.resetSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data)
      queryClient.invalidateQueries({ queryKey: ['prices'] })
      queryClient.invalidateQueries({ queryKey: ['benchmarkModels'] })
      queryClient.invalidateQueries({ queryKey: ['balance'] })
      toast.success('Settings reset to environment defaults')
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : 'Failed to reset settings'),
  })
}

export function useDailyUsage(date?: string) {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['dailyUsage', date],
    queryFn: () => api.getDailyUsage(date),
    refetchInterval: refreshInterval,
  })
}

export function useEpochUsage() {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['epochUsage'],
    queryFn: api.getEpochUsage,
    refetchInterval: refreshInterval,
  })
}

export function useAPIKeysUsage() {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['apiKeysUsage'],
    queryFn: api.getAPIKeysUsage,
    refetchInterval: refreshInterval,
  })
}

export function useAPIKeyAnalytics(days = 7) {
  return useQuery({
    queryKey: ['apiKeyAnalytics', days],
    queryFn: () => api.getAPIKeyAnalytics(days),
    staleTime: 5 * 60 * 1000,
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
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['prices'],
    queryFn: api.getPrices,
    refetchInterval: refreshInterval,
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

export function useModelCompatibilityMapping(
  modelType: TraitModelType | 'code' = 'text',
  enabled = true,
) {
  return useQuery({
    queryKey: ['modelCompatibilityMapping', modelType],
    queryFn: () => api.getModelCompatibilityMapping(modelType),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePriceHistory(token: 'vvv' | 'diem' = 'vvv', range: string = '7d') {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['priceHistory', token, range],
    queryFn: () => api.getPriceHistory(token, range),
    refetchInterval: refreshInterval,
  })
}

export function useUsageTrends(scope: 'epoch' | 'daily' = 'epoch') {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['usageTrends', scope],
    queryFn: () => api.getUsageTrends(scope),
    refetchInterval: refreshInterval,
  })
}

export function useOnchainSupply() {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['onchainSupply'],
    queryFn: api.getOnchainSupply,
    refetchInterval: refreshInterval,
  })
}

export function useOnchainStaking() {
  const refreshInterval = useRefreshInterval()
  return useQuery({
    queryKey: ['onchainStaking'],
    queryFn: api.getOnchainStaking,
    refetchInterval: refreshInterval,
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
  const { data: settings } = useSettings()
  const notificationsEnabled = settings?.in_app_notifications_enabled ?? true
  const notificationsEnabledRef = useRef(notificationsEnabled)
  useEffect(() => {
    notificationsEnabledRef.current = notificationsEnabled
  }, [notificationsEnabled])

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
          const payload = JSON.parse(event.data)
          if (payload.type === 'event') {
            queryClient.invalidateQueries({ queryKey: ['alertEvents'] })
            if (notificationsEnabledRef.current) {
              toast.info(payload.message || 'A new alert was triggered')
            }
          }
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

// ---------------------------------------------------------------------------
// Slice 2.4 — notification channels and deliveries
// ---------------------------------------------------------------------------

export function useNotificationChannels() {
  return useQuery({
    queryKey: ['notificationChannels'],
    queryFn: api.getNotificationChannels,
    staleTime: 60_000,
  })
}

export function useNotificationProviders() {
  return useQuery({
    queryKey: ['notificationProviders'],
    queryFn: api.getNotificationProviders,
    staleTime: 5 * 60_000,
  })
}

export function useVapidPublicKey() {
  return useQuery({
    queryKey: ['vapidPublicKey'],
    queryFn: api.getVapidPublicKey,
    staleTime: 5 * 60_000,
    retry: false,
  })
}

export function useCreateNotificationChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createNotificationChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationChannels'] })
      toast.success('Notification channel added')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Failed to add notification channel'),
  })
}

export function useDeleteNotificationChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.deleteNotificationChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationChannels'] })
      toast.success('Notification channel removed')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Failed to remove notification channel'),
  })
}

export function useTestNotificationChannel() {
  return useMutation({
    mutationFn: api.testNotificationChannel,
    onSuccess: (data) => {
      if (data.status === 'sent') toast.success('Test notification sent')
      else toast.error(data.error || 'Test notification failed')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Test notification failed'),
  })
}

export function useNotificationDeliveries(status?: string) {
  return useQuery({
    queryKey: ['notificationDeliveries', status],
    queryFn: () => api.getNotificationDeliveries(status),
    refetchInterval: 30_000,
  })
}

export function useRetryNotificationDelivery() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.retryNotificationDelivery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationDeliveries'] })
      toast.success('Delivery retry queued')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Failed to retry delivery'),
  })
}

// ---------------------------------------------------------------------------
// Slice 2.5 / 2.6 — chains, watchlists, staking events, holder lookup
// ---------------------------------------------------------------------------

export function useChains() {
  return useQuery({
    queryKey: ['chains'],
    queryFn: api.getChains,
    staleTime: 30 * 60_000,
  })
}

export function useWatchlist() {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: api.getWatchlist,
    staleTime: 60_000,
  })
}

export function useCreateWatchlistItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createWatchlistItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      toast.success('Added to watchlist')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Failed to add to watchlist'),
  })
}

export function useDeleteWatchlistItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.deleteWatchlistItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      toast.success('Removed from watchlist')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Failed to remove from watchlist'),
  })
}

export function useStakingEvents(blocks = 10000, address?: string | null) {
  return useQuery({
    queryKey: ['stakingEvents', blocks, address],
    queryFn: () => api.getStakingEvents(blocks, address ?? undefined),
    staleTime: 60_000,
  })
}

export function useHolderLookup(address: string | null) {
  return useQuery({
    queryKey: ['holderLookup', address],
    queryFn: () => api.getHolderLookup(address!),
    enabled: !!address,
    staleTime: 60_000,
  })
}

// ---------------------------------------------------------------------------
// Slice 2.7 — observability
// ---------------------------------------------------------------------------

export function useObservabilitySummary() {
  return useQuery({
    queryKey: ['observabilitySummary'],
    queryFn: api.getObservabilitySummary,
    refetchInterval: 120_000,
    retry: false,
  })
}

export function useRateLimits() {
  return useQuery({
    queryKey: ['rateLimits'],
    queryFn: api.getRateLimits,
    staleTime: 60_000,
    retry: false,
  })
}

export function useRpcCosts() {
  return useQuery({
    queryKey: ['rpcCosts'],
    queryFn: api.getRpcCosts,
    staleTime: 60_000,
    retry: false,
  })
}

// ---------------------------------------------------------------------------
// Slice 2.8 — wallet session
// ---------------------------------------------------------------------------

export function useWalletBalance(token: string | null) {
  return useQuery({
    queryKey: ['walletBalance', token],
    queryFn: () => api.getWalletBalance(token!),
    enabled: !!token,
    staleTime: 30_000,
    retry: false,
  })
}

export function useWalletTransactions(token: string | null, blocks = 10000) {
  return useQuery({
    queryKey: ['walletTransactions', token, blocks],
    queryFn: () => api.getWalletTransactions(token!, blocks),
    enabled: !!token,
    staleTime: 60_000,
    retry: false,
  })
}

// ---------------------------------------------------------------------------
// Phase 3 — signals, sentiment, media, documents, semantic news
// ---------------------------------------------------------------------------

export function useSignals(limit = 50) {
  return useQuery({
    queryKey: ['signals', limit],
    queryFn: () => api.getSignals(limit),
    refetchInterval: 60_000,
  })
}

export function useEvaluateSignal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, currentPriceUsd }: { id: number; currentPriceUsd?: number }) =>
      api.evaluateSignal(id, currentPriceUsd),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      toast.success('Signal outcome evaluated')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Failed to evaluate signal'),
  })
}

export function useAnalyzeXSentiment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (query?: string) => api.analyzeXSentiment(query),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      toast.success('X sentiment analyzed')
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'X sentiment analysis failed'),
  })
}

export function useNewsSearch() {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      api.searchNews(query, topK),
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Semantic search failed'),
  })
}

export function useAskNews() {
  return useMutation({
    mutationFn: ({ question, topK }: { question: string; topK?: number }) =>
      api.askNews(question, topK),
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'News Q&A failed'),
  })
}

export function useParseDocument() {
  return useMutation({
    mutationFn: api.parseDocument,
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Document parsing failed'),
  })
}

export function useBriefing() {
  return useMutation({
    mutationFn: (text?: string) => api.generateBriefing(text),
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Briefing generation failed'),
  })
}

export function useAlertVoice() {
  const [playing, setPlaying] = useState<number | null>(null)
  const mutation = useMutation({
    mutationFn: api.generateAlertVoice,
    onSuccess: (data) => {
      if (typeof window === 'undefined') return
      const audio = new Audio(`data:${data.mime};base64,${data.audio_b64}`)
      void audio.play().catch(() => {
        toast.error('Could not play alert audio')
      })
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Alert voice generation failed'),
  })
  return { ...mutation, playing, setPlaying }
}

export function useMarketInfographic() {
  return useMutation({
    mutationFn: api.generateMarketInfographic,
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Infographic generation failed'),
  })
}

export function useVideoRecapStatus(queueId: string | null, model?: string) {
  return useQuery({
    queryKey: ['videoRecap', queueId, model],
    queryFn: () => api.getVideoRecap(queueId!, model),
    enabled: !!queueId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'completed' || status === 'error' ? false : 10_000
    },
  })
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
