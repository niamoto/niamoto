import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Terminal,
  Server,
  Globe,
  Database,
  Layers,
  Package,
  Code2,
  Wrench
} from 'lucide-react'

const pythonStack = [
  {
    category: 'CLI & Core',
    icon: Terminal,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    items: [
      { name: 'Click', description: 'Interface ligne de commande élégante', version: '8.1+' },
      { name: 'Rich', description: 'Affichage console moderne', version: '10.0+' },
      { name: 'Pydantic', description: 'Validation de données', version: '2.0+' }
    ]
  },
  {
    category: 'Base de données',
    icon: Database,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    items: [
      { name: 'SQLAlchemy', description: 'ORM Python puissant', version: '2.0+' },
      { name: 'GeoAlchemy2', description: 'Extensions géospatiales', version: '0.14+' },
      { name: 'SQLite', description: 'Base de données embarquée', version: '3.40+' }
    ]
  },
  {
    category: 'Géospatial',
    icon: Layers,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    items: [
      { name: 'GeoPandas', description: 'Données géographiques', version: '0.14+' },
      { name: 'Shapely', description: 'Manipulation géométries', version: '2.0+' },
      { name: 'Fiona', description: 'I/O formats géospatiaux', version: '1.9+' }
    ]
  },
  {
    category: 'Configuration',
    icon: Wrench,
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    items: [
      { name: 'PyYAML', description: 'Parsing YAML', version: '6.0+' },
      { name: 'Jinja2', description: 'Moteur de templates', version: '3.1+' },
      { name: 'Markdown', description: 'Conversion Markdown', version: '3.5+' }
    ]
  }
]

const backendStack = [
  {
    category: 'Serveur API',
    icon: Server,
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-500/10',
    items: [
      { name: 'FastAPI', description: 'Framework web moderne', version: '0.115+' },
      { name: 'Uvicorn', description: 'Serveur ASGI haute performance', version: '0.32+' },
      { name: 'Server-Sent Events', description: 'Streaming temps réel', version: 'native' }
    ]
  },
  {
    category: 'API',
    icon: Code2,
    color: 'text-pink-500',
    bgColor: 'bg-pink-500/10',
    items: [
      { name: '57 endpoints REST', description: '10 modules API spécialisés' },
      { name: 'OpenAPI/Swagger', description: 'Documentation interactive' },
      { name: 'CORS', description: 'Support multi-origine' }
    ]
  }
]

const frontendStack = [
  {
    category: 'Framework UI',
    icon: Globe,
    color: 'text-cyan-500',
    bgColor: 'bg-cyan-500/10',
    items: [
      { name: 'React', description: 'Library UI moderne', version: '19' },
      { name: 'TypeScript', description: 'JavaScript typé', version: '5.6+' },
      { name: 'Vite', description: 'Build tool ultra-rapide', version: '7.0+' }
    ]
  },
  {
    category: 'Styling & UI',
    icon: Package,
    color: 'text-teal-500',
    bgColor: 'bg-teal-500/10',
    items: [
      { name: 'Tailwind CSS', description: 'Framework CSS utility-first', version: '4.0' },
      { name: 'shadcn/ui', description: 'Composants réutilisables', version: 'latest' },
      { name: 'Lucide Icons', description: 'Icônes modernes', version: 'latest' }
    ]
  },
  {
    category: 'State & Outils',
    icon: Wrench,
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    items: [
      { name: 'Zustand', description: 'State management simple', version: '5.0+' },
      { name: 'React Hook Form', description: 'Gestion de formulaires', version: '7.54+' },
      { name: 'Monaco Editor', description: 'Éditeur de code', version: '0.52+' },
      { name: 'Plotly.js', description: 'Visualisations interactives', version: '2.35+' }
    ]
  }
]

export function StackTechSection() {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-8 py-12">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Stack Technique</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Technologies modernes pour une expérience utilisateur optimale
        </p>
      </div>

      {/* Python Core & CLI */}
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Terminal className="w-6 h-6 text-blue-500" />
          <h3 className="text-2xl font-bold">Python Core & CLI</h3>
          <Badge variant="outline">Python 3.10+</Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {pythonStack.map((stack) => {
            const Icon = stack.icon
            return (
              <Card key={stack.category} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className={`w-12 h-12 rounded-lg ${stack.bgColor} flex items-center justify-center mb-2`}>
                    <Icon className={`w-6 h-6 ${stack.color}`} />
                  </div>
                  <CardTitle className="text-lg">{stack.category}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {stack.items.map((item: any) => (
                    <div key={item.name} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{item.name}</span>
                        {item.version && (
                          <Badge variant="secondary" className="text-xs">
                            {item.version}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Backend API */}
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Server className="w-6 h-6 text-indigo-500" />
          <h3 className="text-2xl font-bold">Backend API (FastAPI + Uvicorn)</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {backendStack.map((stack) => {
            const Icon = stack.icon
            return (
              <Card key={stack.category} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className={`w-12 h-12 rounded-lg ${stack.bgColor} flex items-center justify-center mb-2`}>
                    <Icon className={`w-6 h-6 ${stack.color}`} />
                  </div>
                  <CardTitle className="text-lg">{stack.category}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {stack.items.map((item: any) => (
                    <div key={item.name} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{item.name}</span>
                        {item.version && (
                          <Badge variant="secondary" className="text-xs">
                            {item.version}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Frontend UI */}
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Globe className="w-6 h-6 text-cyan-500" />
          <h3 className="text-2xl font-bold">Interface Utilisateur (React + Vite)</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {frontendStack.map((stack) => {
            const Icon = stack.icon
            return (
              <Card key={stack.category} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className={`w-12 h-12 rounded-lg ${stack.bgColor} flex items-center justify-center mb-2`}>
                    <Icon className={`w-6 h-6 ${stack.color}`} />
                  </div>
                  <CardTitle className="text-lg">{stack.category}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {stack.items.map((item: any) => (
                    <div key={item.name} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{item.name}</span>
                        {item.version && (
                          <Badge variant="secondary" className="text-xs">
                            {item.version}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Architecture Summary */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle>Architecture Complète</CardTitle>
          <CardDescription>
            Stack moderne full-stack Python/TypeScript
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div className="space-y-2">
              <Terminal className="w-8 h-8 mx-auto text-blue-500" />
              <div className="font-bold">CLI Python</div>
              <div className="text-sm text-muted-foreground">
                Click + Rich pour une expérience ligne de commande moderne
              </div>
            </div>
            <div className="space-y-2">
              <Server className="w-8 h-8 mx-auto text-indigo-500" />
              <div className="font-bold">API REST</div>
              <div className="text-sm text-muted-foreground">
                FastAPI + Uvicorn pour performance et scalabilité
              </div>
            </div>
            <div className="space-y-2">
              <Globe className="w-8 h-8 mx-auto text-cyan-500" />
              <div className="font-bold">Interface Web</div>
              <div className="text-sm text-muted-foreground">
                React + TypeScript pour une UI réactive
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
