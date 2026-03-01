import { PricesView } from '@/components/prices/PricesView'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export const metadata = {
  title: 'Prices - VVV Token Watch',
}

export default function PricesPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <PricesView />
        </main>
      </div>
    </div>
  )
}