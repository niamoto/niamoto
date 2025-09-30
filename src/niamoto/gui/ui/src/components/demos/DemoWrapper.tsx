import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Home, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface DemoOption {
  id: string
  name: string
  path: string
  description: string
  recommended?: boolean
}

const demoOptions: DemoOption[] = [
  {
    id: 'entity-centric',
    name: 'Entity-Centric',
    path: '/demos/entity-centric',
    description: 'Gestion dynamique des entités avec génération YAML en temps réel',
    recommended: true
  },
  {
    id: 'pipeline-visual',
    name: 'Pipeline Visual',
    path: '/demos/pipeline-visual',
    description: 'Éditeur visuel de pipeline avec vue flow des dépendances'
  },
  {
    id: 'wizard-form',
    name: 'Wizard & Forms',
    path: '/demos/wizard-form',
    description: 'Configuration guidée avec formulaires et validation progressive'
  }
]

interface DemoWrapperProps {
  currentDemo: string
  children: ReactNode
}

export function DemoWrapper({ currentDemo, children }: DemoWrapperProps) {
  const navigate = useNavigate()

  const currentIndex = demoOptions.findIndex(d => d.id === currentDemo)
  const currentOption = demoOptions[currentIndex]
  const prevOption = currentIndex > 0 ? demoOptions[currentIndex - 1] : null
  const nextOption = currentIndex < demoOptions.length - 1 ? demoOptions[currentIndex + 1] : null

  return (
    <div className="min-h-screen bg-background">
      {/* Header Navigation */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/transform')}
              >
                <Home className="h-4 w-4" />
              </Button>

              <div className="flex items-center gap-2">
                <h1 className="text-lg font-semibold">
                  Démo: {currentOption?.name}
                </h1>
                {currentOption?.recommended && (
                  <Badge variant="default" className="ml-2">
                    Recommandé
                  </Badge>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <Info className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p>{currentOption?.description}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => prevOption && navigate(prevOption.path)}
                  disabled={!prevOption}
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  {prevOption?.name || 'Précédent'}
                </Button>

                <Badge variant="secondary" className="mx-2">
                  {currentIndex + 1} / {demoOptions.length}
                </Badge>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => nextOption && navigate(nextOption.path)}
                  disabled={!nextOption}
                >
                  {nextOption?.name || 'Suivant'}
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Demo Selector */}
      <div className="border-b bg-muted/50">
        <div className="container mx-auto px-4 py-2">
          <div className="flex gap-2 overflow-x-auto">
            {demoOptions.map((option) => (
              <Button
                key={option.id}
                variant={option.id === currentDemo ? 'default' : 'ghost'}
                size="sm"
                onClick={() => navigate(option.path)}
                className="whitespace-nowrap"
              >
                {option.name}
                {option.recommended && (
                  <Badge variant="secondary" className="ml-2">
                    ⭐
                  </Badge>
                )}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {children}
      </div>
    </div>
  )
}
