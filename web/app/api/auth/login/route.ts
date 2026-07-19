import { NextRequest, NextResponse } from 'next/server'
import { createSessionToken, SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, timingSafeStringEqual } from '@/lib/session'

export async function POST(req: NextRequest) {
  const appPassword = process.env.APP_PASSWORD

  if (!appPassword) {
    return NextResponse.json(
      { error: 'Server is not configured with APP_PASSWORD.' },
      { status: 500 },
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
    return NextResponse.json({ error: 'Invalid password.' }, { status: 401 })
  }

  const token = await createSessionToken(appPassword)
  const res = NextResponse.json({ ok: true })
  res.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: SESSION_TTL_SECONDS,
  })
  return res
}
