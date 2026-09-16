import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface CrawlerConfig {
  platform: string
  login_type: string
  crawler_type: string
  keywords: string
  specified_ids?: string
  creator_ids?: string
  start_page: number
  enable_comments: boolean
  enable_sub_comments: boolean
  save_option: string
  cookies: string
  headless: boolean
  max_notes_count?: number
  max_comments_count?: number
}

export interface CrawlerStatus {
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform: string | null
  crawler_type: string | null
  started_at: string | null
  error_message: string | null
}

export interface LogEntry {
  id: number
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success' | 'debug'
  message: string
}

export interface DataFile {
  name: string
  path: string
  size: number
  modified_at: number
  record_count: number | null
  type: string
}

export interface FilePreviewResponse {
  data: Record<string, unknown>[]
  total: number
  columns?: string[]
}

export interface Platform {
  value: string
  label: string
  icon: string
}

export interface ConfigOption {
  value: string
  label: string
}

// API functions
export const crawlerApi = {
  start: (config: CrawlerConfig) => api.post('/crawler/start', config),
  stop: () => api.post('/crawler/stop'),
  getStatus: () => api.get<CrawlerStatus>('/crawler/status'),
  getLogs: (limit = 100) => api.get<{ logs: LogEntry[] }>('/crawler/logs', { params: { limit } }),
}

export const dataApi = {
  getFiles: (platform?: string, fileType?: string) =>
    api.get<{ files: DataFile[] }>('/data/files', { params: { platform, file_type: fileType } }),
  getFileContent: (path: string, limit = 100) =>
    api.get<FilePreviewResponse>('/data/files/' + path, { params: { preview: true, limit } }),
  getStats: () => api.get('/data/stats'),
  getDownloadUrl: (path: string) => `/api/data/download/${path}`,
}

export const configApi = {
  getPlatforms: () => api.get<{ platforms: Platform[] }>('/config/platforms'),
  getOptions: () =>
    api.get<{
      login_types: ConfigOption[]
      crawler_types: ConfigOption[]
      save_options: ConfigOption[]
    }>('/config/options'),
}

export interface EnvCheckResult {
  success: boolean
  message: string
  output?: string
  error?: string
}

export const envApi = {
  check: () => api.get<EnvCheckResult>('/env/check'),
}

export interface TrendProduct {
  product_key: string
  product_id?: string
  name: string
  identity_type?: string
  industry?: string
  confidence: number
  heat_now: number
  heat_delta: number
  label: string
  gates?: Record<string, unknown>
}

export interface TrendSettings {
  [key: string]: unknown
}

export interface TrendSnapshot {
  ts: number
  heat_now?: number
  play_velocity?: number
  eng_velocity?: number
  mention_n?: number
  spread?: number
  intent_n?: number
  intent_wilson?: number
  search_cn?: string
}

export interface TrendVideo {
  aweme_id: string
  platform?: string
  play_count?: number
  like_count?: number
  create_time?: number
  url?: string
  local_media_path?: string
}

export interface TrendListing {
  id: number
  marketplace: string
  title?: string
  price?: string
  url: string
  draft_path?: string
}

export interface TrendAlert {
  id: number
  product_key?: string
  ts?: number
  confidence?: number
  payload_json?: string
}

export interface TrendProductDetail {
  product?: TrendProduct & { gates?: Record<string, unknown> }
  videos?: TrendVideo[]
  snapshots?: TrendSnapshot[]
  listings?: TrendListing[]
}

export interface TrendSchedulerStatus {
  enabled?: boolean
  running?: boolean
  last_run?: number | null
  last_result?: { products?: number; alerts?: number; media?: number; listings?: number } | null
  interval_hours?: number
  cron?: string
}

export const trendApi = {
  getProducts: (minConfidence = 0) =>
    api.get<{ products: TrendProduct[] }>('/trend/products', { params: { min_confidence: minConfidence } }),
  getProduct: (key: string) =>
    api.get<TrendProductDetail>(`/trend/products/${encodeURIComponent(key)}`),
  getSettings: () => api.get<{ settings: TrendSettings }>('/trend/settings'),
  saveSettings: (settings: TrendSettings) => api.put('/trend/settings', { settings }),
  scan: () => api.post('/trend/scan'),
  getScheduler: () => api.get<TrendSchedulerStatus>('/trend/scheduler'),
  startScheduler: () => api.post('/trend/scheduler/start'),
  stopScheduler: () => api.post('/trend/scheduler/stop'),
  marketplace: (key: string) => api.post(`/trend/products/${encodeURIComponent(key)}/marketplace`),
  media: (key: string) => api.post(`/trend/products/${encodeURIComponent(key)}/media`),
  getAlerts: () => api.get<{ alerts: TrendAlert[] }>('/trend/alerts'),
  testTelegram: () => api.post<{ ok: boolean }>('/trend/telegram/test'),
}

export default api
