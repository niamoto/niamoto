import { useEffect, useRef } from 'react'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { HeroSection } from './components/HeroSection'
import { ArchitectureSection } from './components/ArchitectureSection'
import { PipelineSection } from './components/PipelineSection'
import { ImportDemo } from './components/ImportDemo'
import { TransformDemo } from './components/TransformDemo'
import { ExportDemo } from './components/ExportDemo'
import { UseCasesSection } from './components/UseCasesSection'
import { CallToAction } from './components/CallToAction'
import { ShowcaseNav } from './components/ShowcaseNav'
import { Progress } from '@/components/ui/progress'

export default function ShowcasePage() {
  const {
    currentSection,
    sections,
    setCurrentSection,
    loadConfiguration
  } = useShowcaseStore()

  const sectionRefs = useRef<(HTMLElement | null)[]>([])

  useEffect(() => {
    // Load configuration on mount
    loadConfiguration()
  }, [loadConfiguration])

  useEffect(() => {
    // Intersection Observer for auto-updating current section
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = sectionRefs.current.indexOf(entry.target as HTMLElement)
            if (index !== -1) {
              setCurrentSection(index)
            }
          }
        })
      },
      {
        threshold: 0.5,
        rootMargin: '-20% 0px -60% 0px'
      }
    )

    sectionRefs.current.forEach(ref => {
      if (ref) observer.observe(ref)
    })

    return () => {
      sectionRefs.current.forEach(ref => {
        if (ref) observer.unobserve(ref)
      })
    }
  }, [setCurrentSection])

  const scrollToSection = (index: number) => {
    sectionRefs.current[index]?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
    setCurrentSection(index)
  }

  const sectionComponents = [
    HeroSection,
    ArchitectureSection,
    PipelineSection,
    ImportDemo,
    TransformDemo,
    ExportDemo,
    UseCasesSection,
    CallToAction
  ]

  const sectionTitles = [
    'Accueil',
    'Architecture',
    'Pipeline',
    'Import',
    'Transform',
    'Export',
    'Cas d\'usage',
    'Commencer'
  ]

  return (
    <div className="relative min-h-screen bg-gradient-to-b from-background to-secondary/10">
      {/* Progress Bar */}
      <div className="fixed top-0 left-0 right-0 z-50">
        <Progress
          value={(currentSection + 1) / sections.length * 100}
          className="h-1 rounded-none"
        />
      </div>

      {/* Fixed Navigation - positioned under the page header */}
      {/* Note: ml-[250px] compensates for the sidebar width to center in the main content area */}
      <div className="fixed top-24 left-0 right-0 z-40">
        <div className="ml-[250px] flex justify-center">
          <ShowcaseNav
            sections={sectionTitles}
            currentSection={currentSection}
            onSectionClick={scrollToSection}
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="container max-w-7xl mx-auto pt-12">
        {/* Sections */}
        {sectionComponents.map((Component, index) => (
          <section
            key={sections[index]}
            ref={el => { sectionRefs.current[index] = el }}
            id={sections[index]}
            className="min-h-screen flex items-center justify-center py-20"
          >
            <Component />
          </section>
        ))}
      </div>

      {/* Floating Action Button */}
      {currentSection > 0 && (
        <button
          onClick={() => scrollToSection(0)}
          className="fixed bottom-8 right-8 z-40 p-3 bg-primary text-primary-foreground rounded-full shadow-lg hover:scale-110 transition-transform"
          aria-label="Retour en haut"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="19" x2="12" y2="5"></line>
            <polyline points="5 12 12 5 19 12"></polyline>
          </svg>
        </button>
      )}
    </div>
  )
}
