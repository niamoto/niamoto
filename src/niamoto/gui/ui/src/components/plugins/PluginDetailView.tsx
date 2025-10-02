import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  X, Download, Copy, Bug, CheckCircle2, AlertCircle,
  Book, BarChart3, Settings, Package, Zap, Database,
  FileCode, TestTube, HelpCircle, GitBranch, Clock, TrendingUp,
  Eye, Palette, Smartphone, Monitor
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface PluginDetail {
  id: string
  name: string
  description: string
  type: 'loader' | 'transformer' | 'widget' | 'exporter'
  category?: string
  version?: string
  author?: string
  status?: 'active' | 'beta' | 'deprecated'
  compatible_inputs?: string[]
  output_format?: string
  parameters_schema?: any
  dependencies?: string[]
  examples?: any[]
  documentation?: string
  stats?: {
    usage_count: number
    last_used?: string
    avg_execution_time?: number
    error_rate?: number
  }
}

interface PluginDetailViewProps {
  plugin: PluginDetail
  onClose: () => void
}

export function PluginDetailView({ plugin, onClose }: PluginDetailViewProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [testResult, setTestResult] = useState<any>(null)
  const [isTesting, setIsTesting] = useState(false)

  const handleTest = async () => {
    setIsTesting(true)
    // Simulate test
    setTimeout(() => {
      setTestResult({
        success: true,
        message: 'Test completed successfully',
        output: { sample: 'data' }
      })
      setIsTesting(false)
    }, 2000)
  }

  const handleCopyConfig = () => {
    const config = {
      plugin: plugin.id,
      type: plugin.type,
      params: {}
    }
    navigator.clipboard.writeText(JSON.stringify(config, null, 2))
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50 dark:bg-green-950/20'
      case 'beta': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950/20'
      case 'deprecated': return 'text-red-600 bg-red-50 dark:bg-red-950/20'
      default: return 'text-gray-600 bg-gray-50 dark:bg-gray-950/20'
    }
  }

  const getTypeIcon = () => {
    switch (plugin.type) {
      case 'loader': return Database
      case 'transformer': return Settings
      case 'widget': return BarChart3
      case 'exporter': return Download
      default: return Package
    }
  }

  const TypeIcon = getTypeIcon()

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
      <div className="fixed inset-y-0 right-0 w-full max-w-3xl bg-background shadow-xl">
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="border-b px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2">
                  <TypeIcon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">{plugin.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline">{plugin.type}</Badge>
                    {plugin.category && (
                      <Badge variant="secondary">{plugin.category}</Badge>
                    )}
                    {plugin.status && (
                      <Badge className={cn("text-xs", getStatusColor(plugin.status))}>
                        {plugin.status}
                      </Badge>
                    )}
                    {plugin.version && (
                      <span className="text-xs text-muted-foreground">v{plugin.version}</span>
                    )}
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Content */}
          <ScrollArea className="flex-1">
            <div className="p-6">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-5">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="config">Configuration</TabsTrigger>
                  <TabsTrigger value="usage">Usage</TabsTrigger>
                  <TabsTrigger value="examples">Examples</TabsTrigger>
                  <TabsTrigger value="stats">Statistics</TabsTrigger>
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview" className="mt-6 space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Description</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        {plugin.description || 'No description available'}
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Technical Specifications</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {plugin.compatible_inputs && (
                        <div>
                          <h4 className="text-sm font-medium mb-2">Accepted Inputs</h4>
                          <div className="flex flex-wrap gap-2">
                            {plugin.compatible_inputs.map((input: string) => (
                              <Badge key={input} variant="outline">
                                <Database className="h-3 w-3 mr-1" />
                                {input}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {plugin.output_format && (
                        <div>
                          <h4 className="text-sm font-medium mb-2">Output Format</h4>
                          <Badge variant="outline">
                            <FileCode className="h-3 w-3 mr-1" />
                            {plugin.output_format}
                          </Badge>
                        </div>
                      )}

                      {plugin.dependencies && plugin.dependencies.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium mb-2">Dependencies</h4>
                          <div className="flex flex-wrap gap-2">
                            {plugin.dependencies.map((dep: string) => (
                              <Badge key={dep} variant="secondary">
                                <Package className="h-3 w-3 mr-1" />
                                {dep}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Quick Actions</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-2 sm:grid-cols-2">
                        <Button variant="outline" onClick={handleTest} disabled={isTesting}>
                          <TestTube className="h-4 w-4 mr-2" />
                          {isTesting ? 'Testing...' : 'Test Plugin'}
                        </Button>
                        <Button variant="outline" onClick={handleCopyConfig}>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy Config
                        </Button>
                        <Button variant="outline">
                          <GitBranch className="h-4 w-4 mr-2" />
                          Add to Pipeline
                        </Button>
                        <Button variant="outline">
                          <Bug className="h-4 w-4 mr-2" />
                          Report Issue
                        </Button>
                      </div>

                      {testResult && (
                        <Alert className="mt-4">
                          {testResult.success ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-red-500" />
                          )}
                          <AlertDescription>
                            {testResult.message}
                            {testResult.output && (
                              <pre className="mt-2 text-xs bg-muted p-2 rounded">
                                {JSON.stringify(testResult.output, null, 2)}
                              </pre>
                            )}
                          </AlertDescription>
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Configuration Tab */}
                <TabsContent value="config" className="mt-6 space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Parameters Schema</CardTitle>
                      <CardDescription>
                        JSON Schema defining the configuration parameters
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {plugin.parameters_schema ? (
                        <ScrollArea className="h-[400px] w-full rounded-md border">
                          <pre className="p-4 text-xs">
                            {JSON.stringify(plugin.parameters_schema, null, 2)}
                          </pre>
                        </ScrollArea>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No configuration parameters required
                        </p>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Configuration Templates</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="rounded-lg border p-3">
                          <h4 className="text-sm font-medium mb-2">Basic Configuration</h4>
                          <pre className="text-xs bg-muted p-2 rounded">
{`{
  "plugin": "${plugin.id}",
  "type": "${plugin.type}",
  "params": {}
}`}
                          </pre>
                        </div>
                        <div className="rounded-lg border p-3">
                          <h4 className="text-sm font-medium mb-2">Advanced Configuration</h4>
                          <pre className="text-xs bg-muted p-2 rounded">
{`{
  "plugin": "${plugin.id}",
  "type": "${plugin.type}",
  "params": {
    "option1": "value1",
    "option2": true,
    "option3": 100
  }
}`}
                          </pre>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Usage Tab */}
                <TabsContent value="usage" className="mt-6 space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Use Cases</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium">Data Aggregation</p>
                            <p className="text-xs text-muted-foreground">
                              Perfect for aggregating data by categories or time periods
                            </p>
                          </div>
                        </div>
                        <div className="flex items-start gap-3">
                          <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium">Statistical Analysis</p>
                            <p className="text-xs text-muted-foreground">
                              Calculate means, medians, and other statistical measures
                            </p>
                          </div>
                        </div>
                        <div className="flex items-start gap-3">
                          <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium">Report Generation</p>
                            <p className="text-xs text-muted-foreground">
                              Generate formatted reports for presentations
                            </p>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Compatible Pipelines</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 rounded hover:bg-muted">
                          <span className="text-sm">Geographic Analysis Pipeline</span>
                          <Badge variant="outline" className="text-xs">3 uses</Badge>
                        </div>
                        <div className="flex items-center justify-between p-2 rounded hover:bg-muted">
                          <span className="text-sm">Species Distribution Pipeline</span>
                          <Badge variant="outline" className="text-xs">5 uses</Badge>
                        </div>
                        <div className="flex items-center justify-between p-2 rounded hover:bg-muted">
                          <span className="text-sm">Temporal Analysis Pipeline</span>
                          <Badge variant="outline" className="text-xs">2 uses</Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Examples Tab */}
                <TabsContent value="examples" className="mt-6 space-y-6">
                  {plugin.type === 'widget' && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">Visual Preview</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div className="aspect-video rounded-lg bg-muted flex items-center justify-center">
                            <div className="text-center">
                              <Eye className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
                              <p className="text-sm text-muted-foreground">Widget Preview</p>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline">
                              <Monitor className="h-4 w-4 mr-1" />
                              Desktop
                            </Button>
                            <Button size="sm" variant="outline">
                              <Smartphone className="h-4 w-4 mr-1" />
                              Mobile
                            </Button>
                            <Button size="sm" variant="outline">
                              <Palette className="h-4 w-4 mr-1" />
                              Themes
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Code Examples</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Tabs defaultValue="yaml">
                        <TabsList className="grid w-full grid-cols-2">
                          <TabsTrigger value="yaml">YAML</TabsTrigger>
                          <TabsTrigger value="json">JSON</TabsTrigger>
                        </TabsList>
                        <TabsContent value="yaml">
                          <ScrollArea className="h-[300px] w-full rounded-md border">
                            <pre className="p-4 text-xs">
{`transform:
  - plugin: ${plugin.id}
    name: my_transform
    params:
      input_field: species_count
      output_field: aggregated_data
      method: sum
      group_by:
        - species
        - location`}
                            </pre>
                          </ScrollArea>
                        </TabsContent>
                        <TabsContent value="json">
                          <ScrollArea className="h-[300px] w-full rounded-md border">
                            <pre className="p-4 text-xs">
{`{
  "transform": [
    {
      "plugin": "${plugin.id}",
      "name": "my_transform",
      "params": {
        "input_field": "species_count",
        "output_field": "aggregated_data",
        "method": "sum",
        "group_by": ["species", "location"]
      }
    }
  ]
}`}
                            </pre>
                          </ScrollArea>
                        </TabsContent>
                      </Tabs>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Statistics Tab */}
                <TabsContent value="stats" className="mt-6 space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Usage Statistics</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Total Uses</span>
                          </div>
                          <p className="text-2xl font-bold">{plugin.stats?.usage_count || 0}</p>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Last Used</span>
                          </div>
                          <p className="text-2xl font-bold">
                            {plugin.stats?.last_used || 'Never'}
                          </p>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Avg Execution Time</span>
                          </div>
                          <p className="text-2xl font-bold">
                            {plugin.stats?.avg_execution_time
                              ? `${plugin.stats.avg_execution_time}ms`
                              : 'N/A'}
                          </p>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <AlertCircle className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Error Rate</span>
                          </div>
                          <p className="text-2xl font-bold">
                            {plugin.stats?.error_rate
                              ? `${plugin.stats.error_rate}%`
                              : '0%'}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Performance Metrics</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>CPU Usage</span>
                            <span className="text-muted-foreground">Low</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-green-500" style={{ width: '25%' }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Memory Usage</span>
                            <span className="text-muted-foreground">Moderate</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-yellow-500" style={{ width: '50%' }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Reliability</span>
                            <span className="text-muted-foreground">Excellent</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-green-500" style={{ width: '95%' }} />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">
                  <Book className="h-4 w-4 mr-2" />
                  Documentation
                </Button>
                <Button variant="outline" size="sm">
                  <HelpCircle className="h-4 w-4 mr-2" />
                  Help
                </Button>
              </div>
              <Button onClick={onClose}>Close</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
