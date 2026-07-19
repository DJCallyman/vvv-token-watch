import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { verifySessionToken, SESSION_COOKIE_NAME } from '@/lib/session'

export async function middleware(req: NextRequest) {
  const appPassword = process.env.APP_PASSWORD

  // Always allow the login page/API and Next internals through.
  if (
    req.nextUrl.pathname === '/login' ||
    req.nextUrl.pathname.startsWith('/api/auth/')
  ) {
    return NextResponse.next()
  }

  // If APP_PASSWORD isn't configured, the backend itself refuses to start
  // (see backend/main.py SEC-01 fail-closed check) unless the operator
  // explicitly opted into ALLOW_INSECURE_NO_AUTH. Nothing to gate here.
  if (!appPassword) {
    return NextResponse.next()
  }

  const token = req.cookies.get(SESSION_COOKIE_NAME)?.value
  const valid = await verifySessionToken(token, appPassword)

  if (valid) {
    return NextResponse.next()
  }

  const isApi = req.nextUrl.pathname.startsWith('/api/')
  if (isApi) {
    return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })
  }

  const loginUrl = new URL('/login', req.url)
  loginUrl.searchParams.set('next', req.nextUrl.pathname)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: ['/((?!login|_next/static|_next/image|favicon.ico).*)'],
}
