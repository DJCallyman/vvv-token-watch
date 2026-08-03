/**
 * Validate the `next` redirect target returned to a successful login.
 *
 * Only same-origin relative paths are accepted; absolute URLs and
 * protocol-relative URLs are silently dropped to a fallback to prevent
 * open-redirects via crafted /login?next=… links.
 */

export function safeNextPath(raw: string | null | undefined, fallback = '/'): string {
  if (!raw) return fallback
  if (typeof raw !== 'string') return fallback
  if (!raw.startsWith('/')) return fallback
  if (raw.startsWith('//')) return fallback
  return raw
}
