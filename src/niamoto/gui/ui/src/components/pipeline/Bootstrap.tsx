import React, { useState, useCallback } from 'react';
import { Upload, FileIcon, CheckCircle, AlertCircle, Loader2, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useDropzone } from 'react-dropzone';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import yaml from 'js-yaml';

interface FileInfo {
  name: string;
  size: number;
  type: string;
  file: File;
}

interface AnalysisResult {
  success: boolean;
  analysis: {
    config: any;
    summary: {
      total_files: number;
      total_records: number;
      detected_entities: {
        references?: Array<{ name: string; type: string; records: number; file: string }>;
        data?: Array<{ name: string; type: string; records: number; file: string }>;
        shapes?: Array<{ name: string; type: string; records: number; file: string }>;
      };
    };
    confidence: number;
    validation: {
      valid: boolean;
      issues: string[];
      warnings: string[];
    };
    profiles: Array<{
      filename: string;
      type: string;
      name: string;
      records: number;
      columns: number;
      confidence: number;
    }>;
  };
}

interface GeneratedConfig {
  import: any;
  transform: any;
  export: any;
}

export const Bootstrap: React.FC = () => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [generatedConfig, setGeneratedConfig] = useState<GeneratedConfig | null>(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      name: file.name,
      size: file.size,
      type: file.type || 'application/octet-stream',
      file: file
    }));
    setFiles(prev => [...prev, ...newFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json', '.geojson'],
      'application/vnd.ms-excel': ['.xls', '.xlsx'],
      'application/x-shapefile': ['.shp', '.dbf', '.shx', '.prj'],
      'application/geopackage+sqlite3': ['.gpkg']
    }
  });

  const analyzeFiles = async () => {
    if (files.length === 0) return;

    setIsAnalyzing(true);
    setError(null);

    const formData = new FormData();
    files.forEach(fileInfo => {
      formData.append('files', fileInfo.file, fileInfo.name);
    });

    try {
      const response = await fetch('/api/bootstrap/analyze', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const result = await response.json();
      setAnalysisResult(result);
      setActiveTab('analysis');

      // Generate configuration
      await generateConfiguration();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const generateConfiguration = async () => {
    const formData = new FormData();
    files.forEach(fileInfo => {
      formData.append('files', fileInfo.file, fileInfo.name);
    });

    try {
      const response = await fetch('/api/bootstrap/generate-config', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Configuration generation failed: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success) {
        setGeneratedConfig(result.configs);
      }
    } catch (err) {
      console.error('Failed to generate configuration:', err);
    }
  };

  const saveConfiguration = async () => {
    if (!generatedConfig) return;

    setIsSaving(true);
    try {
      const response = await fetch('/api/bootstrap/save-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(generatedConfig)
      });

      if (!response.ok) {
        throw new Error('Failed to save configuration');
      }

      setActiveTab('complete');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setIsSaving(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileTypeColor = (type: string) => {
    if (type === 'hierarchical') return 'text-green-600';
    if (type === 'spatial') return 'text-blue-600';
    if (type === 'factual') return 'text-orange-600';
    if (type === 'statistical') return 'text-purple-600';
    return 'text-gray-600';
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Wand2 className="h-8 w-8 text-primary" />
          Bootstrap Data Pipeline
        </h1>
        <p className="text-muted-foreground mt-2">
          Automatically detect and configure your data pipeline from files
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload">
            1. Upload Files
          </TabsTrigger>
          <TabsTrigger value="analysis" disabled={!analysisResult}>
            2. Analysis
          </TabsTrigger>
          <TabsTrigger value="config" disabled={!generatedConfig}>
            3. Configuration
          </TabsTrigger>
          <TabsTrigger value="complete" disabled={!generatedConfig}>
            4. Complete
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upload Your Data Files</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                {isDragActive ? (
                  <p className="text-lg">Drop files here...</p>
                ) : (
                  <>
                    <p className="text-lg mb-2">
                      Drag & drop your data files here
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Supports: CSV, Excel, GeoJSON, Shapefile, GeoPackage
                    </p>
                  </>
                )}
              </div>

              {files.length > 0 && (
                <div className="mt-6 space-y-2">
                  <h3 className="font-semibold mb-2">Selected Files ({files.length})</h3>
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <FileIcon className="h-4 w-4 text-gray-500" />
                        <span className="text-sm">{file.name}</span>
                      </div>
                      <span className="text-xs text-gray-500">{formatBytes(file.size)}</span>
                    </div>
                  ))}

                  <Button
                    onClick={analyzeFiles}
                    disabled={isAnalyzing}
                    className="w-full mt-4"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Wand2 className="mr-2 h-4 w-4" />
                        Analyze Files
                      </>
                    )}
                  </Button>
                </div>
              )}

              {error && (
                <Alert variant="destructive" className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4">
          {analysisResult && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    Analysis Results
                    <Badge variant="default">
                      {Math.round(analysisResult.analysis.confidence * 100)}% Confidence
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="text-center">
                      <div className="text-2xl font-bold">
                        {analysisResult.analysis.summary.total_files}
                      </div>
                      <div className="text-sm text-muted-foreground">Files Analyzed</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold">
                        {analysisResult.analysis.summary.total_records.toLocaleString()}
                      </div>
                      <div className="text-sm text-muted-foreground">Total Records</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold">
                        {Object.keys(analysisResult.analysis.summary.detected_entities).length}
                      </div>
                      <div className="text-sm text-muted-foreground">Entity Types</div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold mb-2">Detected Files</h3>
                      <div className="space-y-2">
                        {analysisResult.analysis.profiles.map((profile, index) => (
                          <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                            <div className="flex items-center gap-3">
                              <FileIcon className="h-4 w-4 text-gray-500" />
                              <span className="font-medium">{profile.filename}</span>
                              <Badge variant="outline" className={getFileTypeColor(profile.type)}>
                                {profile.type}
                              </Badge>
                            </div>
                            <div className="text-sm text-gray-500">
                              {profile.records.toLocaleString()} records • {profile.columns} columns
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {analysisResult.analysis.validation.warnings.length > 0 && (
                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          <div className="font-semibold mb-1">Warnings:</div>
                          <ul className="list-disc list-inside text-sm">
                            {analysisResult.analysis.validation.warnings.map((warning, index) => (
                              <li key={index}>{warning}</li>
                            ))}
                          </ul>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end">
                <Button onClick={() => setActiveTab('config')}>
                  Review Configuration →
                </Button>
              </div>
            </>
          )}
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          {generatedConfig && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Generated Configuration</CardTitle>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="import">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="import">import.yml</TabsTrigger>
                      <TabsTrigger value="transform">transform.yml</TabsTrigger>
                      <TabsTrigger value="export">export.yml</TabsTrigger>
                    </TabsList>

                    <TabsContent value="import">
                      <ScrollArea className="h-96 w-full rounded-md border p-4">
                        <SyntaxHighlighter
                          language="yaml"
                          style={vscDarkPlus}
                          customStyle={{ background: 'transparent' }}
                        >
                          {yaml.dump(generatedConfig.import)}
                        </SyntaxHighlighter>
                      </ScrollArea>
                    </TabsContent>

                    <TabsContent value="transform">
                      <ScrollArea className="h-96 w-full rounded-md border p-4">
                        <SyntaxHighlighter
                          language="yaml"
                          style={vscDarkPlus}
                          customStyle={{ background: 'transparent' }}
                        >
                          {yaml.dump(generatedConfig.transform)}
                        </SyntaxHighlighter>
                      </ScrollArea>
                    </TabsContent>

                    <TabsContent value="export">
                      <ScrollArea className="h-96 w-full rounded-md border p-4">
                        <SyntaxHighlighter
                          language="yaml"
                          style={vscDarkPlus}
                          customStyle={{ background: 'transparent' }}
                        >
                          {yaml.dump(generatedConfig.export)}
                        </SyntaxHighlighter>
                      </ScrollArea>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>

              <div className="flex justify-end gap-4">
                <Button variant="outline" onClick={() => setActiveTab('analysis')}>
                  ← Back
                </Button>
                <Button onClick={saveConfiguration} disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="mr-2 h-4 w-4" />
                      Save & Create Instance
                    </>
                  )}
                </Button>
              </div>
            </>
          )}
        </TabsContent>

        <TabsContent value="complete">
          <Card>
            <CardContent className="text-center py-12">
              <CheckCircle className="mx-auto h-16 w-16 text-green-500 mb-4" />
              <h2 className="text-2xl font-bold mb-2">Instance Created Successfully!</h2>
              <p className="text-muted-foreground mb-6">
                Your Niamoto instance has been configured and is ready to use.
              </p>

              <div className="bg-gray-50 rounded-lg p-6 text-left max-w-md mx-auto">
                <h3 className="font-semibold mb-3">Next Steps:</h3>
                <ol className="space-y-2 text-sm">
                  <li>1. Run <code className="bg-gray-200 px-1 rounded">niamoto import</code> to import your data</li>
                  <li>2. Run <code className="bg-gray-200 px-1 rounded">niamoto transform</code> to process the data</li>
                  <li>3. Run <code className="bg-gray-200 px-1 rounded">niamoto export</code> to generate the site</li>
                  <li>4. View your site at <a href="http://localhost:8000" className="text-primary hover:underline">http://localhost:8000</a></li>
                </ol>
              </div>

              <div className="mt-8 space-x-4">
                <Button variant="outline" onClick={() => {
                  setFiles([]);
                  setAnalysisResult(null);
                  setGeneratedConfig(null);
                  setActiveTab('upload');
                }}>
                  Start New Bootstrap
                </Button>
                <Button>
                  Go to Dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
