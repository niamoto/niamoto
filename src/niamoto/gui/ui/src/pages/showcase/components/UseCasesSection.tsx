import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Building2, Trees, Users } from 'lucide-react'

interface UseCasesSectionProps {}

const useCases = [
  {
    title: 'Institut de Recherche',
    icon: Building2,
    description: 'IRD Nouvelle-Calédonie',
    stats: {
      species: '3,456',
      occurrences: '125,000',
      plots: '450'
    },
    benefits: [
      'Base de données centralisée',
      'Publications automatisées',
      'Partage avec la communauté'
    ],
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10'
  },
  {
    title: 'Gestion Provinciale',
    icon: Trees,
    description: 'Province Sud - Biodiversité',
    stats: {
      species: '1,234',
      occurrences: '45,000',
      plots: '180'
    },
    benefits: [
      'Suivi des espèces protégées',
      'Cartographie interactive',
      'Rapports réglementaires'
    ],
    color: 'text-green-500',
    bgColor: 'bg-green-500/10'
  },
  {
    title: 'Association',
    icon: Users,
    description: 'WWF Nouvelle-Calédonie',
    stats: {
      species: '890',
      occurrences: '23,000',
      plots: '120'
    },
    benefits: [
      'Sensibilisation du public',
      'Données open source',
      'Collaboration citoyenne'
    ],
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10'
  }
]

export function UseCasesSection({}: UseCasesSectionProps) {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Cas d'usage réels</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Niamoto est utilisé par des organisations variées pour gérer leurs données écologiques
        </p>
      </div>

      {/* Use Cases Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {useCases.map((useCase, idx) => {
          const Icon = useCase.icon
          return (
            <Card key={idx} className="relative overflow-hidden">
              <div className={`absolute top-0 right-0 w-32 h-32 ${useCase.bgColor} rounded-full blur-3xl opacity-20`} />
              <CardHeader>
                <div className={`w-12 h-12 rounded-lg ${useCase.bgColor} flex items-center justify-center mb-4`}>
                  <Icon className={`w-6 h-6 ${useCase.color}`} />
                </div>
                <CardTitle>{useCase.title}</CardTitle>
                <CardDescription>{useCase.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Statistics */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center">
                    <div className="text-lg font-bold">{useCase.stats.species}</div>
                    <p className="text-xs text-muted-foreground">Espèces</p>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold">{useCase.stats.occurrences}</div>
                    <p className="text-xs text-muted-foreground">Occurrences</p>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold">{useCase.stats.plots}</div>
                    <p className="text-xs text-muted-foreground">Parcelles</p>
                  </div>
                </div>

                {/* Benefits */}
                <div className="space-y-2 pt-4 border-t">
                  {useCase.benefits.map((benefit, bidx) => (
                    <div key={bidx} className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${useCase.bgColor}`} />
                      <span className="text-sm">{benefit}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
