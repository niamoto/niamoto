import { cn } from '@/lib/utils'

interface ShowcaseNavProps {
  sections: string[]
  currentSection: number
  onSectionClick: (index: number) => void
}

export function ShowcaseNav({ sections, currentSection, onSectionClick }: ShowcaseNavProps) {
  return (
    <nav className="bg-card/80 backdrop-blur-lg rounded-lg shadow-lg p-3 mx-auto">
      <ul className="flex flex-wrap gap-3 justify-center">
        {sections.map((section, index) => (
          <li key={section}>
            <button
              onClick={() => onSectionClick(index)}
              className={cn(
                "group flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm",
                "hover:bg-accent",
                currentSection === index && "bg-primary/10"
              )}
              aria-label={`Aller à la section ${section}`}
            >
              <div
                className={cn(
                  "w-2 h-2 rounded-full transition-all",
                  currentSection === index
                    ? "bg-primary"
                    : "bg-muted-foreground/30 group-hover:bg-muted-foreground/50"
                )}
              />
              <span
                className={cn(
                  "text-sm font-medium transition-all",
                  currentSection === index
                    ? "text-primary"
                    : "text-muted-foreground group-hover:text-foreground"
                )}
              >
                {section}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
