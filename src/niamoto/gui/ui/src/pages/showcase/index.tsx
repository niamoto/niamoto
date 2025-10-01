import { useEffect, useRef } from 'react'
import { useShowcaseStore } from '@/stores/showcaseStore'
import { OverviewSection } from './components/OverviewSection'
import { PipelineFullSection } from './components/PipelineFullSection'
import { IntegrationSection } from './components/IntegrationSection'
import { CommunitySection } from './components/CommunitySection'
import { PerspectivesSection } from './components/PerspectivesSection'
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
  const hasUserScrolled = useRef(false)
  const isProgrammaticScroll = useRef(false)
  const observerEnabled = useRef(false)
  const scrollContainerRef = useRef<HTMLElement | null>(null)

  const sectionComponents = [
    OverviewSection,
    PipelineFullSection,
    IntegrationSection,
    CommunitySection,
    PerspectivesSection
  ]

  // Find the scroll container (main element) on mount
  useEffect(() => {
    scrollContainerRef.current = document.querySelector('main')
  }, [])

  useEffect(() => {
    // Load configuration on mount
    loadConfiguration()
  }, [loadConfiguration])

  // Scroll to top on mount and detect user scrolling
  useEffect(() => {
    if (!scrollContainerRef.current) return

    const scrollContainer = scrollContainerRef.current

    // Force section to 0 and scroll to top
    setCurrentSection(0)
    isProgrammaticScroll.current = true
    observerEnabled.current = false

    // Clear any hash in URL that might cause scroll
    if (window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname)
    }

    // Force scroll to top
    scrollContainer.scrollTo({ top: 0, left: 0, behavior: 'instant' })

    // Enable observer after layout has settled
    const enableObserverTimeout = setTimeout(() => {
      isProgrammaticScroll.current = false
      observerEnabled.current = true
    }, 500)

    const handleScroll = () => {
      if (!isProgrammaticScroll.current) {
        hasUserScrolled.current = true
      }
    }

    scrollContainer.addEventListener('scroll', handleScroll)

    return () => {
      scrollContainer.removeEventListener('scroll', handleScroll)
      clearTimeout(enableObserverTimeout)
    }
  }, [setCurrentSection])

  useEffect(() => {
    if (!scrollContainerRef.current) return

    // Intersection Observer for auto-updating current section
    const observer = new IntersectionObserver(
      (entries) => {
        if (!observerEnabled.current || !hasUserScrolled.current) return

        // Find the section that's most visible
        const visibleSections = entries
          .filter(entry => entry.isIntersecting)
          .map(entry => ({
            index: sectionRefs.current.indexOf(entry.target as HTMLElement),
            ratio: entry.intersectionRatio
          }))
          .sort((a, b) => b.ratio - a.ratio)

        if (visibleSections.length > 0 && visibleSections[0].index !== -1) {
          setCurrentSection(visibleSections[0].index)
        }
      },
      {
        root: scrollContainerRef.current,
        threshold: [0, 0.25, 0.5, 0.75, 1],
        rootMargin: '-100px 0px -50% 0px'
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
    hasUserScrolled.current = true
    isProgrammaticScroll.current = true

    setCurrentSection(index)
    sectionRefs.current[index]?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })

    // Re-enable observer after smooth scroll completes (~500ms)
    setTimeout(() => {
      isProgrammaticScroll.current = false
    }, 600)
  }

  // Keyboard navigation
  useEffect(() => {
    const totalSections = sectionComponents.length

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input/textarea
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault()
          if (currentSection > 0) {
            scrollToSection(currentSection - 1)
          }
          break
        case 'ArrowRight':
          e.preventDefault()
          if (currentSection < totalSections - 1) {
            scrollToSection(currentSection + 1)
          }
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentSection])

  const sectionTitles = [
    'Vue d\'ensemble',
    'Pipeline',
    'API & Intégration',
    'Communauté',
    'Perspectives'
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
            className="relative min-h-screen flex items-start justify-center py-20"
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
