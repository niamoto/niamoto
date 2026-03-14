import { useState, useCallback, useEffect } from 'react'
import { Input } from '@/components/ui/input'

interface NumberArrayInputProps {
  value: number[] | undefined
  onChange: (value: number[] | undefined) => void
  placeholder?: string
  className?: string
}

/**
 * Input for number arrays like range_y: [0, 50]
 * Uses local state and only parses on blur to allow natural typing
 */
export function NumberArrayInput({
  value,
  onChange,
  placeholder = "ex: 0, 100",
  className = "h-8"
}: NumberArrayInputProps) {
  // Local state for the text input
  const [text, setText] = useState(() =>
    Array.isArray(value) ? value.join(', ') : ''
  )

  // Sync from external value changes (when not focused)
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    if (!isFocused) {
      const newText = Array.isArray(value) ? value.join(', ') : ''
      if (newText !== text) {
        setText(newText)
      }
    }
  }, [value, isFocused])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setText(e.target.value)
  }, [])

  const handleBlur = useCallback(() => {
    setIsFocused(false)
    // Parse on blur
    const values = text
      .split(',')
      .map(s => parseFloat(s.trim()))
      .filter(n => !isNaN(n))
    onChange(values.length > 0 ? values : undefined)
  }, [text, onChange])

  const handleFocus = useCallback(() => {
    setIsFocused(true)
  }, [])

  return (
    <Input
      className={className}
      value={text}
      onChange={handleChange}
      onBlur={handleBlur}
      onFocus={handleFocus}
      placeholder={placeholder}
    />
  )
}
