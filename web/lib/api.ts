const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
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

export interface BalanceData {
  diem: number
  usd: number
  daily_diem_limit: number
  daily_usd_limit: number
  next_epoch_begins: string | null
  diem_usage_percent: number
  usd_usage_percent: number
  consumption_currency?: string
  can_consume?: boolean
  diem_epoch_allocation?: number | null
}

export interface DailyUsage {
  date: string
  diem: number
  usd: number
  epoch_start?: string
}

export interface APIKeyUsage {
  id: string
  name: string
  diem_usage: number
  usd_usage: number
  created_at: string
  is_active: boolean
}

export interface UsageKeysResponse {
  keys: APIKeyUsage[]
}

export interface PricesData {
  vvv: Record<string, number>
  diem: Record<string, number>
  holdings: {
    vvv: number
    diem: number
  }
  portfolio?: {
    vvv_value_usd: number
    diem_value_usd: number
    total_usd: number
  }
}

export interface ModelData {
  id: string
  name?: string
  type?: string
  model_type?: string
  object?: string
  created?: number
  owned_by?: string
  model_spec?: Record<string, unknown>
  spec?: Record<string, unknown>
  input_price_usd?: number | null
  output_price_usd?: number | null
  generation_price_usd?: number | null
  cache_input_price_usd?: number | null
  cache_input_price_diem?: number | null
  cache_write_price_usd?: number | null
  cache_write_price_diem?: number | null
  supports_cache?: boolean
  capabilities?: string[] | Record<string, unknown>
  is_beta?: boolean
  context_window?: number | null
  deprecation?: {
    autoRemap?: boolean
    removesAt?: string
    replacementModelId?: string
    startsAt?: string
    date?: string
  } | null
  [key: string]: unknown
}

export interface ModelsResponse {
  models: ModelData[]
  count: number
  types: string[]
}

// ---------------------------------------------------------------------------
// Benchmark types
// ---------------------------------------------------------------------------

export interface BenchmarkRunSummary {
  run_id: string
  filename: string
  generated_at: string
  model_count: number
  timestamp: string
}

export interface BenchmarkRunsResponse {
  runs: BenchmarkRunSummary[]
}

export interface BenchmarkCapabilities {
  supportsFunctionCalling: boolean
  supportsReasoning: boolean
  supportsReasoningEffort: boolean
  supportsResponseSchema: boolean
  supportsVision: boolean
}

export interface BenchmarkModelMeta {
  id: string
  privacy: string
  context_length: number
  max_completion_tokens: number
  capabilities: BenchmarkCapabilities
  pricing_input_usd: number | null
  pricing_output_usd: number | null
  description: string
}

export interface BenchmarkCategory {
  runs_total: number
  runs_success: number
  runs_error: number
  runs_skip: number
  skipped: boolean
  score_mean: number | null
  score_stdev: number | null
  score_effective: number | null
  latency_mean_ms: number | null
  latency_median_ms: number | null
  latency_p90_ms: number | null
  ttft_mean_ms: number | null
  tokens_per_sec_mean: number | null
  tokens_completion_mean: number | null
  tokens_prompt_mean: number | null
}

export interface BenchmarkModelResult {
  model_id: string
  model_meta: BenchmarkModelMeta
  categories: Record<string, BenchmarkCategory>
  composite_score: number | null
  data_coverage: number | null
}

export interface BenchmarkRunDetail {
  run_id: string
  generated_at: string
  model_count: number
  models: BenchmarkModelResult[]
}

export interface BenchmarkModel {
  id: string
  display_name: string
  privacy: string
  capabilities: BenchmarkCapabilities
  pricing_input_usd: number | null
  pricing_output_usd: number | null
  deprecation?: {
    autoRemap?: boolean
    removesAt?: string
    replacementModelId?: string
    startsAt?: string
    date?: string
  } | null
}

export interface BenchmarkModelsResponse {
  models: BenchmarkModel[]
  count: number
}

export interface BenchmarkStartParams {
  models?: string[]
  tests?: string[]
  iterations: number
  workers: number
  privacy: 'both' | 'private' | 'anonymized'
}

export interface BenchmarkJobStatus {
  status: 'running' | 'done' | 'failed'
  run_id: string | null
  error: string | null
}

export const api = {
  async getBalance(): Promise<BalanceData> {
    return fetchAPI<BalanceData>('/api/balance')
  },

  async getDailyUsage(date?: string): Promise<DailyUsage> {
    const params = date ? `?target_date=${date}` : ''
    return fetchAPI<DailyUsage>(`/api/usage/daily${params}`)
  },

  async getAPIKeysUsage(): Promise<UsageKeysResponse> {
    return fetchAPI<UsageKeysResponse>('/api/usage/keys')
  },

  async getPrices(): Promise<PricesData> {
    return fetchAPI<PricesData>('/api/prices')
  },

  async getModels(): Promise<ModelsResponse> {
    return fetchAPI<ModelsResponse>('/api/models')
  },

  async getHealth(): Promise<{ status: string; timestamp: string }> {
    return fetchAPI<{ status: string; timestamp: string }>('/api/health')
  },

  async get<T>(endpoint: string): Promise<T> {
    return fetchAPI<T>(endpoint)
  },

  // Benchmark endpoints
  async getBenchmarkRuns(): Promise<BenchmarkRunsResponse> {
    return fetchAPI<BenchmarkRunsResponse>('/api/benchmark/runs')
  },

  async getBenchmarkRun(runId: string): Promise<BenchmarkRunDetail> {
    return fetchAPI<BenchmarkRunDetail>(`/api/benchmark/runs/${encodeURIComponent(runId)}`)
  },

  async getBenchmarkModels(): Promise<BenchmarkModelsResponse> {
    return fetchAPI<BenchmarkModelsResponse>('/api/benchmark/models')
  },

  async startBenchmark(params: BenchmarkStartParams): Promise<{ job_id: string }> {
    return fetchAPI<{ job_id: string }>('/api/benchmark/start', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  async getBenchmarkStatus(jobId: string): Promise<BenchmarkJobStatus> {
    return fetchAPI<BenchmarkJobStatus>(`/api/benchmark/status/${encodeURIComponent(jobId)}`)
  },

  async generateInfographic(runId: string): Promise<{ image_b64: string; prompt: string }> {
    return fetchAPI<{ image_b64: string; prompt: string }>(
      `/api/benchmark/infographic/${encodeURIComponent(runId)}`,
      { method: 'POST' },
    )
  },
}