import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Code,
  BookOpen,
  Zap,
  Globe,
  Database,
  Rocket,
  ExternalLink,
  Copy,
  CheckCircle
} from 'lucide-react'

interface ApiDemoProps {}

const apiFeatures = [
  {
    title: 'Automatisation complète',
    description: 'Contrôlez tout le pipeline Niamoto via API REST',
    icon: <Zap className="w-6 h-6 text-yellow-500" />
  },
  {
    title: '57 endpoints',
    description: '10 modules couvrant import, transformation, export',
    icon: <Database className="w-6 h-6 text-blue-500" />
  },
  {
    title: 'Intégration externe',
    description: 'Applications tierces, SIG, workflows scientifiques',
    icon: <Globe className="w-6 h-6 text-green-500" />
  }
]

const quickExamples = {
  'Récupérer un taxon': {
    language: 'bash',
    code: `curl http://localhost:8080/api/entities/entity/taxon/1`
  },
  'Lancer une transformation': {
    language: 'bash',
    code: `curl -X POST http://localhost:8080/api/transform/execute \\
  -H "Content-Type: application/json" \\
  -d '{"config_path": "config/transform.yml"}'`
  },
  'Exporter le site': {
    language: 'bash',
    code: `curl -X POST http://localhost:8080/api/export/execute \\
  -H "Content-Type: application/json" \\
  -d '{"config_path": "config/export.yml"}'`
  }
}

const fullExamples = {
  python: `import requests

# 1. Récupérer un taxon avec tous ses widgets
response = requests.get(
    "http://localhost:8080/api/entities/entity/taxon/1"
)
taxon = response.json()
print(f"Taxon: {taxon['name']}")
print(f"Widgets disponibles: {len(taxon['widgets'])}")

# 2. Lancer une transformation
response = requests.post(
    "http://localhost:8080/api/transform/execute",
    json={"config_path": "config/transform.yml"}
)
job = response.json()
job_id = job["job_id"]

# 3. Suivre la progression
import time
while True:
    status = requests.get(
        f"http://localhost:8080/api/transform/status/{job_id}"
    ).json()

    print(f"Progress: {status['progress']}%")

    if status["status"] == "completed":
        print("✓ Transformation terminée!")
        break

    time.sleep(1)`,

  javascript: `// 1. Récupérer un taxon avec tous ses widgets
const taxon = await fetch(
  'http://localhost:8080/api/entities/entity/taxon/1'
).then(r => r.json())

console.log(\`Taxon: \${taxon.name}\`)
console.log(\`Widgets: \${taxon.widgets.length}\`)

// 2. Lancer un export
const job = await fetch(
  'http://localhost:8080/api/export/execute',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      config_path: 'config/export.yml'
    })
  }
).then(r => r.json())

// 3. Suivre la progression
const pollStatus = async (jobId) => {
  while (true) {
    const status = await fetch(
      \`http://localhost:8080/api/export/status/\${jobId}\`
    ).then(r => r.json())

    console.log(\`Progress: \${status.progress}%\`)

    if (status.status === 'completed') {
      console.log('✓ Export terminé!')
      return status
    }

    await new Promise(r => setTimeout(r, 1000))
  }
}

await pollStatus(job.job_id)`,

  r: `library(httr)
library(jsonlite)

# 1. Récupérer tous les taxons
response <- GET("http://localhost:8080/api/entities/entities/taxon")
taxons <- content(response, as = "parsed")

# Convertir en dataframe pour analyse
df <- do.call(rbind, lapply(taxons, as.data.frame))
print(paste("Nombre de taxons:", nrow(df)))

# 2. Requête SQL personnalisée sur la base
query <- list(
  query = "SELECT rank_name, COUNT(*) as count
           FROM taxon GROUP BY rank_name"
)

response <- POST(
  "http://localhost:8080/api/data/query",
  body = query,
  encode = "json"
)

result <- content(response, as = "parsed")
print(result$rows)

# 3. Exporter pour analyse
POST(
  "http://localhost:8080/api/export/execute",
  body = list(config_path = "config/export.yml"),
  encode = "json"
)`
}

