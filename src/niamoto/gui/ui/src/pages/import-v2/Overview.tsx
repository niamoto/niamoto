import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  FileSpreadsheet,
  TreePine,
  MapPin,
  Map,
  ArrowRight,
  Database,
  BarChart3,
  CheckCircle
} from 'lucide-react'

import niamotoLogo from '@/assets/niamoto_logo.png'

export function Overview() {
  return (
    <div className="space-y-8">
      {/* Welcome message */}
      <div className="text-center space-y-4">
        <img
          src={niamotoLogo}
          alt="Niamoto Logo"
          className="w-32 h-32 mx-auto object-contain"
        />
        <h2 className="text-2xl font-bold">Bienvenue dans l'import de données Niamoto</h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Niamoto organise vos données écologiques autour des observations (occurrences).
          Cette interface guidée vous accompagnera pas à pas dans le processus d'import.
        </p>
      </div>

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle>Comment fonctionne Niamoto ?</CardTitle>
          <CardDescription>
            Comprendre le flux de données pour mieux organiser vos imports
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-5 gap-4 items-center">
            <div className="text-center space-y-2">
              <div className="bg-primary/10 w-20 h-20 rounded-full flex items-center justify-center mx-auto">
                <FileSpreadsheet className="w-10 h-10 text-primary" />
              </div>
              <div className="font-medium">Occurrences</div>
              <div className="text-sm text-muted-foreground">Observations brutes</div>
            </div>

            <div className="hidden md:flex justify-center">
              <ArrowRight className="w-6 h-6 text-muted-foreground" />
            </div>

            <div className="text-center space-y-2">
              <div className="bg-green-100 dark:bg-green-900/20 w-20 h-20 rounded-full flex items-center justify-center mx-auto">
                <TreePine className="w-10 h-10 text-green-600" />
              </div>
              <div className="font-medium">Taxonomie</div>
              <div className="text-sm text-muted-foreground">Extraction automatique</div>
              <Badge variant="secondary" className="text-xs">Automatique</Badge>
            </div>

            <div className="hidden md:flex justify-center">
              <ArrowRight className="w-6 h-6 text-muted-foreground" />
            </div>

            <div className="text-center space-y-2">
              <div className="bg-blue-100 dark:bg-blue-900/20 w-20 h-20 rounded-full flex items-center justify-center mx-auto">
                <MapPin className="w-10 h-10 text-blue-600" />
              </div>
              <div className="font-medium">Agrégations</div>
              <div className="text-sm text-muted-foreground">Plots & Shapes</div>
              <Badge variant="outline" className="text-xs">Optionnel</Badge>
            </div>
          </div>

          <Alert className="mt-6">
            <Database className="w-4 h-4" />
            <AlertDescription>
              <strong>Point clé :</strong> La taxonomie est extraite automatiquement de vos occurrences.
              Vous n'avez pas besoin de l'importer séparément !
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Requirements */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              Ce dont vous avez besoin
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">Fichier d'occurrences (CSV) avec :</h4>
              <ul className="space-y-1 text-sm text-muted-foreground ml-4">
                <li>• Identifiant taxonomique unique</li>
                <li>• Localisation (coordonnées WKT ou lat/lon)</li>
                <li>• Colonnes taxonomiques (famille, genre, espèce...)</li>
                <li>• Autorité taxonomique (optionnel)</li>
                <li>• Lien vers plot/parcelle (optionnel)</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              Options d'agrégation (facultatif)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                Plots
              </h4>
              <p className="text-sm text-muted-foreground ml-5">
                Regroupements spatiaux : parcelles, localités, sites d'étude
              </p>
            </div>
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Map className="w-4 h-4" />
                Shapes
              </h4>
              <p className="text-sm text-muted-foreground ml-5">
                Zones géographiques : communes, provinces, régions
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Process summary */}
      <Card className="border-primary/50">
        <CardHeader>
          <CardTitle>Processus d'import en 3 étapes</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-none">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  1
                </div>
              </div>
              <div className="flex-1">
                <h4 className="font-medium">Import des occurrences</h4>
                <p className="text-sm text-muted-foreground">
                  Chargez votre fichier CSV et configurez le mapping des colonnes.
                  La taxonomie sera extraite automatiquement.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-none">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  2
                </div>
              </div>
              <div className="flex-1">
                <h4 className="font-medium">Agrégations spatiales (optionnel)</h4>
                <p className="text-sm text-muted-foreground">
                  Ajoutez des plots ou des shapes pour regrouper vos données
                  et générer des statistiques par zone.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-none">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  3
                </div>
              </div>
              <div className="flex-1">
                <h4 className="font-medium">Vérification et import</h4>
                <p className="text-sm text-muted-foreground">
                  Vérifiez le résumé de vos données et lancez l'import.
                  Les statistiques seront générées automatiquement.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
