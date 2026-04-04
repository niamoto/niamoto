import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { ImageOff } from 'lucide-react'

interface ScreenshotPreviewProps {
  screenshot: Blob | null
  error: boolean
  isCapturing: boolean
  included: boolean
  onIncludedChange: (included: boolean) => void
}

export function ScreenshotPreview({
  screenshot,
  error,
  isCapturing,
  included,
  onIncludedChange,
}: ScreenshotPreviewProps) {
  const { t } = useTranslation('feedback')

  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!screenshot) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(screenshot)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [screenshot])

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Checkbox
          id="include-screenshot"
          checked={included}
          onCheckedChange={(checked) => onIncludedChange(checked === true)}
          disabled={isCapturing || (!screenshot && !error)}
        />
        <Label htmlFor="include-screenshot" className="text-sm cursor-pointer">
          {t('screenshot_label')}
        </Label>
      </div>

      {isCapturing && (
        <div className="h-24 w-40 animate-pulse rounded-theme-sm bg-muted" />
      )}

      {!isCapturing && error && (
        <div className="flex h-24 w-40 items-center justify-center rounded-theme-sm bg-muted text-muted-foreground">
          <div className="flex flex-col items-center gap-1">
            <ImageOff className="h-5 w-5" />
            <span className="text-xs">{t('screenshot_unavailable')}</span>
          </div>
        </div>
      )}

      {!isCapturing && previewUrl && included && (
        <img
          src={previewUrl}
          alt="Screenshot preview"
          className="h-24 w-auto rounded-theme-sm border object-cover"
        />
      )}
    </div>
  )
}
