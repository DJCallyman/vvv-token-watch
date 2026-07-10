import { OnChainView } from '@/components/onchain/OnChainView'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export const metadata = {
  title: 'On-Chain - VVV Token Watch',
}

export default function OnChainPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <OnChainView />
        </main>
      </div>
    </div>
  )
}
