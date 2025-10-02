import { useTranslation } from 'react-i18next'
import { FileText, Book, Code, ExternalLink, Search, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

export function Documentation() {
  const { t } = useTranslation()

  const docSections = [
    {
      title: 'Getting Started',
      description: 'Learn the basics of Niamoto',
      items: [
        { title: 'Installation', href: '#' },
        { title: 'Quick Start Guide', href: '#' },
        { title: 'Project Structure', href: '#' },
        { title: 'Basic Concepts', href: '#' }
      ]
    },
    {
      title: 'Data Pipeline',
      description: 'Understanding the data flow',
      items: [
        { title: 'Import Configuration', href: '#' },
        { title: 'Transform Pipeline', href: '#' },
        { title: 'Export Process', href: '#' },
        { title: 'Widget System', href: '#' }
      ]
    },
    {
      title: 'Plugin Development',
      description: 'Create custom plugins',
      items: [
        { title: 'Plugin Architecture', href: '#' },
        { title: 'Creating Transformers', href: '#' },
        { title: 'Building Widgets', href: '#' },
        { title: 'Custom Exporters', href: '#' }
      ]
    },
    {
      title: 'API Reference',
      description: 'Complete API documentation',
      items: [
        { title: 'Core API', href: '#' },
        { title: 'Plugin API', href: '#' },
        { title: 'Database Schema', href: '#' },
        { title: 'CLI Commands', href: '#' }
      ]
    }
  ]

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('documentation.title', 'Documentation')}
          </h1>
          <p className="text-muted-foreground">
            {t('documentation.description', 'Learn how to use Niamoto effectively')}
          </p>
        </div>
        <Badge variant="secondary">
          {t('common.coming_soon', 'Coming Soon')}
        </Badge>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={t('documentation.search_placeholder', 'Search documentation...')}
          className="pl-10"
        />
      </div>

      {/* Quick Links */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Book className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">{t('documentation.tutorials', 'Tutorials')}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('documentation.tutorials_desc', 'Step-by-step guides to get you started')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Code className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">{t('documentation.examples', 'Examples')}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('documentation.examples_desc', 'Real-world examples and use cases')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">{t('documentation.api_reference', 'API Reference')}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('documentation.api_reference_desc', 'Complete technical documentation')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Documentation Sections */}
      <div className="grid gap-6 md:grid-cols-2">
        {docSections.map((section) => (
          <Card key={section.title}>
            <CardHeader>
              <CardTitle>{section.title}</CardTitle>
              <CardDescription>{section.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {section.items.map((item) => (
                  <a
                    key={item.title}
                    href={item.href}
                    className="flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors hover:bg-muted"
                  >
                    <span>{item.title}</span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* External Resources */}
      <Card>
        <CardHeader>
          <CardTitle>{t('documentation.external_resources', 'External Resources')}</CardTitle>
          <CardDescription>
            {t('documentation.external_resources_desc', 'Additional resources and community links')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm">
              <ExternalLink className="mr-2 h-4 w-4" />
              GitHub Repository
            </Button>
            <Button variant="outline" size="sm">
              <ExternalLink className="mr-2 h-4 w-4" />
              Community Forum
            </Button>
            <Button variant="outline" size="sm">
              <ExternalLink className="mr-2 h-4 w-4" />
              Video Tutorials
            </Button>
            <Button variant="outline" size="sm">
              <ExternalLink className="mr-2 h-4 w-4" />
              Blog
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
