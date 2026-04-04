import { useTranslation } from 'react-i18next'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Bug, Lightbulb, HelpCircle } from 'lucide-react'
import type { FeedbackType } from '../types'

interface FeedbackTypeSelectorProps {
  value: FeedbackType
  onChange: (type: FeedbackType) => void
  disabled?: boolean
}

const types = [
  { value: 'bug' as const, icon: Bug, labelKey: 'type_bug' },
  { value: 'suggestion' as const, icon: Lightbulb, labelKey: 'type_suggestion' },
  { value: 'question' as const, icon: HelpCircle, labelKey: 'type_question' },
]

export function FeedbackTypeSelector({ value, onChange, disabled }: FeedbackTypeSelectorProps) {
  const { t } = useTranslation('feedback')

  return (
    <ToggleGroup
      type="single"
      value={value}
      onValueChange={(v) => {
        if (v) onChange(v as FeedbackType)
      }}
      className="justify-start"
    >
      {types.map(({ value: typeValue, icon: Icon, labelKey }) => (
        <ToggleGroupItem
          key={typeValue}
          value={typeValue}
          disabled={disabled}
          className="gap-1.5 text-xs"
          aria-label={t(labelKey)}
        >
          <Icon className="h-3.5 w-3.5" />
          {t(labelKey)}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  )
}
