import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Database,
  FileCode,
  Settings,
  Package,
  Layers,
  Upload,
  Download,
  Rocket,
  Code,
  BookOpen,
  ChevronDown,
  ChevronUp
} from 'lucide-react'

interface ApiModule {
  name: string
  path: string
  icon: React.ReactNode
  description: string
  endpoints: number
  examples: string[]
}

const apiModules: ApiModule[] = [
  {
    name: 'Configuration',
    path: '/api/config',
    icon: <Settings className="w-5 h-5" />,
    description: 'Gestion des fichiers de configuration YAML (import.yml, transform.yml, export.yml)',
    endpoints: 6,
    examples: ['Lecture/écriture configs', 'Validation', 'Backups et restauration']
  },
  {
    name: 'Plugins',
    path: '/api/plugins',
    icon: <Package className="w-5 h-5" />,
    description: 'Découverte et introspection des 60+ plugins enregistrés',
    endpoints: 6,
    examples: ['Liste par type/catégorie', 'Schémas de configuration', 'Vérification compatibilité']
  },
  {
    name: 'Data Explorer',
    path: '/api/data',
    icon: <Database className="w-5 h-5" />,
    description: 'Exploration et requêtage des données de la base SQLite',
    endpoints: 4,
    examples: ['Requêtes SQL personnalisées', 'Inspection colonnes', 'Prévisualisation enrichissements']
  },
  {
    name: 'Entities',
    path: '/api/entities',
    icon: <Layers className="w-5 h-5" />,
    description: 'Accès aux entités (taxons, parcelles, zones) avec leurs widgets et relations',
    endpoints: 4,
    examples: ['Liste entités par groupe', 'Détails avec widgets', 'Relations hiérarchiques']
  },
  {
    name: 'Transform',
    path: '/api/transform',
    icon: <Rocket className="w-5 h-5" />,
    description: 'Exécution des transformations de données avec gestion de jobs asynchrones',
    endpoints: 6,
    examples: ['Lancement transformations', 'Suivi progression', 'Métriques et résultats']
  },
  {
    name: 'Imports',
    path: '/api/imports',
    icon: <Upload className="w-5 h-5" />,
    description: 'Import de données depuis CSV, Excel, JSON, GeoJSON, Shapefile',
    endpoints: 9,
    examples: ['Validation fichiers', 'Détection champs', 'Import avec mapping']
  },
  {
    name: 'Export',
    path: '/api/export',
    icon: <Download className="w-5 h-5" />,
    description: 'Génération de sites statiques, API JSON, Darwin Core Archives',
    endpoints: 7,
    examples: ['Lancement exports', 'Métriques de génération', 'Configuration cibles']
  },
  {
    name: 'Bootstrap',
    path: '/api',
    icon: <Rocket className="w-5 h-5" />,
    description: 'Analyse de fichiers et génération automatique de configurations',
    endpoints: 5,
    examples: ['Analyse structure fichiers', 'Génération configs', 'Diagnostic projet']
  },
  {
    name: 'Database',
    path: '/api/database',
    icon: <Database className="w-5 h-5" />,
    description: 'Introspection du schéma de base de données et statistiques',
    endpoints: 4,
    examples: ['Schéma complet', 'Aperçu tables', 'Statistiques']
  },
  {
    name: 'Files',
    path: '/api/files',
    icon: <FileCode className="w-5 h-5" />,
    description: 'Navigation système de fichiers, analyse et accès aux exports',
    endpoints: 7,
    examples: ['Parcours répertoires', 'Analyse fichiers CSV/JSON', 'Lecture exports']
  }
]

const codeExamples = {
  curl: `# Récupérer un taxon spécifique
curl http://localhost:8080/api/entities/entity/taxon/1

# Lancer une transformation
curl -X POST http://localhost:8080/api/transform/execute \\
  -H "Content-Type: application/json" \\
  -d '{"config_path": "config/transform.yml"}'

# Lister les exports générés
curl http://localhost:8080/api/files/exports/list`,

  python: `import requests

# Récupérer un taxon avec ses widgets
response = requests.get(
    "http://localhost:8080/api/entities/entity/taxon/1"
)
taxon = response.json()

# Exécuter un export
response = requests.post(
    "http://localhost:8080/api/export/execute",
    json={"config_path": "config/export.yml"}
)
job_id = response.json()["job_id"]

# Suivre la progression
status = requests.get(
    f"http://localhost:8080/api/export/status/{job_id}"
).json()`,

  javascript: `// Récupérer un taxon avec fetch
const taxon = await fetch(
  'http://localhost:8080/api/entities/entity/taxon/1'
).then(r => r.json())

// Lancer une transformation
const job = await fetch(
  'http://localhost:8080/api/transform/execute',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      config_path: 'config/transform.yml'
    })
  }
).then(r => r.json())

// Suivre la progression
const status = await fetch(
  \`http://localhost:8080/api/transform/status/\${job.job_id}\`
).then(r => r.json())`
}

