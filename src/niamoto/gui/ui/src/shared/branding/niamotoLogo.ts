import niamotoLogo from '@/assets/niamoto_logo.png'
import niamotoLogoDark from '@/assets/niamoto_logo_dark.png'

export function getNiamotoLogoSrc(mode: 'light' | 'dark') {
  return mode === 'dark' ? niamotoLogoDark : niamotoLogo
}
