import { useState } from 'react'
import { Toaster } from 'sonner'
import { useTranslation } from 'react-i18next'
import { Sidebar } from '@/components/layout/Sidebar'
import { CrawlerConfigPanel } from '@/components/config/CrawlerConfigPanel'
import { TrendRadarPanel } from '@/components/trend/TrendRadarPanel'
import { TerminalDialog } from '@/components/console/TerminalDialog'
import { EnvironmentCheck, isEnvChecked } from '@/components/env/EnvironmentCheck'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

function App() {
  const [envChecked, setEnvChecked] = useState(() => isEnvChecked())
  const { t } = useTranslation('trend')

  return (
    <div className="flex flex-col h-screen cyber-grid overflow-hidden relative">
      {!envChecked && (
        <EnvironmentCheck onCheckComplete={() => setEnvChecked(true)} />
      )}

      <Sidebar />

      <div className="flex-1 flex flex-col gap-4 p-4 overflow-auto min-h-0">
        <Tabs defaultValue="radar" className="flex-1 flex flex-col min-h-0">
          <TabsList className="self-start">
            <TabsTrigger value="radar">{t('tabs.radar')}</TabsTrigger>
            <TabsTrigger value="scan">{t('tabs.scan')}</TabsTrigger>
          </TabsList>
          <TabsContent value="radar" className="flex-1 overflow-auto">
            <TrendRadarPanel />
          </TabsContent>
          <TabsContent value="scan" className="flex-1 overflow-auto">
            <CrawlerConfigPanel />
          </TabsContent>
        </Tabs>
      </div>

      <TerminalDialog />

      <Toaster
        position="top-right"
        toastOptions={{
          className: 'glass-panel font-mono text-cyber-text-primary',
          style: {
            fontFamily: 'JetBrains Mono, monospace',
          },
        }}
      />
    </div>
  )
}

export default App
