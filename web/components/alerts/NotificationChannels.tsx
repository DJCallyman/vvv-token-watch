'use client'

import { useId, useState } from 'react'
import {
  useCreateNotificationChannel,
  useDeleteNotificationChannel,
  useNotificationChannels,
  useNotificationDeliveries,
  useNotificationProviders,
  useRetryNotificationDelivery,
  useTestNotificationChannel,
  useVapidPublicKey,
} from '@/lib/hooks'
import type { NotificationChannelCreate, NotificationChannelKind } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { BellRing, Send, Trash2, Webhook } from 'lucide-react'

const KIND_OPTIONS: Array<{ value: NotificationChannelKind; label: string }> = [
  { value: 'discord', label: 'Discord webhook' },
  { value: 'slack', label: 'Slack webhook' },
  { value: 'telegram', label: 'Telegram bot' },
  { value: 'webhook', label: 'Generic HTTPS webhook' },
  { value: 'email', label: 'Email (SMTP)' },
  { value: 'browser_push', label: 'Browser push' },
]

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const output = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i += 1) output[i] = rawData.charCodeAt(i)
  return output
}

export function NotificationChannels() {
  const formId = useId()
  const { data, isLoading, isError } = useNotificationChannels()
  const { data: providersData } = useNotificationProviders()
  const { data: vapid } = useVapidPublicKey()
  const { data: deliveriesData } = useNotificationDeliveries()
  const createChannel = useCreateNotificationChannel()
  const deleteChannel = useDeleteNotificationChannel()
  const testChannel = useTestNotificationChannel()
  const retryDelivery = useRetryNotificationDelivery()

  const [kind, setKind] = useState<NotificationChannelKind>('discord')
  const [name, setName] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')
  const [telegramToken, setTelegramToken] = useState('')
  const [telegramChatId, setTelegramChatId] = useState('')
  const [emailTo, setEmailTo] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [subscribing, setSubscribing] = useState(false)

  const availability = new Map(
    (providersData?.providers ?? []).map((provider) => [provider.kind, provider.available]),
  )
  const isAvailable = (value: NotificationChannelKind) => availability.get(value) ?? true

  const reset = () => {
    setName('')
    setWebhookUrl('')
    setTelegramToken('')
    setTelegramChatId('')
    setEmailTo('')
  }

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!name.trim()) {
      setError('Channel name is required')
      return
    }
    if (!isAvailable(kind)) {
      setError(`The ${kind} provider is not configured on this server`)
      return
    }
    let payload: NotificationChannelCreate
    if (kind === 'discord' || kind === 'slack' || kind === 'webhook') {
      if (!webhookUrl.trim().startsWith('https://')) {
        setError('Destination URL must use https')
        return
      }
      payload = { name: name.trim(), kind, webhook_url: webhookUrl.trim() }
    } else if (kind === 'telegram') {
      if (!telegramToken.trim() || !telegramChatId.trim()) {
        setError('Telegram bot token and chat id are required')
        return
      }
      payload = {
        name: name.trim(),
        kind,
        telegram_bot_token: telegramToken.trim(),
        telegram_chat_id: telegramChatId.trim(),
      }
    } else if (kind === 'email') {
      if (!emailTo.trim()) {
        setError('Email recipient is required')
        return
      }
      payload = { name: name.trim(), kind, email_to: emailTo.trim() }
    } else {
      setError('Use “Subscribe this browser” to add a browser push channel')
      return
    }
    createChannel.mutate(payload, { onSuccess: reset })
  }

  const subscribeBrowser = async () => {
    setError(null)
    if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
      setError('This browser does not support push notifications')
      return
    }
    if (!vapid?.key) {
      setError('Browser push is not configured on this server (VAPID keys missing)')
      return
    }
    setSubscribing(true)
    try {
      const permission = await Notification.requestPermission()
      if (permission !== 'granted') {
        setError('Notification permission was not granted')
        return
      }
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapid.key) as unknown as BufferSource,
      })
      const json = subscription.toJSON() as {
        endpoint?: string
        keys?: { p256dh?: string; auth?: string }
      }
      if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
        throw new Error('Push subscription is missing required keys')
      }
      createChannel.mutate(
        {
          name: name.trim() || 'Browser push',
          kind: 'browser_push',
          subscription: {
            endpoint: json.endpoint,
            keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
          },
        },
        { onSuccess: reset },
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Push subscription failed'
      setError(message)
      toast.error(message)
    } finally {
      setSubscribing(false)
    }
  }

  const failedDeliveries = (deliveriesData?.deliveries ?? []).filter(
    (delivery) => delivery.status === 'failed',
  )

  const field = (id: string, label: string, value: string, onChange: (value: string) => void, placeholder = '') => (
    <div>
      <label htmlFor={id} className="text-sm text-muted-foreground">
        {label}
      </label>
      <input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
      />
    </div>
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="w-5 h-5" aria-hidden="true" />
            Notification Channels
          </CardTitle>
          <CardDescription>
            Discord, Slack, Telegram, generic HTTPS webhooks, email, and browser push.
            Credentials are stored server-side and never returned in full.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={onSubmit} className="space-y-3">
            <div>
              <label htmlFor={`${formId}-kind`} className="text-sm text-muted-foreground">
                Provider
              </label>
              <select
                id={`${formId}-kind`}
                value={kind}
                onChange={(event) => setKind(event.target.value as NotificationChannelKind)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {KIND_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value} disabled={!isAvailable(option.value)}>
                    {option.label}
                    {isAvailable(option.value) ? '' : ' (not configured)'}
                  </option>
                ))}
              </select>
            </div>
            {field(`${formId}-name`, 'Channel name', name, setName, 'Ops alerts')}
            {(kind === 'discord' || kind === 'slack' || kind === 'webhook') &&
              field(
                `${formId}-url`,
                kind === 'discord' ? 'Discord webhook URL' : kind === 'slack' ? 'Slack webhook URL' : 'Webhook URL',
                webhookUrl,
                setWebhookUrl,
                'https://…',
              )}
            {kind === 'telegram' && (
              <>
                {field(`${formId}-tg-token`, 'Bot token', telegramToken, setTelegramToken, '123456:ABC…')}
                {field(`${formId}-tg-chat`, 'Chat id', telegramChatId, setTelegramChatId, '-1001234567890')}
              </>
            )}
            {kind === 'email' && field(`${formId}-email`, 'Recipient', emailTo, setEmailTo, 'ops@example.com')}
            {kind === 'browser_push' && (
              <div className="rounded-md border border-border p-3 text-sm">
                <p className="text-muted-foreground">
                  {vapid?.status === 'ok'
                    ? 'Subscribe this browser to receive OS-level notifications via Web Push.'
                    : 'Browser push is not configured on this server.'}
                </p>
                <button
                  type="button"
                  onClick={() => { void subscribeBrowser() }}
                  disabled={subscribing || vapid?.status !== 'ok'}
                  className="mt-2 inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent disabled:opacity-50"
                >
                  <BellRing className="w-3.5 h-3.5" aria-hidden="true" />
                  {subscribing ? 'Subscribing…' : 'Subscribe this browser'}
                </button>
              </div>
            )}
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={createChannel.isPending || kind === 'browser_push'}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              <Send className="w-4 h-4" aria-hidden="true" />
              {createChannel.isPending ? 'Adding…' : 'Add channel'}
            </button>
          </form>

          {isLoading && <p className="text-sm text-muted-foreground">Loading channels…</p>}
          {isError && <p className="text-sm text-destructive">Failed to load notification channels</p>}
          {data && data.channels.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No external channels configured. Alerts remain visible in the app.
            </p>
          )}
          <ul className="space-y-2">
            {data?.channels.map((channel) => (
              <li
                key={channel.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border p-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{channel.name}</span>
                    <Badge variant="secondary">{channel.kind}</Badge>
                    <Badge variant={channel.enabled ? 'success' : 'secondary'}>
                      {channel.enabled ? 'On' : 'Off'}
                    </Badge>
                  </div>
                  <p className="truncate text-xs text-muted-foreground">{channel.destination}</p>
                </div>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => testChannel.mutate(channel.id)}
                    disabled={testChannel.isPending}
                    className="rounded-md border border-border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
                  >
                    Send test
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteChannel.mutate(channel.id)}
                    aria-label={`Delete channel ${channel.name}`}
                    className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Delivery Status</CardTitle>
          <CardDescription>
            Durable attempts with bounded retries. Duplicate events are never sent twice.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {failedDeliveries.length > 0 && (
            <p role="alert" className="mb-3 text-sm text-destructive">
              {failedDeliveries.length} delivery failure(s) need attention.
            </p>
          )}
          {!deliveriesData || deliveriesData.deliveries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No external deliveries yet. Trigger an alert after adding a channel.
            </p>
          ) : (
            <ul className="space-y-2">
              {deliveriesData.deliveries.slice(0, 20).map((delivery) => (
                <li
                  key={delivery.id}
                  className="flex items-center justify-between gap-3 rounded-md border border-border p-3"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Event #{delivery.alert_event_id}</span>
                      <Badge
                        variant={
                          delivery.status === 'sent'
                            ? 'success'
                            : delivery.status === 'failed'
                              ? 'destructive'
                              : 'secondary'
                        }
                      >
                        {delivery.status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {delivery.channel_name ?? 'channel'} · {delivery.attempts} attempt(s)
                      </span>
                    </div>
                    {delivery.last_error && (
                      <p className="truncate text-xs text-destructive">{delivery.last_error}</p>
                    )}
                  </div>
                  {delivery.status === 'failed' && (
                    <button
                      type="button"
                      onClick={() => retryDelivery.mutate(delivery.id)}
                      disabled={retryDelivery.isPending}
                      className="rounded-md border border-border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
                    >
                      Retry
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
