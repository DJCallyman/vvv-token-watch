'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface ModelAnalytics {
  requests: number
  tokens: number
  prompt_tokens: number
  completion_tokens: number
  cost: number
  // BUG-05: separated costs (preferred over the mixed 'cost')
  cost_usd?: number
  cost_diem?: number
  avg_response_time_ms: number
  model_type: string
}

export interface ModelRecommendation {
  type: string
  message: string
  priority: string
}

export interface AnalyticsResponse {
  model_usage: Record<string, ModelAnalytics>
  total_requests: number
  total_tokens: number
  total_cost: number
  period_days: number
  recommendations: ModelRecommendation[]
  source?: string
}

export interface DailyUsage {
  date: string
  requests: number
  tokens: number
  cost: number
  // BUG-05: separated daily costs
  cost_usd?: number
  cost_diem?: number
}

export interface DailyAnalyticsResponse {
  daily_usage: DailyUsage[]
  period_days: number
  source?: string
}

export function useAnalytics(days: number = 7) {
  return useQuery({
    queryKey: ['analytics', days],
    queryFn: () => api.get<AnalyticsResponse>(`/api/analytics/models?days=${days}`),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDailyAnalytics(days: number = 7) {
  return useQuery({
    queryKey: ['dailyAnalytics', days],
    queryFn: () => api.get<DailyAnalyticsResponse>(`/api/analytics/daily?days=${days}`),
    staleTime: 5 * 60 * 1000,
  })
}