import { Link } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNavigationStore } from '@/stores/navigationStore'

interface BreadcrumbNavProps {
  className?: string
}

export function BreadcrumbNav({ className }: BreadcrumbNavProps) {
  const { breadcrumbs } = useNavigationStore()

  if (!breadcrumbs || breadcrumbs.length === 0) {
    return null
  }

  return (
    <nav
      className={cn(
        'flex h-9 items-center border-b bg-muted/40 px-4',
        className
      )}
      aria-label="Breadcrumb"
    >
      <ol className="flex items-center gap-1 text-sm text-muted-foreground">
        {/* Home link */}
        <li>
          <Link
            to="/"
            className="flex items-center gap-1 hover:text-foreground transition-colors"
          >
            <Home className="h-3 w-3" />
          </Link>
        </li>

        {/* Breadcrumb items */}
        {breadcrumbs.map((crumb, index) => {
          const isLast = index === breadcrumbs.length - 1

          return (
            <li key={index} className="flex items-center gap-1">
              <ChevronRight className="h-3 w-3" />
              {crumb.path && !isLast ? (
                <Link
                  to={crumb.path}
                  className="hover:text-foreground transition-colors"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className={cn(isLast && 'text-foreground font-medium')}>
                  {crumb.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
