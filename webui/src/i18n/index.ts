import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import enCommon from './locales/en-US/common.json'
import enConfig from './locales/en-US/config.json'
import enTerminal from './locales/en-US/terminal.json'
import enData from './locales/en-US/data.json'
import enEnv from './locales/en-US/env.json'
import enTrend from './locales/en-US/trend.json'

import viCommon from './locales/vi-VN/common.json'
import viConfig from './locales/vi-VN/config.json'
import viTerminal from './locales/vi-VN/terminal.json'
import viData from './locales/vi-VN/data.json'
import viEnv from './locales/vi-VN/env.json'
import viTrend from './locales/vi-VN/trend.json'

const vi = {
  common: viCommon,
  config: viConfig,
  terminal: viTerminal,
  data: viData,
  env: viEnv,
  trend: viTrend,
}

const en = {
  common: enCommon,
  config: enConfig,
  terminal: enTerminal,
  data: enData,
  env: enEnv,
  trend: enTrend,
}

const resources = {
  'vi-VN': vi,
  vi,
  'en-US': en,
  en,
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'vi-VN',
    supportedLngs: ['vi-VN', 'vi', 'en-US', 'en'],
    defaultNS: 'common',
    interpolation: {
      escapeValue: false,
    },
    react: {
      useSuspense: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'mediacrawler_language',
    },
  })

export default i18n