export function ApiDemo({}: ApiDemoProps) {
  const [copiedExample, setCopiedExample] = useState<string | null>(null)

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedExample(key)
    setTimeout(() => setCopiedExample(null), 2000)
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">API REST Complète</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Intégrez Niamoto dans vos workflows et applications
        </p>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {apiFeatures.map((feature, idx) => (
          <Card key={idx}>
            <CardContent className="pt-6 space-y-2 text-center">
              <div className="flex justify-center mb-2">
                {feature.icon}
              </div>
              <h3 className="font-semibold">{feature.title}</h3>
              <p className="text-xs text-muted-foreground">
                {feature.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Examples */}
      <Card>
        <CardHeader>
          <CardTitle>Exemples rapides</CardTitle>
          <CardDescription>
            Commandes cURL pour tester l'API immédiatement
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(quickExamples).map(([title, { code }]) => (
            <div key={title} className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">{title}</h4>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(code, title)}
                >
                  {copiedExample === title ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
              <pre className="bg-muted p-3 rounded-lg text-xs overflow-x-auto">
                <code>{code}</code>
              </pre>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Full Examples */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="w-5 h-5" />
            Exemples complets
          </CardTitle>
          <CardDescription>
            Workflow complet : récupération de données, exécution de jobs, suivi de progression
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="python" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="python">Python</TabsTrigger>
              <TabsTrigger value="javascript">JavaScript</TabsTrigger>
              <TabsTrigger value="r">R</TabsTrigger>
            </TabsList>
            {Object.entries(fullExamples).map(([lang, code]) => (
              <TabsContent key={lang} value={lang} className="mt-4">
                <div className="relative">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-2 right-2 z-10"
                    onClick={() => copyToClipboard(code, lang)}
                  >
                    {copiedExample === lang ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                  <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto max-h-96">
                    <code>{code}</code>
                  </pre>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>

      {/* Use Cases */}
      <Card>
        <CardHeader>
          <CardTitle>Cas d'usage</CardTitle>
          <CardDescription>
            Comment utiliser l'API Niamoto dans différents contextes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Rocket className="w-5 h-5 text-purple-500" />
                <h4 className="font-semibold">Automatisation CI/CD</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Intégrez les exports Niamoto dans vos pipelines d'intégration continue :
                génération automatique du site à chaque modification des données source
              </p>
              <div className="bg-muted/50 p-3 rounded text-xs font-mono">
                GitHub Actions, GitLab CI, Jenkins
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-500" />
                <h4 className="font-semibold">Applications web personnalisées</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Construisez des interfaces sur-mesure qui consomment les données Niamoto :
                tableaux de bord, visualisations interactives, portails spécialisés
              </p>
              <div className="bg-muted/50 p-3 rounded text-xs font-mono">
                React, Vue, Svelte, Next.js
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-green-500" />
                <h4 className="font-semibold">Intégration SIG</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Connectez vos outils SIG pour accéder aux données géographiques :
                visualisation, analyse spatiale, export de couches personnalisées
              </p>
              <div className="bg-muted/50 p-3 rounded text-xs font-mono">
                QGIS, ArcGIS, Python scripts
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Code className="w-5 h-5 text-orange-500" />
                <h4 className="font-semibold">Workflows scientifiques</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Intégrez Niamoto dans vos analyses : extraction de données pour modélisation,
                analyses statistiques, génération de rapports automatisés
              </p>
              <div className="bg-muted/50 p-3 rounded text-xs font-mono">
                R scripts, Python notebooks, workflows
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Documentation Link */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            Documentation complète
          </CardTitle>
          <CardDescription>
            Explorez tous les endpoints, schémas et testez l'API directement
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-medium text-sm">10 modules API</h4>
              <p className="text-xs text-muted-foreground">
                Configuration, Plugins, Import, Transform, Export, Database,
                Entities, Data Explorer, Files, Bootstrap
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm">57 endpoints REST</h4>
              <p className="text-xs text-muted-foreground">
                GET, POST, PUT, DELETE avec validation automatique,
                documentation Swagger interactive et schémas JSON
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <Button asChild className="flex-1">
              <a href="/tools/docs" target="_blank" rel="noopener noreferrer">
                <BookOpen className="w-4 h-4 mr-2" />
                Voir la documentation API
              </a>
            </Button>
            <Button asChild variant="outline" className="flex-1">
              <a href="/api/docs" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                Ouvrir Swagger UI
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
