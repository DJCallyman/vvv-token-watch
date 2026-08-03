import {
  LoginRateLimiter,
  clientKeyFromHeaders,
} from '@/lib/login-rate-limit'

class FakeHeaders {
  private readonly map: Record<string, string>
  constructor(entries: Record<string, string>) {
    this.map = { ...entries }
  }
  get(name: string): string | null {
    return this.map[name.toLowerCase()] ?? null
  }
}

describe('LoginRateLimiter', () => {
  const FIXED_NOW = 1_700_000_000_000
  const WINDOW = 15 * 60 * 1000

  function makeLimiter(max = 5, windowMs = WINDOW) {
    let now = FIXED_NOW
    return {
      limiter: new LoginRateLimiter({
        maxAttempts: max,
        windowMs,
        now: () => now,
      }),
      advance: (ms: number) => {
        now += ms
      },
    }
  }

  it('allows requests under the threshold', () => {
    const { limiter } = makeLimiter()
    let result = limiter.check('1.2.3.4')
    expect(result.allowed).toBe(true)
    expect(result.attempts).toBe(0)
    for (let i = 0; i < 4; i++) {
      limiter.recordFailure('1.2.3.4')
    }
    result = limiter.check('1.2.3.4')
    expect(result.allowed).toBe(true)
    expect(result.attempts).toBe(4)
  })

  it('blocks requests at and above maxAttempts', () => {
    const { limiter } = makeLimiter(5)
    for (let i = 0; i < 5; i++) limiter.recordFailure('1.2.3.4')
    const result = limiter.check('1.2.3.4')
    expect(result.allowed).toBe(false)
    expect(result.attempts).toBe(5)
    expect(result.retryAfterSeconds).toBeGreaterThan(0)
  })

  it('emits a Retry-After that covers the remaining window', () => {
    const { limiter, advance } = makeLimiter(5, WINDOW)
    for (let i = 0; i < 5; i++) limiter.recordFailure('1.2.3.4')
    advance(WINDOW / 2)
    const result = limiter.check('1.2.3.4')
    expect(result.allowed).toBe(false)
    // Window was reclaimed half-way through; we are 7.5min away from eligibility.
    expect(result.retryAfterSeconds).toBeGreaterThanOrEqual(450)
    expect(result.retryAfterSeconds).toBeLessThanOrEqual(451)
  })

  it('becomes eligible again after the window elapses', () => {
    const { limiter, advance } = makeLimiter(5, WINDOW)
    for (let i = 0; i < 5; i++) limiter.recordFailure('1.2.3.4')
    advance(WINDOW + 1)
    const result = limiter.check('1.2.3.4')
    expect(result.allowed).toBe(true)
    expect(result.attempts).toBe(0)
  })

  it('clears the bucket on success', () => {
    const { limiter, advance } = makeLimiter(5, WINDOW)
    for (let i = 0; i < 4; i++) limiter.recordFailure('1.2.3.4')
    limiter.clear('1.2.3.4')
    advance(WINDOW + 1)
    // Fresh start: a full quota of failures must be required to block again.
    for (let i = 0; i < 4; i++) limiter.recordFailure('1.2.3.4')
    expect(limiter.check('1.2.3.4').allowed).toBe(true)
  })

  it('isolates buckets per client', () => {
    const { limiter } = makeLimiter(2)
    limiter.recordFailure('1.1.1.1')
    limiter.recordFailure('1.1.1.1')
    expect(limiter.check('1.1.1.1').allowed).toBe(false)
    expect(limiter.check('2.2.2.2').allowed).toBe(true)
  })

  it('rolls stale buckets forward on new failures', () => {
    const { limiter, advance } = makeLimiter(3, WINDOW)
    limiter.recordFailure('1.2.3.4')
    advance(WINDOW + 1000)
    limiter.recordFailure('1.2.3.4')
    limiter.recordFailure('1.2.3.4')
    // Two failures in the new window — below the limit.
    expect(limiter.check('1.2.3.4').allowed).toBe(true)
    limiter.recordFailure('1.2.3.4')
    expect(limiter.check('1.2.3.4').allowed).toBe(false)
  })
})

describe('clientKeyFromHeaders', () => {
  it('uses the first hop of x-forwarded-for', () => {
    const h = new FakeHeaders({ 'x-forwarded-for': '8.8.8.8, 10.0.0.1' })
    expect(clientKeyFromHeaders(h)).toBe('8.8.8.8')
  })

  it('trims whitespace around the first hop', () => {
    const h = new FakeHeaders({ 'x-forwarded-for': '  8.8.8.8 , 10.0.0.1' })
    expect(clientKeyFromHeaders(h)).toBe('8.8.8.8')
  })

  it('falls back to "local" when x-forwarded-for is absent', () => {
    const h = new FakeHeaders({})
    expect(clientKeyFromHeaders(h)).toBe('local')
  })

  it('falls back to "local" when x-forwarded-for is empty', () => {
    const h = new FakeHeaders({ 'x-forwarded-for': '' })
    expect(clientKeyFromHeaders(h)).toBe('local')
  })
})
