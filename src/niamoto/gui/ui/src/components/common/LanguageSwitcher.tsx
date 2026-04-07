import { useTranslation } from 'react-i18next';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Globe } from 'lucide-react';
import {
  applyUiLanguagePreference,
  getAppSettings,
  setAppSettings,
} from '@/shared/desktop/appSettings';

const languages = [
  { code: 'fr', name: 'FR', flag: '🇫🇷' },
  { code: 'en', name: 'EN', flag: '🇬🇧' },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const handleLanguageChange = async (value: string) => {
    const nextLanguage = value === 'fr' ? 'fr' : 'en';
    const currentSettings = await getAppSettings();
    await setAppSettings({
      ...currentSettings,
      ui_language: nextLanguage,
    });
    await applyUiLanguagePreference(nextLanguage);
  };

  return (
    <Select value={i18n.language.startsWith('fr') ? 'fr' : 'en'} onValueChange={handleLanguageChange}>
      <SelectTrigger className="w-[140px]">
        <Globe className="w-4 h-4 mr-2" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {languages.map((lang) => (
          <SelectItem key={lang.code} value={lang.code}>
            <span className="flex items-center gap-2">
              <span>{lang.flag}</span>
              <span>{lang.name}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
