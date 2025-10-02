import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { usePipelineStore } from '@/stores/pipelineStore'
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
  FolderOpen,
  ChevronRight,
  ChevronDown,
  Upload,
  Cloud,
  Terminal,
  ExternalLink,
  Server,
  Key
} from 'lucide-react'
import { executeExportAndWait } from '@/lib/api/export'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api/client'
import { getExportsStructure, type ExportsStructure, type ExportTreeItem } from '@/lib/api/exports'

interface ExportDemoProps {}

interface ExportTarget {
  name: string
  files: number
}

// Helper component to render tree items recursively
function TreeItem({ item, depth }: { item: ExportTreeItem; depth: number }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const icon = item.type === 'directory' ? '📁' : '📄'

  // Get description based on folder name
  const getDescription = (name: string) => {
    const descriptions: Record<string, string> = {
      'web': 'Site statique HTML',
      'api': 'API JSON statique',
      'dwc': 'Darwin Core exports',
      'dwc-archive': 'Archive DwC-A standard',
      'taxon': 'Pages/JSON par taxon',
      'plot': 'Pages/JSON par parcelle',
      'shape': 'Pages/JSON par zone',
      'assets': 'CSS, JS, images',
      'occurrence_json': 'Occurrences par taxon',
    }
    return descriptions[name]
  }

  const description = item.type === 'directory' ? getDescription(item.name) : null
  const displayCount = item.type === 'directory' && item.count ? ` (${item.count})` : ''

  const handleToggle = () => {
    if (item.type === 'directory' && item.children) {
      setIsExpanded(!isExpanded)
    }
  }

  return (
    <>
      <div
        style={{ marginLeft: `${depth * 1}rem` }}
        className={item.type === 'directory' && item.children ? 'cursor-pointer hover:bg-muted/50 rounded px-1' : 'px-1'}
        onClick={handleToggle}
      >
        {item.type === 'directory' && item.children && (
          isExpanded ?
            <ChevronDown className="inline w-3 h-3 mr-1" /> :
            <ChevronRight className="inline w-3 h-3 mr-1" />
        )}
        {icon} {item.name}{displayCount}
        {description && <span className="text-muted-foreground"> → {description}</span>}
      </div>
      {isExpanded && item.children && item.children.map((child, idx) => (
        <TreeItem key={idx} item={child} depth={depth + 1} />
      ))}
    </>
  )
}

