import { Globe } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useLanguages } from "@/contexts/LanguageContext"

// Type alias matching backend LocalizedString
export type LocalizedString = string | Record<string, string>

interface LocalizedInputProps {
  /** Current value (string or localized dict) */
  value: LocalizedString | undefined
  /** Callback when value changes */
  onChange: (value: LocalizedString | undefined) => void
  /** Available languages for editing (uses LanguageContext if not provided) */
  languages?: string[]
  /** Default language (uses LanguageContext if not provided) */
  defaultLang?: string
  /** Placeholder text */
  placeholder?: string
  /** Whether to use textarea instead of input */
  multiline?: boolean
  /** Number of rows for textarea */
  rows?: number
  /** Additional className */
  className?: string
  /** Disabled state */
  disabled?: boolean
  /** Label for the field */
  label?: string
}

/**
 * LocalizedInput - A component for editing localized strings.
 *
 * Supports two modes:
 * 1. Simple mode: Single input for a plain string
 * 2. Localized mode: Multiple inputs for each language
 *
 * Users can toggle between modes using the globe button.
 *
 * Languages are automatically read from LanguageContext if not explicitly provided.
 */
export function LocalizedInput({
  value,
  onChange,
  languages: languagesProp,
  defaultLang: defaultLangProp,
  placeholder,
  multiline = false,
  rows = 3,
  className,
  disabled = false,
  label,
}: LocalizedInputProps) {
  const { t } = useTranslation("common")

  // Use context values as defaults, allow props to override
  const languageContext = useLanguages()
  const languages = languagesProp ?? languageContext.languages
  const defaultLang = defaultLangProp ?? languageContext.defaultLang

  // Determine if current value is localized
  const isLocalized = typeof value === "object" && value !== null

  // Convert value to a working state
  const getStringValue = (): string => {
    if (value === undefined || value === null) return ""
    if (typeof value === "string") return value
    // Return value for default language, or first available
    return value[defaultLang] || Object.values(value)[0] || ""
  }

  const getLocalizedValue = (): Record<string, string> => {
    if (typeof value === "string") {
      return { [defaultLang]: value }
    }
    if (typeof value === "object" && value !== null) {
      return value
    }
    return { [defaultLang]: "" }
  }

  // Toggle to localized mode
  const enableLocalized = () => {
    const currentValue = getStringValue()
    const newValue: Record<string, string> = {}
    languages.forEach((lang) => {
      newValue[lang] = lang === defaultLang ? currentValue : ""
    })
    onChange(newValue)
  }

  // Toggle to simple mode
  const disableLocalized = () => {
    const localizedValue = getLocalizedValue()
    // Keep value from default language
    const simpleValue = localizedValue[defaultLang] || Object.values(localizedValue)[0] || ""
    onChange(simpleValue || undefined)
  }

  // Update a specific language value
  const updateLanguageValue = (lang: string, newValue: string) => {
    const current = getLocalizedValue()
    const updated = { ...current, [lang]: newValue }

    // Check if all values are empty
    const allEmpty = Object.values(updated).every((v) => !v)
    if (allEmpty) {
      onChange(undefined)
    } else {
      onChange(updated)
    }
  }

  // Update simple string value
  const updateSimpleValue = (newValue: string) => {
    onChange(newValue || undefined)
  }

  const InputComponent = multiline ? Textarea : Input

  // Simple mode
  if (!isLocalized) {
    return (
      <div className={cn("space-y-1.5", className)}>
        {label && (
          <label className="text-sm font-medium text-muted-foreground">
            {label}
          </label>
        )}
        <div className="flex gap-2">
          <InputComponent
            value={getStringValue()}
            onChange={(e) => updateSimpleValue(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            className="flex-1"
            {...(multiline ? { rows } : {})}
          />
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={enableLocalized}
                  disabled={disabled}
                  className="shrink-0"
                >
                  <Globe className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t("i18n.enableMultilingual", "Enable multilingual content")}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    )
  }

  // Localized mode
  const localizedValue = getLocalizedValue()

  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-muted-foreground">
            {label}
          </label>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              <Globe className="h-3 w-3 mr-1" />
              {t("i18n.multilingual", "Multilingual")}
            </Badge>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={disableLocalized}
                    disabled={disabled}
                    className="h-6 px-2 text-xs"
                  >
                    {t("i18n.simplify", "Simplify")}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t("i18n.simplifyDescription", "Remove translations and keep only one value")}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      )}
      <div className="space-y-2 rounded-md border p-3 bg-muted/30">
        {languages.map((lang) => (
          <div key={lang} className="flex items-start gap-2">
            <Badge
              variant={lang === defaultLang ? "default" : "outline"}
              className="w-8 justify-center shrink-0 mt-2"
            >
              {lang.toUpperCase()}
            </Badge>
            <InputComponent
              value={localizedValue[lang] || ""}
              onChange={(e) => updateLanguageValue(lang, e.target.value)}
              placeholder={`${placeholder || ""} (${t(`languages.${lang}`, lang)})`}
              disabled={disabled}
              className="flex-1"
              {...(multiline ? { rows } : {})}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Helper hook to work with LocalizedString values.
 * Uses LanguageContext for default language if not provided.
 */
export function useLocalizedString(
  value: LocalizedString | undefined,
  defaultLangProp?: string
) {
  const languageContext = useLanguages()
  const defaultLang = defaultLangProp ?? languageContext.defaultLang

  const isLocalized = typeof value === "object" && value !== null

  const resolve = (lang?: string): string => {
    if (value === undefined || value === null) return ""
    if (typeof value === "string") return value
    const targetLang = lang || defaultLang
    return value[targetLang] || value[defaultLang] || Object.values(value)[0] || ""
  }

  const getAllTranslations = (): Record<string, string> => {
    if (typeof value === "string") {
      return { [defaultLang]: value }
    }
    if (typeof value === "object" && value !== null) {
      return value
    }
    return {}
  }

  return {
    isLocalized,
    resolve,
    getAllTranslations,
    raw: value,
  }
}

export { LocalizedInput as default }
