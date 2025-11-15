import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Leaf, Trees } from 'lucide-react'
import niamotoLogo from '@/assets/niamoto_logo.png'

interface UseCasesSectionProps {}

const useCases = [
  {
    title: 'Niamoto NC',
    icon: Trees,
    logo: niamotoLogo,
    description: 'Nouvelle-Calédonie',
    stats: {
      species: '1275',
      occurrences: '203,865',
      plots: '22',
      shapes: '89'
    },
    benefits: [
      '75% d\'endémisme NC',
      'Point chaud biodiversité mondial',
      'Interface grand public & chercheurs'
    ],
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10'
  },
  {
    title: 'Central African Plot Network',
    icon: Trees,
    description: 'Gabon - Cameroun',
    stats: {
      species: '1,234',
      occurrences: '45,000',
      plots: '265',
      shapes: '71'
    },
    benefits: [
      'Réseau parcelles Afrique Centrale',
      'Biomasse & dynamique forestière',
      'Données scientifiques ouvertes'
    ],
    color: 'text-amber-900',
    bgColor: 'bg-amber-900/10'
  },
  {
    title: 'Endemia',
    icon: Leaf,
    description: 'Nouvelle-Calédonie',
    stats: {
      species: '4658',
      occurrences: '175,537'
    },
    benefits: [
      '2696 espèces endémiques',
      'Observations participatives',
      'Liste Rouge & espèces protégées'
    ],
    color: 'text-lime-700',
    bgColor: 'bg-lime-700/10'
  }
]

export function UseCasesSection({}: UseCasesSectionProps) {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Instances déployées/en cours</h2>
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
                  {useCase.logo ? (
                    <img src={useCase.logo} alt={useCase.title} className="w-8 h-8 object-contain" />
                  ) : (
                    <Icon className={`w-6 h-6 ${useCase.color}`} />
                  )}
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
                  {useCase.stats.plots && (
                  <div className="text-center">
                    <div className="text-lg font-bold">{useCase.stats.plots}</div>
                    <p className="text-xs text-muted-foreground">Parcelles</p>
                  </div>
                  )}
                  {useCase.stats.shapes && (
                  <div className="text-center">
                    <div className="text-lg font-bold">{useCase.stats.shapes}</div>
                    <p className="text-xs text-muted-foreground">Formes</p>
                  </div>
                  )}
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
