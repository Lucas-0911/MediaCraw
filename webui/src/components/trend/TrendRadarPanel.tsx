import { useMemo, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Activity, Radar, Save, ShoppingBag, Download, Send } from 'lucide-react'
import {
  trendApi,
  type TrendAlert,
  type TrendListing,
  type TrendProduct,
  type TrendSettings,
  type TrendSnapshot,
  type TrendVideo,
} from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const LABELS = ['QUAN SAT', 'DANG HOT', 'DU KIEN NONG'] as const
const GATE_KEYS = ['mention_spread', 'play_increase', 'intent', 'search_cn', 'identity'] as const

function num(settings: TrendSettings, key: string, fallback = '') {
  const value = settings[key]
  return value === undefined || value === null ? fallback : String(value)
}

function formatTs(ts?: number | null) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

function ageLabel(createTime?: number) {
  if (!createTime) return '-'
  const hours = (Date.now() / 1000 - createTime) / 3600
  if (hours < 48) return `${hours.toFixed(1)}h`
  return `${(hours / 24).toFixed(1)}d`
}

function parseAlertPayload(raw?: string) {
  try {
    return JSON.parse(raw || '{}') as { sent?: boolean; text?: string }
  } catch {
    return {}
  }
}

function SettingGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-2 pt-2 first:pt-0">
      <div className="text-[10px] font-mono uppercase tracking-wider text-cyber-neon-cyan">{title}</div>
      {children}
    </div>
  )
}

function GateBadge({
  ok,
  label,
  extra,
  okText,
  noText,
}: {
  ok: boolean
  label: string
  extra?: string
  okText: string
  noText: string
}) {
  return (
    <Badge variant={ok ? 'success' : 'destructive'} className="text-[10px]">
      {label}: {ok ? okText : noText}
      {extra ? ` ${extra}` : ''}
    </Badge>
  )
}

