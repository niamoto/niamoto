import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { useProgressiveCounter } from '@/hooks/useProgressiveCounter'
import {
  Globe,
  FileCode,
  Rocket,
  CheckCircle,
  Database,
  FileJson,
  Layers,
  Package,
  FolderOpen
} from 'lucide-react'
import { executeExportAndWait } from '@/lib/api/export'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api/client'

interface ExportDemoProps {}

interface ExportTarget {
  name: string
  files: number
}

export function ExportDemo({}: ExportDemoProps) {
  const navigate = useNavigate()
  const { setDemoProgress } = useShowcaseStore()
  const [exporting, setExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState(0)
  const [exportStarted, setExportStarted] = useState(false)
  const [exportPath, setExportPath] = useState<string>('')
  const [targetMetrics, setTargetMetrics] = useState<{
    totalFiles: number
    duration: number
    targets: ExportTarget[]
  }>({ totalFiles: 0, duration: 0, targets: [] })

  const totalFilesCounter = useProgressiveCounter(
    exportStarted ? targetMetrics.totalFiles : 0,
    3000,
    exportStarted
  )

  // Load working directory to get export path
  useEffect(() => {
    const loadWorkingDir = async () => {
      try {
        const response = await apiClient.get('/config/project')
        const workingDir = response.data.working_directory || process.cwd()
        setExportPath(`${workingDir}/exports`)
      } catch (error) {
        console.error('Failed to load working directory:', error)
        setExportPath('exports')
      }
    }
    loadWorkingDir()
  }, [])

  const runExport = async () => {
    setExporting(true)
    setExportStarted(false)
    setExportProgress(0)

    const startTime = Date.now()

    try {
      const result = await executeExportAndWait(
        { config_path: 'config/export.yml' },
        (progress) => {
          setExportProgress(progress)
        }
      )

      // Extract real metrics from result
      if (result.result) {
        const exports = result.result.exports || {}
        const metrics = result.result.metrics || {}

        const targets: ExportTarget[] = []
        let totalFiles = 0

        // Extract files from each export target
        Object.entries(exports).forEach(([name, exportData]: [string, any]) => {
          if (exportData && exportData.data) {
            const filesGenerated = exportData.data.files_generated || 0
            if (filesGenerated > 0) {
              targets.push({ name, files: filesGenerated })
              totalFiles += filesGenerated
            }
          }
        })

        // Fallback: use metrics if no exports data
        if (totalFiles === 0 && metrics.generated_pages) {
          totalFiles = metrics.generated_pages
        }

        const duration = metrics.execution_time
          ? metrics.execution_time.toFixed(1)
          : ((Date.now() - startTime) / 1000).toFixed(1)


        const newMetrics = {
          totalFiles,
          duration: parseFloat(duration),
          targets
        }

        setTargetMetrics(newMetrics)

        // Start counters after metrics are updated
        setTimeout(() => {
          setExportStarted(true)
        }, 100)
      }

      setExportProgress(100)
      setDemoProgress('export', 100)
      toast.success('Export terminé avec succès!')
    } catch (error) {
      console.error('Export error:', error)
      toast.error('Erreur lors de l\'export')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Export & Publication</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Génération du site web statique avec visualisations interactives
        </p>
      </div>

      {/* Export Targets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 space-y-2">
            <div className="flex items-center justify-between">
              <Globe className="w-8 h-8 text-purple-500" />
              <Badge variant="secondary">Cible 1</Badge>
            </div>
            <h3 className="font-semibold">Site Web Statique</h3>
            <p className="text-xs text-muted-foreground">
              Pages HTML avec navigation hiérarchique, cartes interactives et visualisations
            </p>
            <div className="pt-2 space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <Layers className="w-3 h-3" />
                <span className="text-muted-foreground">Groupes: taxon, plot, shape</span>
              </div>
              <div className="flex items-center gap-2">
                <Package className="w-3 h-3" />
                <span className="text-muted-foreground">22+ types de widgets</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 space-y-2">
            <div className="flex items-center justify-between">
              <FileJson className="w-8 h-8 text-blue-500" />
              <Badge variant="secondary">Cible 2</Badge>
            </div>
            <h3 className="font-semibold">API JSON Statique</h3>
            <p className="text-xs text-muted-foreground">
              Endpoints JSON pour chaque entité et fichiers d'index par groupe
            </p>
            <div className="pt-2 space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <Database className="w-3 h-3" />
                <span className="text-muted-foreground">Format structuré</span>
              </div>
              <div className="flex items-center gap-2">
                <FileCode className="w-3 h-3" />
                <span className="text-muted-foreground">Configurable (minify, compress)</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 space-y-2">
            <div className="flex items-center justify-between">
              <Database className="w-8 h-8 text-green-500" />
              <Badge variant="secondary">Cible 3</Badge>
            </div>
            <h3 className="font-semibold">Darwin Core Archive</h3>
            <p className="text-xs text-muted-foreground">
              Export des occurrences au format Darwin Core pour interopérabilité
            </p>
            <div className="pt-2 space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <Globe className="w-3 h-3" />
                <span className="text-muted-foreground">Standard international</span>
              </div>
              <div className="flex items-center gap-2">
                <FileJson className="w-3 h-3" />
                <span className="text-muted-foreground">Fichiers JSON par taxon</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Export Process */}
      <Card>
        <CardHeader>
          <CardTitle>Génération du site</CardTitle>
          <CardDescription>
            Création du site web statique complet
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {exporting && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Export en cours...</span>
                <span>{exportProgress}%</span>
              </div>
              <Progress value={exportProgress} />
              <div className="text-xs text-muted-foreground">
                {exportProgress < 25 && 'Génération des pages HTML...'}
                {exportProgress >= 25 && exportProgress < 50 && 'Création des visualisations...'}
                {exportProgress >= 50 && exportProgress < 75 && 'Optimisation des assets...'}
                {exportProgress >= 75 && exportProgress < 100 && 'Finalisation...'}
                {exportProgress === 100 && 'Export terminé !'}
              </div>
            </div>
          )}

          {exportProgress === 100 && exportStarted && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="font-medium">Export terminé avec succès !</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Les fichiers sont prêts à être déployés
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-primary">{totalFilesCounter.value.toLocaleString()}</div>
                    <p className="text-xs text-muted-foreground">Fichiers générés</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-primary">{targetMetrics.duration}s</div>
                    <p className="text-xs text-muted-foreground">Temps de génération</p>
                  </CardContent>
                </Card>
              </div>

              {/* Target breakdown */}
              {targetMetrics.targets.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-medium mb-3">Détail par cible</h4>
                  <div className="space-y-2">
                    {targetMetrics.targets.map((target) => (
                      <div key={target.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2">
                          {target.name === 'web_pages' && <Globe className="w-4 h-4 text-purple-500" />}
                          {target.name === 'json_api' && <FileJson className="w-4 h-4 text-blue-500" />}
                          {target.name === 'dwc_occurrence_json' && <Database className="w-4 h-4 text-green-500" />}
                          <span className="text-sm font-medium capitalize">{target.name.replace(/_/g, ' ')}</span>
                        </div>
                        <Badge variant="secondary">
                          {target.files.toLocaleString()} fichiers
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  variant="default"
                  className="flex-1"
                  onClick={() => navigate('/data/preview')}
                >
                  <Globe className="w-4 h-4 mr-2" />
                  Voir le site
                </Button>
              </div>
            </div>
          )}

          {exportProgress !== 100 && !exporting && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">Prêt à exporter</span>
              </div>
              <Button onClick={runExport} disabled={exporting}>
                <Rocket className="w-4 h-4 mr-2" />
                Générer le site
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Site Preview */}
      {exportProgress === 100 && exportStarted && (
        <Card>
          <CardHeader>
            <CardTitle>Aperçu du site généré</CardTitle>
            <CardDescription>Prévisualisation interactive du site exporté</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border overflow-hidden">
              <iframe
                src="/preview/index.html"
                className="w-full h-[600px] border-0"
                title="Site exporté"
                sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Le site complet est disponible dans <code className="px-1 py-0.5 bg-muted rounded">exports/web/</code>
            </p>
          </CardContent>
        </Card>
      )}

      {/* Generated Files Preview */}
      {exportProgress === 100 && exportStarted && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderOpen className="w-5 h-5" />
              Structure des exports
            </CardTitle>
            <CardDescription>
              Organisation des fichiers générés
              {exportPath && (
                <div className="mt-2 flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs">
                  <FolderOpen className="w-4 h-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Répertoire :</span>
                  <code className="text-foreground">{exportPath}</code>
                </div>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="font-mono text-xs space-y-1">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4 text-muted-foreground" />
                <span className="font-semibold">exports/</span>
              </div>
              <div className="ml-4">📁 web/ <span className="text-muted-foreground">→ Site statique HTML</span></div>
              <div className="ml-8">📄 index.html</div>
              <div className="ml-8">📁 taxon/ <span className="text-muted-foreground">→ Pages par taxon</span></div>
              <div className="ml-8">📁 plot/ <span className="text-muted-foreground">→ Pages par parcelle</span></div>
              <div className="ml-8">📁 shape/ <span className="text-muted-foreground">→ Pages par zone</span></div>
              <div className="ml-8">📁 assets/ <span className="text-muted-foreground">→ CSS, JS, images</span></div>
              <div className="ml-4">📁 api/ <span className="text-muted-foreground">→ API JSON statique</span></div>
              <div className="ml-8">📄 all_taxon.json</div>
              <div className="ml-8">📄 all_plot.json</div>
              <div className="ml-8">📄 all_shape.json</div>
              <div className="ml-8">📁 taxon/ <span className="text-muted-foreground">→ JSON détaillés par taxon</span></div>
              <div className="ml-4">📁 dwc/ <span className="text-muted-foreground">→ Darwin Core exports</span></div>
              <div className="ml-8">📁 occurrence_json/ <span className="text-muted-foreground">→ Occurrences par taxon</span></div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
