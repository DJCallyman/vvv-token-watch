import { ApiKeysView } from '@/components/apikeys/ApiKeysView'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export const metadata = {
  title: 'API Keys - VVV Token Watch',
}

export default function ApiKeysPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <ApiKeysView />
        </main>
      </div>
    </div>
  )
}
