import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const languages = [
  { code: 'vi-VN', label: 'VI' },
  { code: 'en-US', label: 'EN' },
  { code: 'zh-CN', label: '中文' },
]

function resolveLang(lng: string) {
  if (lng.startsWith('vi')) return 'vi-VN'
  if (lng.startsWith('zh')) return 'zh-CN'
  if (lng.startsWith('en')) return 'en-US'
  return 'vi-VN'
}

export function LanguageSwitch() {
  const { i18n } = useTranslation()
  const currentCode = resolveLang(i18n.language || 'vi-VN')
  const currentLang = languages.find((l) => l.code === currentCode) || languages[0]

  return (
    <Select value={currentCode} onValueChange={(lang) => i18n.changeLanguage(lang)}>
      <SelectTrigger className="w-20 h-7 text-xs font-mono border-cyber-border-subtle bg-cyber-bg-tertiary/50 hover:border-cyber-neon-cyan/50 transition-colors">
        <Globe className="w-3 h-3 mr-1 text-cyber-text-secondary" />
        <SelectValue>{currentLang.label}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {languages.map((lang) => (
          <SelectItem key={lang.code} value={lang.code} className="text-xs font-mono">
            {lang.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
