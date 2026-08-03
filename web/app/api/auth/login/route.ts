import { NextRequest, NextResponse } from 'next/server'
import {
  createSessionToken,
  SESSION_COOKIE_NAME,
  SESSION_TTL_SECONDS,
  timingSafeStringEqual,
} from '@/lib/session'
import {
  clientKeyFromHeaders,
  defaultLoginLimiter,
} from '@/lib/login-rate-limit'

function sessionSecureCookie(): boolean {
  // Default: true in production builds of Next.js, false otherwise. The
  // explicit env override lets operators serve over plain HTTP (LAN / Unraid
  // reverse-proxy offloading TLS) without silently losing Secure cookies —
  // which would make login appear to succeed but never persist.
  const override = process.env.SESSION_SECURE_COOKIE
  if (override === 'true') return true
  if (override === 'false') return false
  return process.env.NODE_ENV === 'production'
}

export async function POST(req: NextRequest) {
  const appPassword = process.env.APP_PASSWORD

  if (!appPassword) {
    return NextResponse.json(
      { error: 'Server is not configured with APP_PASSWORD.' },
      { status: 500 },
    )
  }

  const clientKey = clientKeyFromHeaders(req.headers)
  const limit = defaultLoginLimiter.check(clientKey)
  if (!limit.allowed) {
    return NextResponse.json(
      { error: 'Too many failed attempts. Try again later.' },
      {
        status: 429,
        headers: { 'Retry-After': String(limit.retryAfterSeconds) },
      },
    )
  }

  let password = ''
  try {
    const body = await req.json()
    password = typeof body?.password === 'string' ? body.password : ''
  } catch {
    return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 })
  }

  if (!password || !timingSafeStringEqual(password, appPassword)) {
    defaultLoginLimiter.recordFailure(clientKey)
    return NextResponse.json({ error: 'Invalid password.' }, { status: 401 })
  }

  defaultLoginLimiter.clear(clientKey)
  const token = await createSessionToken(appPassword)
  const res = NextResponse.json({ ok: true })
  res.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: sessionSecureCookie(),
    sameSite: 'lax',
    path: '/',
    maxAge: SESSION_TTL_SECONDS,
  })
  return res
}
