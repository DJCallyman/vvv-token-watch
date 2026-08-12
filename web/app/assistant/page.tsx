import { AssistantView } from '@/components/assistant/AssistantView'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
export default function AssistantPage() { return <div className="flex h-screen bg-background"><Sidebar /><div className="flex-1 flex flex-col overflow-hidden"><Header /><main className="flex-1 overflow-y-auto p-6"><AssistantView /></main></div></div> }
