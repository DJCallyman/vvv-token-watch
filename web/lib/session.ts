/**
 * Stateless session tokens for the shared-password auth flow.
 *
 * The token is an HMAC-signed, base64url-encoded payload containing an
 * expiry timestamp. It is signed with the server-only APP_PASSWORD secret
 * using Web Crypto (available in both the Node.js and Edge runtimes), so it
 * can be verified from middleware (Edge) and route handlers (Node) alike
 * without any server-side session store.
 *
 * The token itself is NOT the password — it cannot be used to derive the
 * password, and it is only ever stored in an HttpOnly cookie, never sent to
 * client-side JavaScript.
 */

export const SESSION_COOKIE_NAME = 'vvv_session'
export const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7 // 7 days

function base64UrlEncode(bytes: Uint8Array): string {
  let str = ''
  for (const b of bytes) {
    str += String.fromCharCode(b)
  }
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function base64UrlDecode(str: string): Uint8Array<ArrayBuffer> {
  const padLength = (4 - (str.length % 4)) % 4
  const padded = str.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(padLength)
  const bin = atob(padded)
  const bytes = new Uint8Array(new ArrayBuffer(bin.length))
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return bytes
}

async function getHmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify'],
  )
}

export async function createSessionToken(secret: string): Promise<string> {
  const payload = JSON.stringify({ exp: Date.now() + SESSION_TTL_SECONDS * 1000 })
  const payloadB64 = base64UrlEncode(new TextEncoder().encode(payload))
  const key = await getHmacKey(secret)
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payloadB64))
  const sigB64 = base64UrlEncode(new Uint8Array(sig))
  return `${payloadB64}.${sigB64}`
}

export async function verifySessionToken(
  token: string | undefined | null,
  secret: string,
): Promise<boolean> {
  if (!token) return false
  const parts = token.split('.')
  if (parts.length !== 2) return false
  const [payloadB64, sigB64] = parts
  try {
    const key = await getHmacKey(secret)
    const valid = await crypto.subtle.verify(
      'HMAC',
      key,
      base64UrlDecode(sigB64),
      new TextEncoder().encode(payloadB64),
    )
    if (!valid) return false
    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(payloadB64))) as {
      exp?: number
    }
    return typeof payload.exp === 'number' && payload.exp > Date.now()
  } catch {
    return false
  }
}

export function timingSafeStringEqual(a: string, b: string): boolean {
  const aBytes = new TextEncoder().encode(a)
  const bBytes = new TextEncoder().encode(b)
  if (aBytes.length !== bBytes.length) return false
  let diff = 0
  for (let i = 0; i < aBytes.length; i++) diff |= aBytes[i] ^ bBytes[i]
  return diff === 0
}
