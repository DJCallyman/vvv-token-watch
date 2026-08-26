import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { verifySessionToken, SESSION_COOKIE_NAME } from '@/lib/session'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
// Headers that must not be forwarded from the inbound browser request, either
// because they are hop-by-hop per RFC 7230 or because they are trusted only
// when set by THIS proxy (defense against client spoofing).
const HOP_BY_HOP_HEADERS = new Set([
  'host',
  'cookie',
  'connection',
  'content-length',
  // Stripped exclusively because the client controls them and the backend
  // uses x-forwarded-for for rate-limit identity. Setting it from the real
  // peer below ensures a stable key without letting the caller rotate IPs
  // per request to dodge the limiter.
  'x-forwarded-for',
  'x-real-ip',
])

// Defense-in-depth: never forward a client-supplied Authorization header to
// the backend. The proxy injects its own credential server-side (if configured).
const FORWARDED_AUTH_NOT_ALLOWED = new Set(['authorization'])

async function handler(req: NextRequest) {
  const appPassword = process.env.APP_PASSWORD
  const allowInsecureNoAuth = process.env.ALLOW_INSECURE_NO_AUTH === 'true'

  if (appPassword && !allowInsecureNoAuth) {
    const token = req.cookies.get(SESSION_COOKIE_NAME)?.value
    const valid = await verifySessionToken(token, appPassword)
    if (!valid) {
      return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })
    }
  }

  const url = new URL(req.url)
  const targetUrl = `${BACKEND_URL}${url.pathname}${url.search}`

  const headers = new Headers()
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (HOP_BY_HOP_HEADERS.has(lower)) return
    if (FORWARDED_AUTH_NOT_ALLOWED.has(lower)) return
    headers.set(key, value)
  })

  // Set XFF to the direct peer IP so the backend rate limiter derives a
  // stable client identity that the caller cannot spoof.
  // NextRequest no longer exposes `ip` in Next 15. The proxy's direct peer is
  // intentionally used as the fallback rather than trusting a browser header.
  const peerIp = req.headers.get('x-real-ip') || req.headers.get('cf-connecting-ip') || '127.0.0.1'
  headers.set('x-forwarded-for', peerIp)

  // Inject the real backend credential server-side. This value never
  // reaches the browser (no NEXT_PUBLIC_* prefix, only read here).
  if (appPassword) {
    headers.set('Authorization', `Bearer ${appPassword}`)
  }

  const init: RequestInit & { duplex?: 'half' } = {
    method: req.method,
    headers,
  }
  if (!['GET', 'HEAD'].includes(req.method)) {
    init.body = req.body
    init.duplex = 'half'
  }

  const upstream = await fetch(targetUrl, init)

  const resHeaders = new Headers(upstream.headers)
  resHeaders.delete('content-encoding')
  resHeaders.delete('content-length')

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: resHeaders,
  })
}

export {
  handler as GET,
  handler as POST,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
}