export function ApiDocs() {
  const [showOverview, setShowOverview] = useState(true)

  return (
    <div className="h-full w-full flex flex-col overflow-auto">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold">API Documentation</h1>
        <p className="text-sm text-muted-foreground mt-1">
          API REST complète pour automatisation et intégration externe
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Vue d'ensemble */}
        <Card>
          <CardHeader className="cursor-pointer" onClick={() => setShowOverview(!showOverview)}>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5" />
                  Vue d'ensemble
                </CardTitle>
                <CardDescription>
                  57 endpoints répartis en 10 modules pour contrôler Niamoto
                </CardDescription>
              </div>
              {showOverview ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </div>
          </CardHeader>
          {showOverview && (
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {apiModules.map((module) => (
                  <Card key={module.name}>
                    <CardContent className="pt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {module.icon}
                          <h3 className="font-semibold text-sm">{module.name}</h3>
                        </div>
                        <Badge variant="secondary">{module.endpoints} endpoints</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{module.description}</p>
                      <div className="pt-2 space-y-1">
                        {module.examples.map((example, idx) => (
                          <div key={idx} className="text-xs flex items-center gap-2">
                            <div className="w-1 h-1 rounded-full bg-primary" />
                            <span className="text-muted-foreground">{example}</span>
                          </div>
                        ))}
                      </div>
                      <code className="text-xs bg-muted px-2 py-1 rounded block mt-2">
                        {module.path}
                      </code>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Exemples de code */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="w-5 h-5" />
              Exemples d'utilisation
            </CardTitle>
            <CardDescription>
              Intégrez Niamoto dans vos applications et scripts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="curl" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="curl">cURL</TabsTrigger>
                <TabsTrigger value="python">Python</TabsTrigger>
                <TabsTrigger value="javascript">JavaScript</TabsTrigger>
              </TabsList>
              <TabsContent value="curl" className="mt-4">
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                  <code>{codeExamples.curl}</code>
                </pre>
              </TabsContent>
              <TabsContent value="python" className="mt-4">
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                  <code>{codeExamples.python}</code>
                </pre>
              </TabsContent>
              <TabsContent value="javascript" className="mt-4">
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                  <code>{codeExamples.javascript}</code>
                </pre>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Cas d'usage */}
        <Card>
          <CardHeader>
            <CardTitle>Cas d'usage</CardTitle>
            <CardDescription>
              Exemples d'intégration avec l'API Niamoto
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Automatisation</h4>
                <p className="text-xs text-muted-foreground">
                  Scripts d'import/export réguliers, déclenchement de transformations, génération de sites
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Applications tierces</h4>
                <p className="text-xs text-muted-foreground">
                  Sites web personnalisés, applications mobiles, tableaux de bord utilisant les données Niamoto
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Intégration SIG</h4>
                <p className="text-xs text-muted-foreground">
                  Connexion avec QGIS, ArcGIS via requêtes API pour récupérer données géographiques
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Workflows scientifiques</h4>
                <p className="text-xs text-muted-foreground">
                  Intégration dans pipelines R/Python pour analyses statistiques et génération de rapports
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Lien vers Swagger */}
        <Card>
          <CardHeader>
            <CardTitle>Documentation interactive (Swagger UI)</CardTitle>
            <CardDescription>
              Explorez et testez tous les endpoints directement depuis votre navigateur
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <a href="/api/docs" target="_blank" rel="noopener noreferrer">
                <BookOpen className="w-4 h-4 mr-2" />
                Ouvrir la documentation Swagger
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Iframe Swagger en option */}
      <div className="flex-1 border-t">
        <div className="p-4 bg-muted/50">
          <h3 className="text-sm font-semibold mb-2">Documentation complète intégrée</h3>
          <p className="text-xs text-muted-foreground mb-4">
            Interface Swagger interactive avec tous les schémas, paramètres et possibilités de test
          </p>
        </div>
        <iframe
          src="/api/docs"
          className="w-full h-[600px] border-0"
          title="API Documentation"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        />
      </div>
    </div>
  )
}
