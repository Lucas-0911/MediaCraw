import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

const languages = [
  { code: 'vi-VN', label: 'VI' },
  { code: 'en-US', label: 'EN' },
]

function resolveLang(lng: string) {
  if (lng.startsWith('en')) return 'en-US'
  return 'vi-VN'
}

export function LanguageSwitch() {
  const { i18n } = useTranslation()
  const currentCode = resolveLang(i18n.resolvedLanguage || i18n.language || 'vi-VN')

  const switchTo = (lang: string) => {
    void i18n.changeLanguage(lang)
    localStorage.setItem('mediacrawler_language', lang)
  }

  return (
    <div className="flex items-center gap-1">
      <Globe className="w-3 h-3 text-cyber-text-secondary" />
      <div className="flex items-center rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/50 overflow-hidden">
        {languages.map((lang) => (
          <button
            key={lang.code}
            type="button"
            onClick={() => switchTo(lang.code)}
            className={cn(
              'h-7 px-2 text-[10px] font-mono transition-colors',
              currentCode === lang.code
                ? 'bg-cyber-neon-cyan/20 text-cyber-neon-cyan'
                : 'text-cyber-text-secondary hover:text-cyber-text-primary hover:bg-cyber-bg-tertiary'
            )}
          >
            {lang.label}
          </button>
        ))}
      </div>
    </div>
  )
}
