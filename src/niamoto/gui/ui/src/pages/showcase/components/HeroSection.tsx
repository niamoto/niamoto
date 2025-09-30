import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowRight, Workflow, Package, Globe, GitBranch, ExternalLink } from 'lucide-react'
import { useProgressiveCounter } from '@/hooks/useProgressiveCounter'
import { useShowcaseStore } from '@/stores/showcaseStore'
import niamotoLogo from '@/assets/niamoto_logo.png'

interface HeroSectionProps {
  configLoaded?: boolean
}

export function HeroSection({ configLoaded }: HeroSectionProps) {
  // Récupérer tous les plugins depuis le store partagé
  const { plugins, loadPlugins } = useShowcaseStore()
  const totalPlugins = plugins ? plugins.length : 55

  // Charger les plugins au montage
  useEffect(() => {
    loadPlugins()
  }, [])

  const stepsCounter = useProgressiveCounter(4, 1000)
  const pluginsCounter = useProgressiveCounter(totalPlugins, 2000)
  const sitesCounter = useProgressiveCounter(1, 500)
  const [showLogo, setShowLogo] = useState(false)

  useEffect(() => {
    setShowLogo(true)
  }, [])

  const scrollToNext = () => {
    const nextSection = document.getElementById('architecture')
    nextSection?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="w-full flex flex-col items-center justify-center text-center space-y-8 animate-fadeIn">
      {/* Logo Animation */}
      <div className={`transition-all duration-1000 ${showLogo ? 'scale-100 opacity-100' : 'scale-50 opacity-0'}`}>
        <img
          src={niamotoLogo}
          alt="Niamoto"
          className="w-32 h-32 mx-auto animate-pulse"
        />
      </div>

      {/* Main Title */}
      <div className="space-y-4">
        <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
          Niamoto
        </h1>
        <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl">
          Plateforme de valorisation des données écologiques pour la recherche
        </p>
      </div>

      {/* Key Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl w-full">
        <div className="space-y-2 p-6 rounded-lg bg-card/50 backdrop-blur hover:bg-card/70 transition-all cursor-default">
          <div className="text-4xl font-bold text-primary">{stepsCounter.value}</div>
          <div className="text-sm text-muted-foreground">Étapes du pipeline</div>
          <Workflow className="w-8 h-8 mx-auto text-primary/60" />
        </div>
        <div className="space-y-2 p-6 rounded-lg bg-card/50 backdrop-blur hover:bg-card/70 transition-all cursor-default">
          <div className="text-4xl font-bold text-primary">{pluginsCounter.value}</div>
          <div className="text-sm text-muted-foreground">Plugins disponibles</div>
          <Package className="w-8 h-8 mx-auto text-primary/60" />
        </div>
        <div className="space-y-2 p-6 rounded-lg bg-card/50 backdrop-blur hover:bg-card/70 transition-all cursor-pointer"
             onClick={() => window.open('https://niamoto.github.io/niamoto-static-site/', '_blank')}>
          <div className="text-4xl font-bold text-primary">{sitesCounter.value}</div>
          <div className="text-sm text-muted-foreground flex items-center justify-center gap-1">
            Niamoto 2.0 <ExternalLink className="w-3 h-3" />
          </div>
          <Globe className="w-8 h-8 mx-auto text-primary/60" />
        </div>
      </div>

      {/* Features Badges */}
      <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
        <Badge variant="secondary" className="flex items-center gap-1">
          <GitBranch className="w-3 h-3" />
          Open Source
        </Badge>
        <Badge variant="secondary" className="flex items-center gap-1">
          <ExternalLink className="w-3 h-3" />
          Site Statique
        </Badge>
        <Badge variant="secondary">Pipeline Reproductible</Badge>
        <Badge variant="secondary">API REST</Badge>
      </div>

      {/* Tagline */}
      <div className="text-lg text-muted-foreground italic max-w-2xl">
        "Transformez vos données CSV en site web avec analyses statistiques,
         cartes interactives et visualisations dynamiques"
      </div>

      {/* CTA Buttons */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button
          size="lg"
          onClick={scrollToNext}
          className="group"
        >
          Découvrir la démo
          <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
        </Button>
        <Button
          size="lg"
          variant="outline"
          onClick={() => window.open('https://github.com/niamoto/niamoto', '_blank')}
        >
          <GitBranch className="mr-2 h-4 w-4" />
          Voir sur GitHub
        </Button>
      </div>

      {/* Config Status */}
      {configLoaded && (
        <div className="absolute top-4 right-4">
          <Badge variant="outline" className="bg-green-500/10">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />
            Configuration chargée
          </Badge>
        </div>
      )}

      {/* Scroll Indicator */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
        <svg
          className="w-6 h-6 text-muted-foreground"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
        </svg>
      </div>
    </div>
  )
}
