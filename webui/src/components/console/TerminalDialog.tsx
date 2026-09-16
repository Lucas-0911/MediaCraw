import { useTranslation } from 'react-i18next'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Terminal } from '@/components/console/Terminal'
import { useLogWebSocket } from '@/hooks/useWebSocket'
import { useCrawlerStore } from '@/store/crawlerStore'

export function TerminalDialog() {
  const { t } = useTranslation('terminal')
  const consoleOpen = useCrawlerStore((state) => state.consoleOpen)
  const setConsoleOpen = useCrawlerStore((state) => state.setConsoleOpen)

  useLogWebSocket()

  return (
    <Dialog open={consoleOpen} onOpenChange={setConsoleOpen}>
      <DialogContent className="max-w-5xl w-[92vw] h-[80vh] p-0 gap-0 overflow-hidden border-cyber-border-subtle bg-transparent shadow-none [&>button]:hidden">
        <DialogTitle className="sr-only">{t('header.title')}</DialogTitle>
        <Terminal onClose={() => setConsoleOpen(false)} />
      </DialogContent>
    </Dialog>
  )
}
