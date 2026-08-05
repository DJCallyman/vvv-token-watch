import { CharactersView } from '@/components/characters/CharactersView'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export const metadata = {
  title: 'Characters - VVV Token Watch',
}

export default function CharactersPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <CharactersView />
        </main>
      </div>
    </div>
  )
}
