import { Component, type ErrorInfo, type ReactNode } from 'react'
import { recordCrash } from '../lib/crash-tracker'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  errorMessage?: string
}

/**
 * Lightweight ErrorBoundary that records React component crashes
 * for inclusion in feedback reports. Re-throws to let the UI
 * handle the error display (or a parent boundary).
 */
export class FeedbackErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    const componentName = info.componentStack
      ?.split('\n')
      .find((line) => line.trim().startsWith('at '))
      ?.trim()
      .replace(/^at /, '')
      .split(' ')[0] || 'Unknown'

    recordCrash(componentName, error)
  }

  private handleRetry = () => {
    this.setState({ hasError: false, errorMessage: undefined })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full items-center justify-center p-6">
          <div className="w-full max-w-md rounded-theme-md border bg-card p-5 text-center shadow-sm">
            <h2 className="text-sm font-semibold text-foreground">This screen crashed</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              The error was recorded for feedback reporting. You can try again or navigate to another section.
            </p>
            {this.state.errorMessage && (
              <p className="mt-3 text-xs text-muted-foreground">{this.state.errorMessage}</p>
            )}
            <button
              type="button"
              onClick={this.handleRetry}
              className="mt-4 inline-flex h-9 items-center justify-center rounded-theme-sm border px-4 text-sm font-medium transition-theme-fast hover:bg-accent hover:text-accent-foreground"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
