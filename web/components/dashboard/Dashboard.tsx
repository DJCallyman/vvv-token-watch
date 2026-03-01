'use client'

import { HeroBalanceCard } from './HeroBalanceCard'
import { TodayUsageCard } from './TodayUsageCard'
import { PriceCards } from './PriceCards'
import { UsageLeaderboardCard } from './UsageLeaderboardCard'

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <HeroBalanceCard />
        </div>
        <div>
          <TodayUsageCard />
        </div>
      </div>
      
      <PriceCards />
      
      <UsageLeaderboardCard />
    </div>
  )
}