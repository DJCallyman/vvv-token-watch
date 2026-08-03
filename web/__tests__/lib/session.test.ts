/**
 * @jest-environment node
 *
 * session.ts uses Web Crypto which is available in Node 18+ under the node
 * jest env. We deliberately avoid jsdom here to skip DOM polyfills for
 * tokenizer code that has nothing to do with the DOM.
 */

import {
  createSessionToken,
  verifySessionToken,
  timingSafeStringEqual,
} from '@/lib/session'

const SECRET = 'unit-test-secret'

describe('createSessionToken / verifySessionToken', () => {
  it('verifies a freshly minted token', async () => {
    const token = await createSessionToken(SECRET)
    expect(await verifySessionToken(token, SECRET)).toBe(true)
  })

  it('rejects a token signed with a different secret', async () => {
    const token = await createSessionToken(SECRET)
    expect(await verifySessionToken(token, 'wrong-secret')).toBe(false)
  })

  it('rejects an empty / undefined token', async () => {
    expect(await verifySessionToken(undefined, SECRET)).toBe(false)
    expect(await verifySessionToken(null, SECRET)).toBe(false)
    expect(await verifySessionToken('', SECRET)).toBe(false)
  })

  it('rejects a token with the wrong number of parts', async () => {
    expect(await verifySessionToken('not-a-real-token', SECRET)).toBe(false)
    expect(await verifySessionToken('one.two.three', SECRET)).toBe(false)
  })

  it('rejects a tampered payload (signature still valid for original)', async () => {
    const token = await createSessionToken(SECRET)
    const [payload, sig] = token.split('.')
    // Swap payload to something different; signature won't match the new payload.
    const tampered = `${btoa('{"exp":9999999999999}').replace(/=/g, '')}.${sig}`
    expect(await verifySessionToken(tampered, SECRET)).toBe(false)
  })

  it('rejects a tampered signature', async () => {
    const token = await createSessionToken(SECRET)
    const [payload] = token.split('.')
    expect(await verifySessionToken(`${payload}.AAAA`, SECRET)).toBe(false)
  })

  it('rejects an expired token', async () => {
    // Mint a token at "now" (TTL = 7 days from now), then advance the clock
    // past its exp and verify it's rejected.
    const originalNow = Date.now
    const issued = originalNow()
    Date.now = () => issued
    try {
      const token = await createSessionToken(SECRET)
      // Jump 8 days ahead — well past the 7-day TTL.
      Date.now = () => issued + 8 * 24 * 60 * 60 * 1000
      expect(await verifySessionToken(token, SECRET)).toBe(false)
    } finally {
      Date.now = originalNow
    }
  })
})

describe('timingSafeStringEqual', () => {
  it('returns true for identical strings', () => {
    expect(timingSafeStringEqual('abc', 'abc')).toBe(true)
    expect(timingSafeStringEqual('', '')).toBe(true)
  })

  it('returns false for different strings of equal length', () => {
    expect(timingSafeStringEqual('abc', 'abd')).toBe(false)
  })

  it('returns false for different length strings', () => {
    expect(timingSafeStringEqual('abc', 'abcd')).toBe(false)
    expect(timingSafeStringEqual('a', 'aa')).toBe(false)
  })

  it('handles unicode safely', () => {
    expect(timingSafeStringEqual('héllo', 'héllo')).toBe(true)
    expect(timingSafeStringEqual('héllo', 'hèllo')).toBe(false)
  })
})
