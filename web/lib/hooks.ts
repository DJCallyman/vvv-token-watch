'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

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