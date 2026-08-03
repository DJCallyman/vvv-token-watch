/**
 * Process-local rate limiter for the /api/auth/login endpoint.
 *
 * Protects the shared-password gate from rapid brute-force attempts. The
 * limiter is keyed by the request's "client identity" (first hop of
 * X-Forwarded-For, falling back to a local marker). On a successful login
 * the bucket is cleared so legitimate retries do not accumulate.
 *
 * State is in-memory: counters reset on container restart, which is
 * acceptable for a single-container self-hosted deployment. Add a Redis
 * backend if the deployment ever scales out.
 */

export interface RateLimitOptions {
  /** Max failures allowed inside the window before requests are blocked. */
  readonly maxAttempts?: number;
  /** Sliding window length in milliseconds. */
  readonly windowMs?: number;
  /** Clock injection for tests; defaults to Date.now. */
  readonly now?: () => number;
}

export interface RateLimitResult {
  readonly allowed: boolean;
  /** Seconds the client should wait before retrying; populated when blocked. */
  readonly retryAfterSeconds: number;
  /** Failures observed inside the current window. */
  readonly attempts: number;
}

interface Bucket {
  attempts: number;
  firstAt: number;
  lastAt: number;
}

const DEFAULTS: Required<Omit<RateLimitOptions, 'now'>> = {
  maxAttempts: 5,
  windowMs: 15 * 60 * 1000,
};

export class LoginRateLimiter {
  private readonly buckets = new Map<string, Bucket>();
  private readonly maxAttempts: number;
  private readonly windowMs: number;
  private readonly now: () => number;

  constructor(options: RateLimitOptions = {}) {
    this.maxAttempts = options.maxAttempts ?? DEFAULTS.maxAttempts;
    this.windowMs = options.windowMs ?? DEFAULTS.windowMs;
    this.now = options.now ?? Date.now;
  }

  /**
   * Inspect a request. Returns whether it is allowed plus a Retry-After hint
   * (in whole seconds, per RFC 7231). Does NOT mutate state — call
   * `recordFailure` / `clear` as appropriate.
   */
  check(key: string): RateLimitResult {
    const bucket = this.buckets.get(key);
    if (!bucket) {
      return { allowed: true, retryAfterSeconds: 0, attempts: 0 };
    }
    this.prune(bucket);
    if (bucket.attempts < this.maxAttempts) {
      return { allowed: true, retryAfterSeconds: 0, attempts: bucket.attempts };
    }
    // Blocked. Retry-After is the time until the oldest attempt falls outside
    // the window — a conservative (and RFC-compliant) hint.
    const msUntilEligible = bucket.firstAt + this.windowMs - this.now();
    const retryAfterSeconds = Math.max(
      1,
      Math.ceil(msUntilEligible / 1000),
    );
    return {
      allowed: false,
      retryAfterSeconds,
      attempts: bucket.attempts,
    };
  }

  recordFailure(key: string): RateLimitResult {
    const now = this.now();
    const bucket = this.buckets.get(key);
    if (!bucket) {
      this.buckets.set(key, { attempts: 1, firstAt: now, lastAt: now });
      return { allowed: true, retryAfterSeconds: 0, attempts: 1 };
    }
    // If the existing bucket's window has fully elapsed, start fresh.
    if (now - bucket.firstAt >= this.windowMs) {
      bucket.attempts = 1;
      bucket.firstAt = now;
      bucket.lastAt = now;
    } else {
      bucket.attempts += 1;
      bucket.lastAt = now;
    }
    return this.check(key);
  }

  clear(key: string): void {
    this.buckets.delete(key);
  }

  /** Test helper — drops all state. */
  reset(): void {
    this.buckets.clear();
  }

  private prune(bucket: Bucket): void {
    if (this.now() - bucket.firstAt >= this.windowMs) {
      bucket.attempts = 0;
    }
  }
}

/**
 * Derive a stable client identity for the rate-limit key.
 *
 * Trust order: first hop of X-Forwarded-For if present (matches the
 * default origin: the browser reached Next.js which is the only trusted
 * proxy in this stack), otherwise a local marker so unit tests and
 * direct-loopback callers get their own bucket instead of colliding.
 */
export function clientKeyFromHeaders(headers: {
  get(name: string): string | null;
}): string {
  const xff = headers.get('x-forwarded-for');
  if (xff) {
    const first = xff.split(',')[0]?.trim();
    if (first) return first;
  }
  return 'local';
}

// Default singleton for the login route. Tests construct their own instance
// with custom clock/window settings rather than touching this one.
export const defaultLoginLimiter = new LoginRateLimiter();
