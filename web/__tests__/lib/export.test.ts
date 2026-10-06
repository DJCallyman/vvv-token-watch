import {
  buildSnapshot,
  csvFilename,
  csvCell,
  exportCsv,
  exportJson,
  snapshotFilename,
  toCsv,
  toPrettyJson,
} from '@/lib/export'

describe('csvCell', () => {
  it('escapes commas, quotes, and newlines', () => {
    expect(csvCell('plain')).toBe('plain')
    expect(csvCell('a,b')).toBe('"a,b"')
    expect(csvCell('say "hi"')).toBe('"say ""hi"""')
    expect(csvCell('line\nbreak')).toBe('"line\nbreak"')
    expect(csvCell(null)).toBe('')
    expect(csvCell(undefined)).toBe('')
  })

  it('serializes objects as JSON', () => {
    expect(csvCell({ a: 1 })).toBe('"{""a"":1}"')
  })
})

describe('toCsv', () => {
  it('produces a header and rows', () => {
    const csv = toCsv([
      { name: 'vvv', price: 1.5 },
      { name: 'diem', price: 2 },
    ])
    expect(csv).toBe('name,price\nvvv,1.5\ndiem,2')
  })

  it('uses a union of keys in first-seen order', () => {
    const csv = toCsv([{ a: 1 }, { b: 2 }])
    expect(csv).toBe('a,b\n1,\n,2')
  })

  it('returns empty string for no rows', () => {
    expect(toCsv([])).toBe('')
  })
})

describe('filenames and snapshots', () => {
  const fixed = new Date('2026-01-02T03:04:05.678Z')

  it('stamps filenames deterministically', () => {
    expect(snapshotFilename('usage', fixed)).toBe('usage-2026-01-02T03-04-05-678Z.json')
    expect(csvFilename('usage', fixed)).toBe('usage-2026-01-02.csv')
  })

  it('wraps snapshot payloads with version and timestamp', () => {
    const snapshot = buildSnapshot('2026-01-02T03:04:05Z', { balance: 1 })
    expect(snapshot).toEqual({
      app: 'vvv-token-watch',
      snapshot_version: 1,
      generated_at: '2026-01-02T03:04:05Z',
      data: { balance: 1 },
    })
  })

  it('pretty-prints JSON', () => {
    expect(toPrettyJson({ a: 1 })).toBe('{\n  "a": 1\n}')
  })
})

describe('download helpers', () => {
  const originalCreate = URL.createObjectURL
  const originalRevoke = URL.revokeObjectURL

  afterEach(() => {
    URL.createObjectURL = originalCreate
    URL.revokeObjectURL = originalRevoke
  })

  it('creates and revokes an object URL and clicks an anchor', () => {
    const createObjectURL = jest.fn(() => 'blob:mock')
    const revokeObjectURL = jest.fn()
    URL.createObjectURL = createObjectURL
    URL.revokeObjectURL = revokeObjectURL
    const click = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    exportJson('test.json', { a: 1 })
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(click).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock')

    exportCsv('test.csv', [{ a: 1 }])
    expect(createObjectURL).toHaveBeenCalledTimes(2)
    click.mockRestore()
  })
})
