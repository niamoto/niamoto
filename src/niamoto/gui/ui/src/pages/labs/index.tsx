/**
 * Labs - UX Mockups Overview
 * Route: /labs
 *
 * Page d'accueil pour les mockups UX permettant de visualiser
 * les différentes options d'interface avant implémentation.
 */

import { Link } from 'react-router-dom'
import {
  FlaskConical,
  ListCollapse,
  Combine,
  ArrowRight,
  CheckCircle2,
  Circle,
  Star,
  PaintBucket,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface MockupOption {
  id: string
  title: string
  description: string
  path: string
  icon: React.ComponentType<{ className?: string }>
  status: 'recommended' | 'alternative' | 'experimental' | 'new'
  features: string[]
}

const mockupOptions: MockupOption[] = [
  {
    id: 'hybrid',
    title: 'Option A: Hybride',
    description:
      '3 onglets (Sources/Contenu/Index) avec panneau contextuel. Sans sélection = aperçu layout, avec sélection = détails widget.',
    path: '/labs/mockup-widgets-hybrid',
    icon: Combine,
    status: 'recommended',
    features: [
      'Structure simplifiée à 3 onglets',
      'Aperçu layout quand aucun widget sélectionné',
      'Détails widget quand sélectionné',
      'Modal pour ajouter des widgets',
    ],
  },
  {
    id: 'canvas',
    title: 'Option B: Canvas Builder',
    description:
      'Interface WYSIWYG type Figma/Squarespace. Canvas central avec palette contextuelle basée sur les données disponibles.',
    path: '/labs/mockup-canvas-builder',
    icon: PaintBucket,
    status: 'new',
    features: [
      'Paradigme design-first (WYSIWYG)',
      'Palette contextuelle par champ de données',
      'Suggestions de widgets adaptées au type',
      'Détection de patterns multi-champs',
    ],
  },
  {
    id: 'inline',
    title: 'Option C: Expansion inline',
    description:
      '4 onglets avec expansion inline (accordion). Clic sur un widget = expansion dans la liste pour voir preview et édition.',
    path: '/labs/mockup-widgets-inline',
    icon: ListCollapse,
    status: 'experimental',
    features: [
      'Pas de panneau latéral séparé',
      'Expansion accordéon dans la liste',
      'Tout visible dans une seule colonne',
      'Navigation plus linéaire',
    ],
  },
]

const statusConfig = {
  recommended: { label: 'Recommandé', variant: 'default' as const, className: 'bg-green-600' },
  alternative: { label: 'Alternative', variant: 'secondary' as const, className: '' },
  experimental: { label: 'Expérimental', variant: 'outline' as const, className: '' },
  new: { label: 'Nouveau', variant: 'default' as const, className: 'bg-blue-600' },
}

export default function LabsIndex() {
  return (
    <div className="h-full overflow-auto">
      <div className="container max-w-5xl py-8 px-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <FlaskConical className="h-8 w-8 text-purple-600" />
            <h1 className="text-3xl font-bold">Labs - Prototypes UX</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Explorez les différentes options d'interface pour l'onglet Widgets.
            Ces mockups interactifs permettent de comparer les approches avant l'implémentation finale.
          </p>
        </div>

        {/* Context */}
        <Card className="mb-8 border-amber-200 bg-amber-50 dark:bg-amber-950/20">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Contexte du problème</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <p>
              L'interface actuelle des widgets présente plusieurs problèmes d'utilisabilité :
            </p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>Triple chemin pour configurer un widget (Colonnes/Expert/Configurés)</li>
              <li>Nom "Colonnes" confus - suggère des colonnes de données</li>
              <li>Boutons "Sauvegarder" multiples avec workflows différents</li>
              <li>Réorganisation possible à deux endroits différents</li>
            </ul>
          </CardContent>
        </Card>

        {/* Options Grid */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold mb-4">Options proposées</h2>

          {mockupOptions.map((option) => {
            const Icon = option.icon
            const status = statusConfig[option.status]

            return (
              <Card
                key={option.id}
                className={`transition-all hover:shadow-md ${
                  option.status === 'recommended' ? 'ring-2 ring-green-500/50' : ''
                } ${option.status === 'new' ? 'ring-2 ring-blue-500/50' : ''}`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-2 rounded-lg ${
                          option.status === 'recommended'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30'
                            : option.status === 'new'
                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30'
                              : 'bg-muted'
                        }`}
                      >
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{option.title}</CardTitle>
                        <Badge className={status.className} variant={status.variant}>
                          {status.label}
                        </Badge>
                      </div>
                    </div>
                    <Button asChild>
                      <Link to={option.path}>
                        Voir le mockup
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                  <CardDescription className="mt-2">{option.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-2">
                    {option.features.map((feature, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm">
                        {option.status === 'recommended' ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                        ) : option.status === 'new' ? (
                          <Star className="h-4 w-4 text-blue-600 flex-shrink-0" />
                        ) : (
                          <Circle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        )}
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Decision Section */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Prochaines étapes</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
              <li>Explorer chaque mockup pour comprendre l'expérience utilisateur</li>
              <li>Tester les interactions principales (ajout, édition, suppression)</li>
              <li>Noter les points positifs et négatifs de chaque approche</li>
              <li>Choisir l'option à implémenter</li>
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
