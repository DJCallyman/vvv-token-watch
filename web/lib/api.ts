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
}

export interface DailyUsage {
  date: string
  diem: number
  usd: number
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
  type: string
  [key: string]: unknown
}

export interface ModelsResponse {
  models: ModelData[]
  count: number
  types: string[]
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
    return fetchAPI('/api/health')
  },
}