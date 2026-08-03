import { safeNextPath } from '@/lib/safe-next-path'

describe('safeNextPath', () => {
  it('returns the fallback when given null/undefined/empty', () => {
    expect(safeNextPath(null)).toBe('/')
    expect(safeNextPath(undefined)).toBe('/')
    expect(safeNextPath('')).toBe('/')
  })

  it('accepts same-origin relative paths', () => {
    expect(safeNextPath('/')).toBe('/')
    expect(safeNextPath('/dashboard')).toBe('/dashboard')
    expect(safeNextPath('/dashboard?tab=models')).toBe('/dashboard?tab=models')
    expect(safeNextPath('/path/with/many/segments')).toBe('/path/with/many/segments')
  })

  it('rejects absolute URLs (open-redirect prevention)', () => {
    expect(safeNextPath('https://evil.example')).toBe('/')
    expect(safeNextPath('http://evil.example')).toBe('/')
    expect(safeNextPath('javascript:alert(1)')).toBe('/')
  })

  it('rejects protocol-relative URLs', () => {
    expect(safeNextPath('//evil.example')).toBe('/')
    expect(safeNextPath('//evil.example/path')).toBe('/')
  })

  it('rejects paths without a leading slash', () => {
    expect(safeNextPath('dashboard')).toBe('/')
    expect(safeNextPath('relative/path')).toBe('/')
  })

  it('allows a custom fallback', () => {
    expect(safeNextPath(null, '/home')).toBe('/home')
    expect(safeNextPath('https://evil.example', '/home')).toBe('/home')
  })
})
