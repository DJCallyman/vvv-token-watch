import { fireEvent, render, screen, within } from '../../test-utils'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'

interface TestRow {
  id: string
  name: string
  amount: number
}

const rows: TestRow[] = Array.from({ length: 12 }, (_, index) => ({
  id: `row-${index + 1}`,
  name: `Item ${String(index + 1).padStart(2, '0')}`,
  amount: index + 1,
}))

const columns: DataTableColumn<TestRow>[] = [
  { id: 'name', header: 'Name', cell: (row) => row.name, sortValue: (row) => row.name },
  { id: 'amount', header: 'Amount', cell: (row) => row.amount, sortValue: (row) => row.amount },
]

describe('DataTable', () => {
  it('sorts rows by a sortable column', () => {
    render(
      <DataTable
        rows={rows.slice(0, 3)}
        columns={columns}
        getRowId={(row) => row.id}
        ariaLabel="Test data"
        emptyMessage="No rows"
      />,
    )

    const table = screen.getByRole('table', { name: 'Test data' })
    fireEvent.click(within(table).getByRole('button', { name: /amount/i }))

    const bodyRows = within(table).getAllByRole('row').slice(1)
    expect(bodyRows.map((row) => within(row).getAllByRole('cell')[1].textContent)).toEqual(['1', '2', '3'])
    expect(within(table).getByRole('columnheader', { name: /amount/i })).toHaveAttribute('aria-sort', 'ascending')
  })

  it('paginates and allows columns to be hidden', () => {
    render(
      <DataTable
        rows={rows}
        columns={columns}
        getRowId={(row) => row.id}
        ariaLabel="Test data"
        emptyMessage="No rows"
      />,
    )

    const table = screen.getByRole('table', { name: 'Test data' })
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('11–12 of 12')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(3)

    fireEvent.click(screen.getByText('Columns'))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Name' }))
    expect(within(table).queryByRole('columnheader', { name: /name/i })).not.toBeInTheDocument()
  })
})