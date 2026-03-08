export interface ColumnDefinition {
  key: string
  header: string
  minWidth: number
  sortable: boolean
  tooltip?: string
}

export type ModelType = 'text' | 'image' | 'video' | 'tts' | 'asr' | 'embedding' | 'upscale' | 'inpaint' | 'all'

export const TEXT_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'context', header: 'Context', minWidth: 100, sortable: true, tooltip: 'Context window in tokens' },
  { key: 'quantization', header: 'Quant', minWidth: 70, sortable: true },
  { key: 'date_added', header: 'Added', minWidth: 90, sortable: true },
  { key: 'vision', header: 'Vision', minWidth: 70, sortable: true },
  { key: 'functions', header: 'Functions', minWidth: 85, sortable: true },
  { key: 'web_search', header: 'Web Search', minWidth: 90, sortable: true },
  { key: 'reasoning', header: 'Reasoning', minWidth: 85, sortable: true },
  { key: 'logprobs', header: 'LogProbs', minWidth: 80, sortable: true },
  { key: 'response_schema', header: 'JSON', minWidth: 55, sortable: true, tooltip: 'JSON response schema' },
  { key: 'optimized_for_code', header: 'Code Opt', minWidth: 70, sortable: true },
  { key: 'audio_input', header: 'Audio In', minWidth: 75, sortable: true },
  { key: 'video_input', header: 'Video In', minWidth: 75, sortable: true },
  { key: 'input_price', header: 'Input $/1M', minWidth: 110, sortable: true },
  { key: 'output_price', header: 'Output $/1M', minWidth: 120, sortable: true },
  { key: 'cache_input', header: 'Cache Read $/1M', minWidth: 110, sortable: true },
  { key: 'cache_write', header: 'Cache Write $/1M', minWidth: 110, sortable: true },
  { key: 'privacy', header: 'Privacy', minWidth: 90, sortable: true },
]

export const IMAGE_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'resolutions', header: 'Resolutions', minWidth: 150, sortable: true },
  { key: 'steps', header: 'Steps', minWidth: 80, sortable: true },
  { key: 'prompt_limit', header: 'Prompt Limit', minWidth: 110, sortable: true },
  { key: 'generation_price', header: 'Price/Image', minWidth: 110, sortable: true },
  { key: 'privacy', header: 'Privacy', minWidth: 90, sortable: true },
]

export const VIDEO_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'video_type', header: 'Video Type', minWidth: 110, sortable: true, tooltip: 'text-to-video or image-to-video' },
  { key: 'durations', header: 'Durations', minWidth: 110, sortable: true },
  { key: 'resolutions', header: 'Resolutions', minWidth: 150, sortable: true },
  { key: 'aspect_ratios', header: 'Aspect Ratios', minWidth: 120, sortable: true },
  { key: 'audio', header: 'Audio', minWidth: 70, sortable: true },
  { key: 'audio_configurable', header: 'Audio Config', minWidth: 110, sortable: true },
  { key: 'base_price', header: 'Base Price', minWidth: 100, sortable: true },
  { key: 'audio_price', header: 'Audio Price', minWidth: 100, sortable: true },
  { key: 'privacy', header: 'Privacy', minWidth: 90, sortable: true },
]

export const TTS_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'voices', header: 'Voices', minWidth: 110, sortable: true },
  { key: 'input_price', header: 'Price/1M Chars', minWidth: 130, sortable: true },
]

export const ASR_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'input_price', header: 'Price/Min', minWidth: 110, sortable: true },
]

export const EMBEDDING_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'dimensions', header: 'Dimensions', minWidth: 110, sortable: true },
  { key: 'input_price', header: 'Input $/1M', minWidth: 110, sortable: true },
]

export const UPSCALE_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'upscale_factors', header: 'Factors', minWidth: 90, sortable: true },
  { key: 'upscale_price', header: 'Price/Upscale', minWidth: 120, sortable: true },
]

export const INPAINT_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'resolutions', header: 'Resolutions', minWidth: 150, sortable: true },
  { key: 'steps', header: 'Steps', minWidth: 80, sortable: true },
  { key: 'inpaint_price', header: 'Price/Inpaint', minWidth: 120, sortable: true },
]

export const DEFAULT_COLUMNS: ColumnDefinition[] = [
  { key: 'model', header: 'Model', minWidth: 160, sortable: true },
  { key: 'type', header: 'Type', minWidth: 80, sortable: true },
  { key: 'specs', header: 'Specs', minWidth: 150, sortable: true },
  { key: 'price', header: 'Price', minWidth: 110, sortable: true },
]

const COLUMN_CONFIGS: Record<ModelType, ColumnDefinition[]> = {
  text: TEXT_COLUMNS,
  image: IMAGE_COLUMNS,
  video: VIDEO_COLUMNS,
  tts: TTS_COLUMNS,
  asr: ASR_COLUMNS,
  embedding: EMBEDDING_COLUMNS,
  upscale: UPSCALE_COLUMNS,
  inpaint: INPAINT_COLUMNS,
  all: DEFAULT_COLUMNS,
}

export function getColumnsForType(modelType: ModelType): ColumnDefinition[] {
  return COLUMN_CONFIGS[modelType] || DEFAULT_COLUMNS
}

export function getDefaultVisibleColumns(modelType: ModelType): string[] {
  const columns = getColumnsForType(modelType)
  return columns.map(c => c.key)
}

const STORAGE_KEY = 'vvv-model-column-preferences'

export function loadColumnPreferences(modelType: ModelType): Set<string> {
  if (typeof window === 'undefined') return new Set()
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      const hidden = data[modelType] || []
      return new Set(hidden)
    }
  } catch {
    return new Set()
  }
  return new Set()
}

export function saveColumnPreferences(modelType: ModelType, hiddenColumns: Set<string>): void {
  if (typeof window === 'undefined') return
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    const data = stored ? JSON.parse(stored) : {}
    data[modelType] = Array.from(hiddenColumns)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    return
  }
}

export type SortDirection = 'asc' | 'desc'

export interface SortConfig {
  key: string
  direction: SortDirection
}