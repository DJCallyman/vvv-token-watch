import { Dashboard } from '@/components/dashboard/Dashboard'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export const metadata = {
  title: 'Usage - VVV Token Watch',
}

export default function UsagePage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Dashboard />
        </main>
      </div>
    </div>
  )
}