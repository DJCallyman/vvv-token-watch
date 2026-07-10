import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value)
}

export function formatNumber(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getUsagePercentile(value: number, max: number): number {
  if (max === 0) return 0
  return (value / max) * 100
}

export function getUsageBarColor(percentile: number): string {
  if (percentile >= 75) return 'bg-destructive'
  if (percentile >= 50) return 'bg-warning'
  if (percentile >= 25) return 'bg-success/70'
  return 'bg-success'
}

export function getPriorityStyles(priority: 'high' | 'medium' | 'low'): string {
  const styles = {
    high: 'bg-destructive/10 text-destructive border-destructive/20',
    medium: 'bg-warning/10 text-warning border-warning/20',
    low: 'bg-success/10 text-success border-success/20',
  }
  return styles[priority]
}

export function getTypeColor(type: string): string {
  const typeMap: Record<string, string> = {
    text: 'bg-chart-1/10 text-chart-1 border-chart-1/20',
    image: 'bg-chart-5/10 text-chart-5 border-chart-5/20',
    audio: 'bg-chart-3/10 text-chart-3 border-chart-3/20',
    video: 'bg-chart-2/10 text-chart-2 border-chart-2/20',
  }
  return typeMap[type?.toLowerCase()] || 'bg-muted text-muted-foreground border-muted'
}