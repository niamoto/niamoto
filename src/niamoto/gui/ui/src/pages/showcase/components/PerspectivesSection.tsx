import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Brain,
  Sparkles,
  Globe,
  TrendingUp,
  ArrowRight,
  FlaskConical,
  BookOpen,
  Target
} from 'lucide-react'

export function PerspectivesSection() {
  const labsInterfaces = [
    {
      name: 'Bootstrap Wizard',
      description: 'Drag & drop → Configuration automatique',
      path: '/setup/bootstrap',
      features: ['Détection automatique', 'Génération de configs', 'Preview temps réel']
    },
    {
      name: 'Pipeline Editor',
      description: 'Éditeur visuel de flux',
      path: '/setup/pipeline',
      features: ['Nœuds intelligents', 'Suggestions contextuelles', 'Export YAML']
    },
    {
      name: 'Goal-Driven Page Builder',
      description: 'Approche inversée : page → config',
      path: '/demos/goal-driven',
      features: ['Conception visuelle', 'Génération automatique', 'Configuration sans YAML']
    }
  ]

  const inspirations = [
    {
      name: 'LIDA',
      org: 'Microsoft Research',
      description: 'Automatic Generation of Visualizations and Infographics using LLMs',
      url: 'https://github.com/microsoft/lida',
      paper: 'https://arxiv.org/abs/2303.02927'
    },
    {
      name: 'Data Formulator',
      org: 'Microsoft Research',
      description: 'AI-powered concept-driven data transformation',
      url: 'https://github.com/microsoft/data-formulator',
      paper: 'https://arxiv.org/html/2408.16119v2'
    }
  ]

  return (
    <div className="w-full max-w-6xl mx-auto space-y-16 py-12">
      {/* Hero Section */}
      <div className="text-center space-y-6">
        <Badge className="mb-4  dark:text-gray-800 border-none">
          <Sparkles className="w-3 h-3 mr-1" />
          Recherche & Développement
        </Badge>
        <h2 className="text-5xl font-bold  bg-clip-text">
          Perspectives & Évolutions
        </h2>
        <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
          Simplifier la configuration des pages écologiques grâce à des interfaces graphiques ergonomiques
        </p>
      </div>

      {/* 1. Le Défi : Complexité Croissante */}
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-full bg-gradient-to-br from-amber-200/30 to-orange-200/30">
            <Target className="w-8 h-8 text-amber-400" />
          </div>
          <div>
            <h3 className="text-3xl font-bold">Le Défi : Configuration Complexe</h3>
            <p className="text-muted-foreground">Besoin d'ergonomie pour la génération de pages</p>
          </div>
        </div>

        <Card className="border-2 border-amber-300/30">
          <CardHeader>
            <CardTitle>Constats</CardTitle>
            <CardDescription>
              La configuration actuelle devient complexe à mesure que le projet évolue
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-amber-400 mt-2 shrink-0" />
                <p className="text-sm text-muted-foreground">
                  <strong>Fichiers YAML manuels</strong> : Édition directe requise pour configurer les transformations et widgets
                </p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-amber-400 mt-2 shrink-0" />
                <p className="text-sm text-muted-foreground">
                  <strong>Paramètres nombreux</strong> : Chaque plugin a ses propres schémas et options
                </p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-amber-400 mt-2 shrink-0" />
                <p className="text-sm text-muted-foreground">
                  <strong>Cycle itératif long</strong> : Éditer YAML → Exécuter pipeline → Voir résultat → Recommencer
                </p>
              </div>
            </div>

            <div className="p-4 bg-amber-50/50 dark:bg-amber-950/10 border border-amber-200/50 dark:border-amber-900/30 rounded-lg mt-4">
              <p className="text-sm text-amber-700 dark:text-amber-200">
                <strong>Objectif :</strong> Créer des interfaces graphiques qui permettent de configurer et prévisualiser
                les pages en temps réel, sans éditer manuellement les fichiers de configuration.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 2. Interfaces de Test (Labs) */}
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-full bg-gradient-to-br from-teal-200/30 to-cyan-200/30">
            <FlaskConical className="w-8 h-8 text-teal-400" />
          </div>
          <div>
            <h3 className="text-3xl font-bold">Prototypes d'Interfaces</h3>
            <p className="text-muted-foreground">Interfaces de test dans la section Labs</p>
          </div>
        </div>

        <Card className="border-2">
          <CardHeader>
            <CardTitle>Prototypes Actuels</CardTitle>
            <CardDescription>
              Plusieurs interfaces de test sont déjà disponibles dans le menu Labs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {labsInterfaces.map((interface_item) => (
                <Card key={interface_item.name} className="border hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{interface_item.name}</CardTitle>
                      <Badge variant="outline" className="text-teal-400 border-teal-300">
                        <FlaskConical className="w-3 h-3 mr-1" />
                        Labs
                      </Badge>
                    </div>
                    <CardDescription className="text-sm">{interface_item.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                      {interface_item.features.map((feature, idx) => (
                        <li key={idx} className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <Button variant="outline" size="sm" className="w-full" asChild>
                      <a href={interface_item.path}>
                        Tester
                        <ArrowRight className="w-3 h-3 ml-2" />
                      </a>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="mt-6 p-4 bg-teal-50/50 dark:bg-teal-950/10 border border-teal-200/50 dark:border-teal-900/30 rounded-lg">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-teal-400 mt-0.5 shrink-0" />
                <div>
                  <h4 className="font-semibold text-teal-700 dark:text-teal-200">
                    Prototype à venir : Configuration de Page en Temps Réel
                  </h4>
                  <p className="text-sm text-teal-600 dark:text-teal-300 mt-1">
                    Une interface permettant de configurer une page taxon en temps réel, avec preview instantané
                    des widgets et de la mise en page, sans éditer manuellement les fichiers YAML.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. Exploration de l'Assistance ML */}
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-full bg-gradient-to-br from-sky-200/30 to-cyan-200/30">
            <Brain className="w-8 h-8 text-sky-400" />
          </div>
          <div>
            <h3 className="text-3xl font-bold">Exploration de l'Assistance ML</h3>
            <p className="text-muted-foreground">Recherche en cours, approche en évaluation</p>
          </div>
        </div>

        <Card className="border-2 border-sky-300/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-sky-400" />
              Potentiel du Machine Learning
            </CardTitle>
            <CardDescription>
              Dans le contexte d'interfaces ergonomiques, le ML pourrait assister l'utilisateur
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">
                Notre système combine extraction de features statistiques et détection de patterns sémantiques
                pour identifier automatiquement les types de colonnes dans vos données écologiques. Cette approche
                est encore en phase d'évaluation pour déterminer si elle peut réellement simplifier la configuration.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-sky-400 mt-2 shrink-0" />
                <p className="text-sm text-muted-foreground">
                  <strong>Détection de types</strong> : Random Forest avec features statistiques pour identifier diamètres, hauteurs, noms d'espèces, etc.
                </p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-sky-400 mt-2 shrink-0" />
                <p className="text-sm text-muted-foreground">
                  <strong>Suggestions contextuelles</strong> : Proposer automatiquement des widgets appropriés selon les types détectés
                </p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-sky-400 mt-2 shrink-0" />
                <p className="text-sm text-muted-foreground">
                  <strong>Simplification</strong> : Réduire le nombre de décisions manuelles nécessaires lors de la configuration
                </p>
              </div>
            </div>

            <div className="p-4 bg-sky-50/50 dark:bg-sky-950/10 border border-sky-200/50 dark:border-sky-900/30 rounded-lg">
              <p className="text-sm text-sky-700 dark:text-sky-200">
                <strong>État actuel :</strong> Modèle préliminaire en phase de test. L'objectif est d'évaluer si cette approche
                apporte réellement une valeur ajoutée ou si des solutions plus simples suffiraient.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 4. Inspirations Scientifiques */}
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-full bg-gradient-to-br from-green-200/30 to-emerald-200/30">
            <BookOpen className="w-8 h-8 text-green-400" />
          </div>
          <div>
            <h3 className="text-3xl font-bold">Inspirations</h3>
            <p className="text-muted-foreground">Travaux de recherche en visualisation automatique</p>
          </div>
        </div>

        <Card className="border-2">
          <CardHeader>
            <CardTitle>Projets de Recherche</CardTitle>
            <CardDescription>
              Travaux récents sur la génération automatique de visualisations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {inspirations.map((project) => (
                <Card key={project.name} className="border">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-lg">{project.name}</CardTitle>
                        <Badge variant="secondary" className="text-xs">
                          {project.org}
                        </Badge>
                      </div>
                    </div>
                    <CardDescription className="mt-2 text-sm">
                      {project.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start"
                      onClick={() => window.open(project.url, '_blank')}
                    >
                      <Globe className="w-3 h-3 mr-2" />
                      GitHub
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start"
                      onClick={() => window.open(project.paper, '_blank')}
                    >
                      <BookOpen className="w-3 h-3 mr-2" />
                      Paper
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="mt-6 p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">
                Ces projets explorent l'utilisation de LLMs et d'approches d'IA pour générer automatiquement
                des visualisations de données. Ils peuvent inspirer notre réflexion sur l'assistance
                à la configuration, tout en restant conscients des différences de contexte entre données
                tabulaires génériques et données écologiques spécifiques.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Scientific References */}
      <div className="pt-8 border-t space-y-3">
        <h4 className="text-sm font-semibold text-muted-foreground">Références Scientifiques</h4>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>
            • Hulsebos, M., et al. (2019). "Sherlock: A Deep Learning Approach to Semantic Data Type Detection". MIT
          </p>
          <p>
            • Zhang, D., et al. (2024). "Pythagoras: A GNN-based Approach for Table Column Type Prediction"
          </p>
          <p>
            • Koutras, C., et al. (2023). "GitTables: A Large-Scale Corpus of Relational Tables". arXiv:2106.07258
          </p>
        </div>
      </div>
    </div>
  )
}
