import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { verifySessionToken, SESSION_COOKIE_NAME } from '@/lib/session'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const HOP_BY_HOP_HEADERS = new Set(['host', 'cookie', 'connection', 'content-length'])

async function handler(req: NextRequest) {
  const appPassword = process.env.APP_PASSWORD

  if (appPassword) {
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
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) headers.set(key, value)
  })
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
