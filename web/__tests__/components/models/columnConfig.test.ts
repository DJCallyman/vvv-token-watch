import { getColumnsForType } from '@/components/models/columnConfig'

describe('model column configuration', () => {
  it('supports music models in the catalog table', () => {
    const columns = getColumnsForType('music')

    expect(columns.map((column) => column.key)).toEqual(expect.arrayContaining(['model', 'type']))
  })
})
