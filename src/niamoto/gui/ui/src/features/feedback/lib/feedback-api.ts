import type { FeedbackPayload, FeedbackResponse } from '../types'
import { saveTextFileWithNativeDialog } from '@/shared/desktop/saveTextFile'

const GITHUB_NEW_ISSUE_URL = 'https://github.com/niamoto/niamoto/issues/new'
const MAX_GITHUB_ISSUE_URL_LENGTH = 7500

const TYPE_LABEL: Record<FeedbackPayload['type'], string> = {
  bug: 'Bug',
  suggestion: 'Suggestion',
  question: 'Question',
}

interface FeedbackSubmission {
  payload: FeedbackPayload
  screenshot?: Blob | null
}

export type FeedbackDownloadResult =
  | { status: 'saved'; filename: string; path?: string }
  | { status: 'downloaded'; filename: string }
  | { status: 'cancelled'; filename: string }

interface ScreenshotData {
  filename: 'feedback.jpg'
  mime_type: string
  size_bytes: number
  data_url: string
}

export async function sendFeedback({ payload, screenshot }: FeedbackSubmission): Promise<FeedbackResponse> {
  const screenshotData = screenshot ? await buildScreenshotData(screenshot) : null
  const markdown = buildMarkdownReport(payload, screenshotData)
  const githubBody = buildGitHubIssueBody(payload, Boolean(screenshotData))
  const githubIssueUrl = buildGitHubIssueUrl(payload, githubBody)
  const reportFilename = buildReportFilename(payload.title)

  return {
    success: true,
    report_downloaded: false,
    report_format: 'markdown',
    report_filename: reportFilename,
    report_content: markdown,
    screenshot_included: Boolean(screenshotData),
    github_issue_url: githubIssueUrl,
  }
}

export function downloadFeedbackReport(
  report: Pick<FeedbackResponse, 'report_content' | 'report_filename'>,
): Promise<FeedbackDownloadResult> {
  return saveFeedbackReport(report)
}

async function saveFeedbackReport(
  report: Pick<FeedbackResponse, 'report_content' | 'report_filename'>,
): Promise<FeedbackDownloadResult> {
  const nativeResult = await saveTextFileWithNativeDialog({
    filename: report.report_filename,
    contents: report.report_content,
  })

  if (nativeResult.status === 'saved') {
    return {
      status: 'saved',
      filename: report.report_filename,
      path: nativeResult.path,
    }
  }

  if (nativeResult.status === 'cancelled') {
    return {
      status: 'cancelled',
      filename: report.report_filename,
    }
  }

  downloadMarkdownReport(report.report_content, report.report_filename)
  return {
    status: 'downloaded',
    filename: report.report_filename,
  }
}

async function buildScreenshotData(screenshot: Blob): Promise<ScreenshotData> {
  return {
    filename: 'feedback.jpg',
    mime_type: screenshot.type || 'application/octet-stream',
    size_bytes: screenshot.size,
    data_url: await blobToDataUrl(screenshot),
  }
}

function buildMarkdownReport(payload: FeedbackPayload, screenshot: ScreenshotData | null): string {
  const technicalDetails = {
    source: 'niamoto-local-feedback-report',
    generated_at: new Date().toISOString(),
    payload,
    screenshot: screenshot
      ? {
          filename: screenshot.filename,
          mime_type: screenshot.mime_type,
          size_bytes: screenshot.size_bytes,
        }
      : null,
  }

  return [
    `# ${cleanMarkdownLine(payload.title)}`,
    '',
    '> This report was generated locally by Niamoto. No feedback was sent automatically.',
    '',
    ...descriptionSection(payload.description),
    ...contextSection(payload),
    ...diagnosticSections(payload),
    ...screenshotSection(screenshot),
    '## Technical details',
    '',
    '```json',
    escapeCodeFence(JSON.stringify(technicalDetails, null, 2)),
    '```',
    '',
  ].join('\n')
}

function buildGitHubIssueBody(payload: FeedbackPayload, hasScreenshot: boolean): string {
  return [
    ...descriptionSection(payload.description),
    ...contextSection(payload),
    hasScreenshot
      ? [
          '## Screenshot',
          '',
          'A screenshot was included in the downloaded report. Please attach it manually when useful.',
          '',
        ]
      : [],
    ...diagnosticSections(payload, { compact: true }),
  ].flat().join('\n')
}

function descriptionSection(description: string | undefined): string[] {
  return [
    '## Description',
    '',
    description?.trim() || '_No description provided._',
    '',
  ]
}