export function TrendRadarPanel() {
  const { t } = useTranslation('trend')
  const queryClient = useQueryClient()
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [draft, setDraft] = useState<TrendSettings>({})
  const [search, setSearch] = useState('')
  const [labelFilter, setLabelFilter] = useState('all')
  const [minConf, setMinConf] = useState(0)

  const productsQuery = useQuery({
    queryKey: ['trendProducts', minConf],
    queryFn: async () => {
      const { data } = await trendApi.getProducts(minConf)
      return data.products
    },
    refetchInterval: 15000,
  })

  const settingsQuery = useQuery({
    queryKey: ['trendSettings'],
    queryFn: async () => {
      const { data } = await trendApi.getSettings()
      setDraft(data.settings)
      return data.settings
    },
  })

  const schedulerQuery = useQuery({
    queryKey: ['trendScheduler'],
    queryFn: async () => {
      const { data } = await trendApi.getScheduler()
      return data
    },
    refetchInterval: 10000,
  })

  const alertsQuery = useQuery({
    queryKey: ['trendAlerts'],
    queryFn: async () => {
      const { data } = await trendApi.getAlerts()
      return data.alerts || []
    },
    refetchInterval: 15000,
  })

  const detailQuery = useQuery({
    queryKey: ['trendProduct', selectedKey],
    enabled: Boolean(selectedKey),
    queryFn: async () => {
      const { data } = await trendApi.getProduct(selectedKey as string)
      return data
    },
  })

  const scanMutation = useMutation({
    mutationFn: () => trendApi.scan(),
    onSuccess: () => {
      toast.success(t('toastScan'))
      queryClient.invalidateQueries({ queryKey: ['trendProducts'] })
      queryClient.invalidateQueries({ queryKey: ['trendScheduler'] })
      queryClient.invalidateQueries({ queryKey: ['trendAlerts'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const saveMutation = useMutation({
    mutationFn: () => trendApi.saveSettings(draft),
    onSuccess: () => {
      toast.success(t('toastSave'))
      queryClient.invalidateQueries({ queryKey: ['trendSettings'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const schedulerMutation = useMutation({
    mutationFn: async (enable: boolean) => (enable ? trendApi.startScheduler() : trendApi.stopScheduler()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trendScheduler'] }),
  })

  const marketplaceMutation = useMutation({
    mutationFn: (key: string) => trendApi.marketplace(key),
    onSuccess: () => {
      toast.success(t('toastMarket'))
      queryClient.invalidateQueries({ queryKey: ['trendProduct', selectedKey] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const mediaMutation = useMutation({
    mutationFn: (key: string) => trendApi.media(key),
    onSuccess: () => {
      toast.success(t('toastMedia'))
      queryClient.invalidateQueries({ queryKey: ['trendProduct', selectedKey] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const telegramMutation = useMutation({
    mutationFn: () => trendApi.testTelegram(),
    onSuccess: ({ data }) => {
      if (data.ok) toast.success(t('toastTelegramOk'))
      else toast.error(t('toastTelegramFail'))
    },
    onError: () => toast.error(t('toastTelegramFail')),
  })

  const products = productsQuery.data || []
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return products.filter((item) => {
      if (labelFilter !== 'all' && item.label !== labelFilter) return false
      if (q && !(item.name || '').toLowerCase().includes(q)) return false
      return true
    })
  }, [products, search, labelFilter])

  const selected = useMemo(
    () => products.find((item) => item.product_key === selectedKey) || null,
    [products, selectedKey]
  )

  const setField = (key: string, value: string | boolean | number) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
  }

  const lastRun = schedulerQuery.data?.last_run
  const lastResult = schedulerQuery.data?.last_result
  const snapshots = (detailQuery.data?.snapshots || []) as TrendSnapshot[]
  const t1 = snapshots[0]
  const t0 = snapshots[1]
  const gates = (detailQuery.data?.product?.gates || {}) as Record<string, unknown>
  const alerts = (alertsQuery.data || []) as TrendAlert[]

  const textField = (key: string, label: string, secret = false) => (
    <div className="space-y-1">
      <Label className="text-[10px] text-cyber-text-muted font-mono">{t(label)}</Label>
      <Input
        type={secret ? 'password' : 'text'}
        value={num(draft, key)}
        onChange={(e) => setField(key, e.target.value)}
        className="h-8 text-xs"
      />
    </div>
  )

  const checkField = (key: string, label: string) => (
    <div className="flex items-center gap-2 text-[11px] font-mono">
      <Checkbox checked={Boolean(draft[key])} onCheckedChange={(checked) => setField(key, Boolean(checked))} />
      {t(label)}
    </div>
  )

  return (
    <div className="space-y-4">
      <section className="rounded-lg glass-panel overflow-hidden">
        <header className="px-4 py-3 border-b border-cyber-border-subtle/50 flex flex-wrap items-center justify-between gap-3 bg-cyber-bg-tertiary/30">
          <div className="flex items-center gap-3">
            <Radar className="h-4 w-4 text-cyber-neon-cyan" />
            <div>
              <div className="text-xs font-mono font-semibold">{t('title')}</div>
              <div className="text-[10px] text-cyber-text-muted">{t('subtitle')}</div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono text-cyber-text-muted">
            <span>
              {t('lastScan')}: {lastRun ? formatTs(lastRun) : t('never')}
            </span>
            {lastResult ? (
              <span>
                {t('resultProducts')} {lastResult.products ?? 0} · {t('resultAlerts')} {lastResult.alerts ?? 0} ·{' '}
                {t('resultMedia')} {lastResult.media ?? 0} · {t('resultListings')} {lastResult.listings ?? 0}
              </span>
            ) : null}
            <Badge variant={schedulerQuery.data?.enabled ? 'success' : 'secondary'}>
              {schedulerQuery.data?.enabled ? t('schedulerOn') : t('schedulerOff')}
            </Badge>
            <Button size="sm" variant="outline" onClick={() => schedulerMutation.mutate(!schedulerQuery.data?.enabled)}>
              {schedulerQuery.data?.enabled ? t('schedulerOff') : t('schedulerOn')}
            </Button>
            <Button size="sm" onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              <Activity className="h-3.5 w-3.5" />
              {scanMutation.isPending ? t('scanning') : t('scanNow')}
            </Button>
          </div>
        </header>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section className="xl:col-span-2 space-y-4">
          <div className="rounded-lg glass-panel overflow-hidden">
            <div className="px-4 py-3 border-b border-cyber-border-subtle/50 grid grid-cols-1 md:grid-cols-3 gap-2">
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('search')}
                className="h-8 text-xs"
              />
              <Select value={labelFilter} onValueChange={setLabelFilter}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder={t('allLabels')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('allLabels')}</SelectItem>
                  {LABELS.map((label) => (
                    <SelectItem key={label} value={label}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2">
                <Label className="text-[10px] text-cyber-text-muted font-mono whitespace-nowrap">{t('minConf')}</Label>
                <Input
                  type="number"
                  min={0}
                  max={5}
                  value={minConf}
                  onChange={(e) => setMinConf(Math.max(0, Math.min(5, parseInt(e.target.value) || 0)))}
                  className="h-8 text-xs"
                />
              </div>
            </div>
            <div className="overflow-auto">
              {filtered.length === 0 ? (
                <p className="p-6 text-xs text-cyber-text-muted font-mono">{t('empty')}</p>
              ) : (
                <table className="w-full text-xs font-mono">
                  <thead className="text-cyber-text-muted border-b border-cyber-border-subtle">
                    <tr>
                      <th className="text-left p-3">{t('columns.name')}</th>
                      <th className="text-left p-3">{t('columns.label')}</th>
                      <th className="text-left p-3">{t('columns.confidence')}</th>
                      <th className="text-left p-3">{t('columns.heat')}</th>
                      <th className="text-left p-3">{t('columns.delta')}</th>
                      <th className="text-left p-3">{t('columns.identity')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((item: TrendProduct) => (
                      <tr
                        key={item.product_key}
                        className={`border-b border-cyber-border-subtle/40 cursor-pointer hover:bg-cyber-bg-tertiary/40 ${selectedKey === item.product_key ? 'bg-cyber-neon-cyan/10' : ''}`}
                        onClick={() => setSelectedKey(item.product_key)}
                      >
                        <td className="p-3">{item.name}</td>
                        <td className="p-3">
                          <Badge
                            variant={item.label === 'DANG HOT' ? 'success' : item.label === 'DU KIEN NONG' ? 'warning' : 'secondary'}
                          >
                            {item.label}
                          </Badge>
                        </td>
                        <td className="p-3">{item.confidence}/5</td>
                        <td className="p-3">{Number(item.heat_now || 0).toFixed(2)}</td>
                        <td className="p-3">{Number(item.heat_delta || 0).toFixed(2)}</td>
                        <td className="p-3">{item.identity_type || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {selected && detailQuery.data ? (
            <div className="rounded-lg glass-panel p-4 space-y-4 text-xs font-mono">
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => marketplaceMutation.mutate(selected.product_key)}>
                  <ShoppingBag className="h-3.5 w-3.5" />
                  {t('source')}
                </Button>
                <Button size="sm" variant="outline" onClick={() => mediaMutation.mutate(selected.product_key)}>
                  <Download className="h-3.5 w-3.5" />
                  {t('download')}
                </Button>
              </div>

              <div>
                <div className="text-cyber-text-muted mb-2">{t('detail.gates')}</div>
                <div className="flex flex-wrap gap-1.5">
                  {GATE_KEYS.map((key) => (
                    <GateBadge
                      key={key}
                      ok={Boolean(gates[key])}
                      label={t(`gate.${key}`)}
                      extra={key === 'search_cn' ? String(gates.search_cn_value || '') : undefined}
                      okText={t('ok')}
                      noText={t('no')}
                    />
                  ))}
                </div>
              </div>

              <div>
                <div className="text-cyber-text-muted mb-2">{t('detail.snapshots')}</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {[
                    { tag: t('t0'), snap: t0 },
                    { tag: t('t1'), snap: t1 },
                  ].map(({ tag, snap }) => (
                    <div key={tag} className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3 space-y-1">
                      <div className="text-cyber-neon-cyan">{tag}</div>
                      {snap ? (
                        <>
                          <div>{formatTs(snap.ts)}</div>
                          <div>HeatNow {Number(snap.heat_now || 0).toFixed(2)}</div>
                          <div>play_vel {Number(snap.play_velocity || 0).toFixed(2)}</div>
                          <div>
                            mention {snap.mention_n ?? 0} · spread {snap.spread ?? 0}
                          </div>
                          <div>
                            intent {snap.intent_n ?? 0} · wilson {Number(snap.intent_wilson || 0).toFixed(2)}
                          </div>
                          <div>trends_CN {snap.search_cn || 'unknown'}</div>
                        </>
                      ) : (
                        <div className="text-cyber-text-muted">{t('never')}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-cyber-text-muted mb-2">{t('detail.videos')}</div>
                <div className="space-y-2">
                  {(detailQuery.data.videos || []).slice(0, 8).map((video: TrendVideo) => (
                    <div key={video.aweme_id} className="rounded-md border border-cyber-border-subtle/60 p-2 space-y-1">
                      <a href={video.url} target="_blank" rel="noreferrer" className="block text-cyber-neon-cyan truncate">
                        {t('play')} {video.play_count || 0} · {t('like')} {video.like_count || 0} · {t('age')} {ageLabel(video.create_time)}
                      </a>
                      {video.url ? <div className="truncate text-cyber-text-muted">{video.url}</div> : null}
                      {video.local_media_path ? (
                        <div className="truncate text-cyber-text-secondary">
                          {t('detail.mp4')}: {video.local_media_path}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-cyber-text-muted mb-2">{t('detail.listings')}</div>
                <div className="space-y-2">
                  {(detailQuery.data.listings || []).slice(0, 8).map((listing: TrendListing) => (
                    <div key={listing.id} className="rounded-md border border-cyber-border-subtle/60 p-2 space-y-1">
                      <a href={listing.url} target="_blank" rel="noreferrer" className="block truncate text-cyber-neon-cyan">
                        {listing.marketplace} {listing.price || ''} · {listing.title || listing.url}
                      </a>
                      {listing.draft_path ? (
                        <div className="truncate text-cyber-text-secondary">
                          {t('detail.draft')}: {listing.draft_path}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          <div className="rounded-lg glass-panel overflow-hidden">
            <header className="px-4 py-3 border-b border-cyber-border-subtle/50 bg-cyber-bg-tertiary/30">
              <div className="text-xs font-mono font-semibold">{t('detail.alerts')}</div>
            </header>
            <div className="p-4 space-y-2 max-h-72 overflow-auto">
              {alerts.length === 0 ? (
                <p className="text-[11px] text-cyber-text-muted font-mono">{t('never')}</p>
              ) : (
                alerts.map((alert) => {
                  const payload = parseAlertPayload(alert.payload_json)
                  return (
                    <div key={alert.id} className="rounded-md border border-cyber-border-subtle/60 p-2 text-[11px] font-mono space-y-1">
                      <div className="flex justify-between gap-2">
                        <span>{alert.product_key}</span>
                        <Badge variant={payload.sent ? 'success' : 'destructive'}>
                          {payload.sent ? t('sent') : t('notSent')}
                        </Badge>
                      </div>
                      <div className="text-cyber-text-muted">
                        {formatTs(alert.ts)} · conf {alert.confidence}/5
                      </div>
                      {payload.text ? (
                        <pre className="whitespace-pre-wrap text-[10px] text-cyber-text-secondary max-h-24 overflow-auto">
                          {payload.text}
                        </pre>
                      ) : null}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </section>

        <section className="rounded-lg glass-panel overflow-hidden">
          <header className="px-4 py-3 border-b border-cyber-border-subtle/50 bg-cyber-bg-tertiary/30">
            <div className="text-xs font-mono font-semibold">{t('settings.title')}</div>
          </header>
          <div className="p-4 space-y-4 max-h-[1400px] overflow-auto">
            <SettingGroup title={t('settings.scanGroup')}>
              {textField('TREND_SCAN_INTERVAL_HOURS', 'settings.interval')}
              {textField('TREND_SCAN_CRON', 'settings.cron')}
              {textField('TREND_SNAPSHOT_GAP_HOURS', 'settings.gap')}
              {textField('TREND_ALERT_COOLDOWN_HOURS', 'settings.cooldown')}
              {checkField('TREND_SCHEDULER_ENABLED', 'settings.scheduler')}
            </SettingGroup>
            <SettingGroup title={t('settings.videoGroup')}>
              {textField('TREND_VIDEOS_PER_ALERT', 'settings.videos')}
              {textField('TREND_VIDEO_MIN_AGE_HOURS', 'settings.minAge')}
              {textField('TREND_VIDEO_MAX_AGE_DAYS', 'settings.maxAge')}
              {textField('TREND_MAX_MEDIA_PER_SCAN', 'settings.maxMedia')}
              {checkField('TREND_REQUIRE_PLAY_INCREASE', 'settings.playIncrease')}
              {checkField('TREND_DOWNLOAD_MEDIA', 'settings.media')}
            </SettingGroup>
            <SettingGroup title={t('settings.thresholdGroup')}>
              {textField('TREND_MIN_CONFIDENCE', 'settings.confidence')}
              {textField('TREND_MIN_MENTION', 'settings.mention')}
              {textField('TREND_MIN_SPREAD', 'settings.spread')}
              {textField('TREND_MIN_INTENT_N', 'settings.intentN')}
              {textField('TREND_MIN_INTENT_WILSON', 'settings.intentW')}
              {textField('TREND_MIN_NAME_VIDEOS', 'settings.nameVideos')}
              {textField('TREND_HOT_HEATNOW', 'settings.hot')}
              {textField('TREND_RISING_HEATNOW_MIN', 'settings.risingMin')}
              {textField('TREND_RISING_DELTA_RATIO', 'settings.risingDelta')}
            </SettingGroup>
            <SettingGroup title={t('settings.telegramGroup')}>
              {textField('TREND_TELEGRAM_BOT_TOKEN', 'settings.telegramToken', true)}
              {textField('TREND_TELEGRAM_CHAT_ID', 'settings.telegramChat')}
              <Button
                size="sm"
                variant="outline"
                onClick={() => telegramMutation.mutate()}
                disabled={telegramMutation.isPending}
              >
                <Send className="h-3.5 w-3.5" />
                {t('telegramTest')}
              </Button>
            </SettingGroup>
            <SettingGroup title={t('settings.llmGroup')}>
              {checkField('TREND_LLM_ENABLED', 'settings.llm')}
              {textField('TREND_LLM_BASE_URL', 'settings.llmUrl')}
              {textField('TREND_LLM_MODEL', 'settings.llmModel')}
              {textField('TREND_LLM_API_KEY', 'settings.llmKey', true)}
            </SettingGroup>
            <SettingGroup title={t('settings.marketGroup')}>
              {checkField('TREND_MARKETPLACE_ENABLED', 'settings.marketplace')}
              {checkField('TREND_SHOPEE_ENABLED', 'settings.shopee')}
              {checkField('TREND_LAZADA_ENABLED', 'settings.lazada')}
              {checkField('TREND_GOOGLE_TRENDS_ENABLED', 'settings.google')}
              {textField('TREND_PLATFORMS', 'settings.platforms')}
              {textField('TREND_KEYWORDS', 'settings.keywords')}
            </SettingGroup>
            <div className="flex gap-2 pt-2">
              <Button size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || !settingsQuery.data}>
                <Save className="h-3.5 w-3.5" />
                {t('save')}
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
