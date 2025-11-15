import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  ArrowRight,
  Github,
  BookOpen,
  Sparkles,
  Code
} from 'lucide-react'

interface CallToActionProps {}

export function CallToAction({}: CallToActionProps) {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <Badge variant="outline" className="mb-4">
          <Sparkles className="w-3 h-3 mr-1" />
          Open Source
        </Badge>
        <h2 className="text-4xl md:text-5xl font-bold">
          Prêt à transformer vos données ?
        </h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Rejoignez la communauté Niamoto et créez votre site de données écologiques en quelques minutes
        </p>
      </div>

      {/* Main CTA Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button
          size="lg"
          className="group"
          onClick={() => window.open('https://github.com/niamoto/niamoto', '_blank')}
        >
          <Github className="mr-2 h-5 w-5" />
          Commencer sur GitHub
          <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
        </Button>
        <Button
          size="lg"
          variant="outline"
          onClick={() => window.open('https://niamoto.readthedocs.io/', '_blank')}
        >
          <BookOpen className="mr-2 h-5 w-5" />
          Lire la documentation
        </Button>
      </div>

      {/* Quick Start Command */}
      <Card className="max-w-2xl mx-auto">
        <CardContent className="pt-6">
          <div className="space-y-4">
            <h3 className="font-semibold text-center">Installation rapide</h3>
            <div className="bg-muted rounded-lg p-4">
              <code className="text-sm font-mono">pip install niamoto</code>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm">
              <div className="flex items-center gap-2">
                <Code className="w-4 h-4 text-muted-foreground" />
                <span>niamoto init</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
                <span>niamoto import</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
                <span>niamoto transform</span>
              </div>
              <div className="flex items-center gap-2">
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
                <span>niamoto export</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Final Message */}
      <div className="text-center pt-8 space-y-4">
        <p className="text-lg text-muted-foreground">
          Construit avec 💚 pour la communauté scientifique
        </p>
        <div className="flex justify-center gap-4">
          <Badge variant="secondary">v0.7.3</Badge>
          <Badge variant="secondary">GPL-3.0</Badge>
          <Badge variant="secondary">Python 3.11+</Badge>
        </div>
      </div>
    </div>
  )
}