function contextSection(payload: FeedbackPayload): string[] {
  const { context } = payload
  const rows = [
    ['Type', TYPE_LABEL[payload.type]],
    ['Version', context.app_version],
    ['Page', `\`${context.current_page}\``],
    ['Runtime', context.runtime_mode],
    ['Language', context.language],
    ['Theme', context.theme],
    ['Window', context.window_size],
    ['Generated at', context.timestamp],
  ]

  if (context.screen_size) rows.push(['Screen', context.screen_size])
  if (context.memory) rows.push(['Memory', context.memory])
  if (context.backend_status) rows.push(['Backend', context.backend_status])

  return [
    '## Context',
    '',
    '| Field | Value |',
    '| --- | --- |',
    ...rows.map(([field, value]) => `| ${escapeTableCell(field)} | ${escapeTableCell(value)} |`),
    '',
  ]
}

function diagnosticSections(
  payload: FeedbackPayload,
  options: { compact?: boolean } = {},
): string[] {
  const { context } = payload
  const sections: string[] = []

  if (context.navigation_history?.length) {
    sections.push('## Navigation history', '')
    for (const item of context.navigation_history.slice(-5)) {
      sections.push(`- \`${item.path}\` (${item.timestamp})`)
    }
    sections.push('')
  }

  if (context.failed_requests?.length) {
    sections.push('## Failed requests', '')
    for (const request of context.failed_requests.slice(-5)) {
      sections.push(`- \`${request.url}\` -> ${request.status} (${request.duration}ms, ${request.timestamp})`)
    }
    sections.push('')
  }

  if (context.recent_errors?.length) {
    sections.push('## Recent errors', '', '```text')
    for (const error of context.recent_errors.slice(0, options.compact ? 3 : 5)) {
      sections.push(`[${error.timestamp}] ${escapeCodeFence(error.message)}`)
      if (!options.compact && error.stack) {
        sections.push(escapeCodeFence(error.stack))
      }
    }
    sections.push('```', '')
  }

  if (context.crashes?.length) {
    sections.push('## Crashes', '')
    for (const crash of context.crashes) {
      sections.push(`- **${cleanMarkdownLine(crash.component)}**: ${cleanMarkdownLine(crash.error)} (${crash.timestamp})`)
    }
    sections.push('')
  }

  if (context.diagnostic && !options.compact) {
    sections.push('## Backend diagnostic', '', '```json')
    sections.push(escapeCodeFence(JSON.stringify(context.diagnostic, null, 2)))
    sections.push('```', '')
  }

  return sections
}

function screenshotSection(screenshot: ScreenshotData | null): string[] {
  if (!screenshot) return []

  return [
    '## Screenshot',
    '',
    'Attach the screenshot manually when creating a GitHub issue. It is embedded below for local review.',
    '',
    `<img alt="Niamoto feedback screenshot" src="${screenshot.data_url}" />`,
    '',
  ]
}

function buildGitHubIssueUrl(payload: FeedbackPayload, body: string): string | undefined {
  const url = new URL(GITHUB_NEW_ISSUE_URL)
  url.searchParams.set('title', `[${TYPE_LABEL[payload.type]}] ${payload.title}`)
  url.searchParams.set('body', body)
  url.searchParams.set('labels', `feedback,feedback:${payload.type}`)

  const issueUrl = url.toString()
  return issueUrl.length <= MAX_GITHUB_ISSUE_URL_LENGTH ? issueUrl : undefined
}

async function blobToDataUrl(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer()
  const bytes = new Uint8Array(buffer)
  const chunkSize = 0x8000
  let binary = ''

  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize))
  }

  return `data:${blob.type || 'application/octet-stream'};base64,${btoa(binary)}`
}

function buildReportFilename(title: string): string {
  const timestamp = new Date()
    .toISOString()
    .replace(/[:.]/g, '-')
    .replace('T', '-')
    .replace('Z', '')
  const slug = title
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)

  return `niamoto-feedback-${timestamp}${slug ? `-${slug}` : ''}.md`
}

function downloadMarkdownReport(markdown: string, filename: string): void {
  const blob = new Blob([markdown], {
    type: 'text/markdown;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function cleanMarkdownLine(value: string): string {
  return value.replace(/[\r\n]+/g, ' ').trim()
}

function escapeTableCell(value: string): string {
  return cleanMarkdownLine(value).replace(/\|/g, '\\|')
}

function escapeCodeFence(value: string): string {
  return value.replace(/```/g, '`` `')
}
