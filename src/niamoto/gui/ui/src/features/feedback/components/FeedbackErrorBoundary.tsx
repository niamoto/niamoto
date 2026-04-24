import { Component, type ErrorInfo, type ReactNode } from 'react'
import i18n from '@/i18n'
import { recordCrash } from '../lib/crash-tracker'
import { requestBugReport } from '../lib/bug-report-bridge'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  errorMessage?: string
  componentName?: string
}

function getComponentStackLines(componentStack?: string | null): string[] {
  return componentStack
    ?.split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('at '))
    .map((line) => line.replace(/^at /, ''))
    ?? []
}

function getUsefulComponentName(componentStack?: string | null): string {
  const stackLines = getComponentStackLines(componentStack)
  const usefulLine = stackLines.find((line) => {
    const name = line.split(' ')[0]
    return !!name && !/^[a-z]/.test(name)
  })
  return usefulLine?.split(' ')[0] ?? stackLines[0]?.split(' ')[0] ?? 'Unknown'
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
    const componentStack = getComponentStackLines(info.componentStack)
    const componentName = getUsefulComponentName(info.componentStack)

    recordCrash(componentName, error, componentStack)
    this.setState({ componentName })
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      errorMessage: undefined,
      componentName: undefined,
    })
  }

  private handleReportBug = () => {
    const componentName = this.state.componentName || 'Unknown'
    const errorMessage = this.state.errorMessage || 'Unknown error'

    requestBugReport({
      title: i18n.t('feedback:prefill_crash_title', { component: componentName }),
      description: i18n.t('feedback:prefill_crash_description', {
        component: componentName,
        error: errorMessage,
      }),
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full items-center justify-center p-6">
          <div className="w-full max-w-md rounded-theme-md border bg-card p-5 text-center shadow-sm">
            <h2 className="text-sm font-semibold text-foreground">
              {i18n.t('feedback:crash_screen_title')}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {i18n.t('feedback:crash_screen_description')}
            </p>
            {this.state.errorMessage && (
              <p className="mt-3 text-xs text-muted-foreground">{this.state.errorMessage}</p>
            )}
            <div className="mt-4 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={this.handleRetry}
                className="inline-flex h-9 items-center justify-center rounded-theme-sm border px-4 text-sm font-medium transition-theme-fast hover:bg-accent hover:text-accent-foreground"
              >
                {i18n.t('feedback:crash_screen_retry')}
              </button>
              <button
                type="button"
                onClick={this.handleReportBug}
                className="inline-flex h-9 items-center justify-center rounded-theme-sm border px-4 text-sm font-medium transition-theme-fast hover:bg-accent hover:text-accent-foreground"
              >
                {i18n.t('feedback:report_bug_cta')}
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