export function ExportDemo({}: ExportDemoProps) {
  const navigate = useNavigate()
  const { setDemoProgress } = useShowcaseStore()
  const { exportResult, setExportResult, setCurrentStep: setPipelineStep } = usePipelineStore()
  const [exporting, setExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState(0)
  const [exportStarted, setExportStarted] = useState(false)
  const [exportPath, setExportPath] = useState<string>('')
  const [targetMetrics, setTargetMetrics] = useState<{
    totalFiles: number
    duration: number
    targets: ExportTarget[]
  }>({ totalFiles: 0, duration: 0, targets: [] })
  const [exportsStructure, setExportsStructure] = useState<ExportsStructure | null>(null)

  // Deployment states
  const [deployModal, setDeployModal] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [branchName, setBranchName] = useState('')
  const [deploying, setDeploying] = useState(false)
  const [deployLogs, setDeployLogs] = useState<string[]>([])
  const [deploymentUrl, setDeploymentUrl] = useState<string | null>(null)

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
        const workingDir = response.data.working_directory || '.'
        setExportPath(`${workingDir}/exports`)
      } catch (error) {
        console.error('Failed to load working directory:', error)
        setExportPath('exports')
      }
    }
    loadWorkingDir()
  }, [])

  // Check for existing export result from pipeline store
  useEffect(() => {
    if (exportResult && exportResult.result) {
      const exports = exportResult.result.exports || {}
      const metrics = exportResult.result.metrics || {}

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

      const newMetrics = {
        totalFiles,
        duration: exportResult.duration,
        targets
      }

      setTargetMetrics(newMetrics)
      setExportStarted(true)
      setExportProgress(100)

      // Load exports structure
      loadExportsStructure()
    }
  }, [exportResult])

  const loadExportsStructure = async () => {
    try {
      const structure = await getExportsStructure()
      setExportsStructure(structure)
    } catch (error) {
      console.error('Failed to load exports structure:', error)
    }
  }

  const handleDeployToCloudflare = async () => {
    if (!projectName.trim()) {
      toast.error('Veuillez entrer un nom de projet')
      return
    }

    setDeploying(true)
    setDeployLogs([])
    setDeploymentUrl(null)

    try {
      const eventSource = new EventSource(
        `/api/deploy/cloudflare/deploy?project_name=${encodeURIComponent(projectName)}&branch=${encodeURIComponent(branchName)}`,
        { withCredentials: false }
      )

      eventSource.onmessage = (event) => {
        const data = event.data

        if (data === 'DONE') {
          eventSource.close()
          setDeploying(false)
          if (deploymentUrl) {
            toast.success('Déploiement réussi !')
          }
          return
        }

        if (data.startsWith('URL: ')) {
          const url = data.substring(5)
          setDeploymentUrl(url)
        } else if (data.startsWith('ERROR: ')) {
          setDeployLogs(prev => [...prev, `❌ ${data}`])
          toast.error('Erreur lors du déploiement')
        } else if (data.startsWith('SUCCESS: ')) {
          setDeployLogs(prev => [...prev, `✅ ${data}`])
        } else {
          setDeployLogs(prev => [...prev, data])
        }
      }

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error)
        eventSource.close()
        setDeploying(false)
        toast.error('Erreur de connexion au serveur')
      }
    } catch (error) {
      console.error('Deploy error:', error)
      setDeploying(false)
      toast.error('Erreur lors du déploiement')
    }
  }

  const runExport = async () => {
    setExporting(true)
    setPipelineStep('export') // Signal to pipeline store that export is running
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

        // Save to shared pipeline store
        setExportResult({
          status: 'completed',
          result: result.result,
          duration: parseFloat(duration)
        })

        // Start counters after metrics are updated
        setTimeout(() => {
          setExportStarted(true)
        }, 100)
      }

      setExportProgress(100)
      setDemoProgress('export', 100)

      // Load exports structure
      await loadExportsStructure()

      toast.success('Export terminé avec succès!')
    } catch (error) {
      console.error('Export error:', error)
      toast.error('Erreur lors de l\'export')
    } finally {
      setExporting(false)
      setPipelineStep(null) // Clear running state
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
                <span className="text-muted-foreground">Standard international GBIF</span>
              </div>
              <div className="flex items-center gap-2">
                <FileJson className="w-3 h-3" />
                <span className="text-muted-foreground">JSON par taxon + Archive ZIP</span>
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
                          {target.name === 'dwc_archive_standard' && <Package className="w-4 h-4 text-emerald-500" />}
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
            {exportsStructure && exportsStructure.exists ? (
              <div className="font-mono text-xs space-y-1">
                <div className="flex items-center gap-2">
                  <FolderOpen className="w-4 h-4 text-muted-foreground" />
                  <span className="font-semibold">exports/</span>
                </div>
                {exportsStructure.tree.map((item, idx) => (
                  <TreeItem key={idx} item={item} depth={1} />
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">
                Aucun export disponible
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Publication Options */}
      {exportProgress === 100 && exportStarted && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Publication
            </CardTitle>
            <CardDescription>
              Déployez votre site sur GitHub Pages, Netlify, Cloudflare ou votre serveur
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Deployment Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* GitHub Pages */}
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-gray-900 dark:bg-gray-100 flex items-center justify-center">
                        <svg viewBox="0 0 24 24" className="w-6 h-6 fill-white dark:fill-gray-900">
                          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                        </svg>
                      </div>
                      <div>
                        <h3 className="font-semibold">GitHub Pages</h3>
                        <p className="text-xs text-muted-foreground">Hébergement gratuit</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Déployez automatiquement vers une branche gh-pages de votre dépôt
                    </p>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Terminal className="w-4 h-4 text-muted-foreground" />
                        <span className="text-xs font-semibold">Commande</span>
                      </div>
                      <code className="text-xs font-mono block">
                        niamoto deploy github \<br/>
                        &nbsp;&nbsp;--repo https://github.com/user/repo \<br/>
                        &nbsp;&nbsp;--branch gh-pages
                      </code>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold">Options</h4>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--repo</code> : URL du dépôt GitHub</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--branch</code> : Branche cible (défaut: gh-pages)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--name</code> : Nom du committer</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--email</code> : Email du committer</span>
                      </div>
                    </div>
                  </div>

                  <Button variant="outline" className="w-full" asChild>
                    <a href="https://pages.github.com/" target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Documentation GitHub Pages
                    </a>
                  </Button>
                </CardContent>
              </Card>

              {/* Netlify */}
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-[#00C7B7] flex items-center justify-center">
                        <Cloud className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Netlify</h3>
                        <p className="text-xs text-muted-foreground">CDN global</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Déploiement instantané avec CDN mondial et HTTPS automatique
                    </p>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Terminal className="w-4 h-4 text-muted-foreground" />
                        <span className="text-xs font-semibold">Commande</span>
                      </div>
                      <code className="text-xs font-mono block">
                        niamoto deploy netlify \<br/>
                        &nbsp;&nbsp;--site-id your-site-id
                      </code>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold">Prérequis</h4>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span>Installer Netlify CLI : <code className="bg-muted px-1 py-0.5 rounded">npm install -g netlify-cli</code></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span>Se connecter : <code className="bg-muted px-1 py-0.5 rounded">netlify login</code></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span>Créer un site sur Netlify et récupérer le site-id</span>
                      </div>
                    </div>
                  </div>

                  <Button variant="outline" className="w-full" asChild>
                    <a href="https://docs.netlify.com/" target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Documentation Netlify
                    </a>
                  </Button>
                </CardContent>
              </Card>

              {/* Cloudflare Pages */}
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-[#F38020] flex items-center justify-center">
                        <Cloud className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Cloudflare Pages</h3>
                        <p className="text-xs text-muted-foreground">Réseau edge mondial</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Déploiement sur le réseau edge mondial de Cloudflare
                    </p>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Terminal className="w-4 h-4 text-muted-foreground" />
                        <span className="text-xs font-semibold">Commande</span>
                      </div>
                      <code className="text-xs font-mono block">
                        niamoto deploy cloudflare \<br/>
                        &nbsp;&nbsp;--project-name my-project \<br/>
                        &nbsp;&nbsp;--branch production
                      </code>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold">Prérequis</h4>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span>Installer Wrangler : <code className="bg-muted px-1 py-0.5 rounded">npm install -g wrangler</code></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span>Se connecter : <code className="bg-muted px-1 py-0.5 rounded">wrangler login</code></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span>Créer un projet Cloudflare Pages</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Button
                      variant="default"
                      className="w-full"
                      onClick={() => {
                        setDeployModal(true)
                        setProjectName('')
                        setBranchName('')
                        setDeployLogs([])
                        setDeploymentUrl(null)
                      }}
                      disabled={!exportStarted || exportProgress !== 100}
                    >
                      <Rocket className="w-4 h-4 mr-2" />
                      Déployer maintenant
                    </Button>
                    <Button variant="outline" className="w-full" asChild>
                      <a href="https://developers.cloudflare.com/pages/" target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-4 h-4 mr-2" />
                        Documentation
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* SSH/rsync */}
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center">
                        <Server className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">SSH/rsync</h3>
                        <p className="text-xs text-muted-foreground">Serveur custom</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Déployez sur votre propre serveur via SSH et rsync
                    </p>
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Terminal className="w-4 h-4 text-muted-foreground" />
                        <span className="text-xs font-semibold">Commande</span>
                      </div>
                      <code className="text-xs font-mono block">
                        niamoto deploy ssh \<br/>
                        &nbsp;&nbsp;--host user@server.com \<br/>
                        &nbsp;&nbsp;--path /var/www/html \<br/>
                        &nbsp;&nbsp;--port 22 \<br/>
                        &nbsp;&nbsp;--key ~/.ssh/id_rsa
                      </code>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold">Options</h4>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--host</code> : user@hostname</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--path</code> : Chemin distant</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--port</code> : Port SSH (défaut: 22)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        <span><code className="bg-muted px-1 py-0.5 rounded">--key</code> : Clé SSH privée</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
                    <Key className="w-4 h-4 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Nécessite rsync installé</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Additional Info */}
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-start gap-3">
                <Rocket className="w-5 h-5 text-blue-500 mt-0.5" />
                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">Publication automatisée</h4>
                  <p className="text-xs text-muted-foreground">
                    Ces commandes peuvent être intégrées dans vos workflows CI/CD (GitHub Actions, GitLab CI)
                    pour automatiser le déploiement à chaque modification de vos données source.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <Badge variant="secondary" className="text-xs">
                      GitHub Actions
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      GitLab CI
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      4 plateformes
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      Serveur custom
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Deployment Modal */}
      <Dialog open={deployModal} onOpenChange={setDeployModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Déployer sur Cloudflare Pages</DialogTitle>
            <DialogDescription>
              Déployez votre site exporté sur Cloudflare Pages
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {!deploying && !deploymentUrl && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="project-name">Nom du projet Cloudflare</Label>
                  <Input
                    id="project-name"
                    placeholder="mon-site-niamoto"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    disabled={deploying}
                  />
                  <p className="text-xs text-muted-foreground">
                    Le projet sera créé automatiquement s'il n'existe pas
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="branch-name">Branche (optionnel)</Label>
                  <Input
                    id="branch-name"
                    placeholder="Laisser vide pour déploiement en production"
                    value={branchName}
                    onChange={(e) => setBranchName(e.target.value)}
                    disabled={deploying}
                  />
                  <p className="text-xs text-muted-foreground">
                    Laisser vide pour URL principale (projet.pages.dev). Spécifier une branche crée un alias (branche.projet.pages.dev)
                  </p>
                </div>

                <Button
                  onClick={handleDeployToCloudflare}
                  disabled={!projectName.trim() || deploying}
                  className="w-full"
                >
                  <Rocket className="w-4 h-4 mr-2" />
                  Lancer le déploiement
                </Button>
              </div>
            )}

            {(deploying || deployLogs.length > 0) && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold">Logs de déploiement</h4>
                    {deploying && (
                      <div className="flex items-center gap-2">
                        <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                        <span className="text-xs text-muted-foreground">Déploiement en cours...</span>
                      </div>
                    )}
                  </div>
                  <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs max-h-96 overflow-y-auto">
                    {deployLogs.length === 0 ? (
                      <div className="text-muted-foreground">En attente des logs...</div>
                    ) : (
                      deployLogs.map((log, idx) => (
                        <div key={idx} className="mb-1">
                          {log}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {deploymentUrl && (
                  <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                    <div className="flex items-start gap-3">
                      <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                      <div className="space-y-2 flex-1">
                        <h4 className="font-semibold text-sm">Déploiement réussi !</h4>
                        <p className="text-xs text-muted-foreground">Votre site est maintenant en ligne</p>
                        <div className="flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs break-all">
                          <Globe className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                          <a href={deploymentUrl} target="_blank" rel="noopener noreferrer" className="hover:underline text-primary">
                            {deploymentUrl}
                          </a>
                        </div>
                        <Button asChild className="w-full" size="sm">
                          <a href={deploymentUrl} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="w-4 h-4 mr-2" />
                            Ouvrir le site
                          </a>
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  {!deploying && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setDeployModal(false)
                        setDeployLogs([])
                        setDeploymentUrl(null)
                        setProjectName('')
                      }}
                      className="flex-1"
                    >
                      Fermer
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
