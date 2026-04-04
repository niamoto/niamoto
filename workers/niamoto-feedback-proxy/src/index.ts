interface Env {
  FEEDBACK_BUCKET: R2Bucket
  GITHUB_TOKEN: string
  FEEDBACK_API_KEY: string
  R2_PUBLIC_URL: string
  GITHUB_REPO: string
}

interface FeedbackPayload {
  type: 'bug' | 'suggestion' | 'question'
  title: string
  description?: string
  context: {
    app_version: string
    os: string
    current_page: string
    runtime_mode: string
    theme: string
    language: string
    window_size: string
    timestamp: string
    diagnostic?: Record<string, unknown>
    recent_errors?: Array<{ message: string; stack?: string; timestamp: string }>
  }
}

const ALLOWED_ORIGINS = [
  'tauri://localhost',
  'https://tauri.localhost',
  'http://localhost:1420',
  'http://localhost:1421',
  'http://127.0.0.1:1420',
  'http://127.0.0.1:1421',
]

const TYPE_EMOJI: Record<string, string> = {
  bug: '🐛',
  suggestion: '💡',
  question: '❓',
}

const TYPE_LABEL: Record<string, string> = {
  bug: 'Bug Report',
  suggestion: 'Suggestion',
  question: 'Question',
}

function corsHeaders(request: Request): Record<string, string> {
  const origin = request.headers.get('Origin') || ''
  if (ALLOWED_ORIGINS.includes(origin)) {
    return {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Feedback-Key',
      'Access-Control-Max-Age': '86400',
    }
  }
  return {}
}

function sanitizeMarkdown(text: string): string {
  return text
    .replace(/@(\w)/g, '@ $1')  // break @mentions
    .replace(/#(\d)/g, '# $1')  // break #refs
    .replace(/\[([^\]]*)\]\(/g, '\\[$1\\](') // escape markdown links
}

function generateId(): string {
  return crypto.randomUUID().slice(0, 12)
}

function formatDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function buildIssueBody(
  payload: FeedbackPayload,
  screenshotUrl?: string
): string {
  const emoji = TYPE_EMOJI[payload.type] || '📝'
  const label = TYPE_LABEL[payload.type] || payload.type

  let body = `## ${emoji} ${label}\n\n`

  if (payload.description) {
    body += `### Description\n${sanitizeMarkdown(payload.description)}\n\n`
  }

  if (screenshotUrl) {
    body += `### Screenshot\n![screenshot](${screenshotUrl})\n\n`
  }

  const ctx = payload.context
  body += `### Contexte\n`
  body += `| | |\n|-|-|\n`
  body += `| Version | ${ctx.app_version} |\n`
  body += `| OS | ${ctx.os} |\n`
  body += `| Page | ${ctx.current_page} |\n`
  body += `| Mode | ${ctx.runtime_mode} |\n`
  body += `| Thème | ${ctx.theme} |\n`
  body += `| Langue | ${ctx.language} |\n`
  body += `| Fenêtre | ${ctx.window_size} |\n`

  if (ctx.recent_errors && ctx.recent_errors.length > 0) {
    // Escape backtick sequences that would break the code fence
    const escapeCodeFence = (s: string) => s.replace(/`{3,}/g, '`` `')
    body += `\n### Erreurs console\n\`\`\`\n`
    for (const err of ctx.recent_errors.slice(0, 5)) {
      body += `[${err.timestamp}] ${escapeCodeFence(err.message)}\n`
      if (err.stack) body += `${escapeCodeFence(err.stack)}\n`
    }
    body += `\`\`\`\n`
  }

  body += `\n---\n*Envoyé depuis Niamoto Desktop v${ctx.app_version}*`

  return body
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(request) })
    }

    // Only POST /feedback
    const url = new URL(request.url)
    if (request.method !== 'POST' || url.pathname !== '/feedback') {
      return Response.json(
        { error: 'not_found' },
        { status: 404, headers: corsHeaders(request) }
      )
    }

    // Auth check
    const apiKey = request.headers.get('X-Feedback-Key')
    if (!apiKey || apiKey !== env.FEEDBACK_API_KEY) {
      return Response.json(
        { error: 'unauthorized' },
        { status: 401, headers: corsHeaders(request) }
      )
    }

    // Size check (6MB max)
    const contentLength = Number(request.headers.get('Content-Length') || 0)
    if (contentLength > 6 * 1024 * 1024) {
      return Response.json(
        { error: 'payload_too_large' },
        { status: 413, headers: corsHeaders(request) }
      )
    }

    try {
      // Parse multipart/form-data
      const formData = await request.formData()
      const payloadRaw = formData.get('payload')
      if (!payloadRaw || typeof payloadRaw !== 'string') {
        return Response.json(
          { error: 'missing_payload' },
          { status: 400, headers: corsHeaders(request) }
        )
      }

      const payload: FeedbackPayload = JSON.parse(payloadRaw)

      // Validate required fields
      if (!payload.title || payload.title.trim().length === 0) {
        return Response.json(
          { error: 'missing_title' },
          { status: 400, headers: corsHeaders(request) }
        )
      }
      if (!['bug', 'suggestion', 'question'].includes(payload.type)) {
        return Response.json(
          { error: 'invalid_type' },
          { status: 400, headers: corsHeaders(request) }
        )
      }

      // Truncate fields
      payload.title = payload.title.slice(0, 200)
      if (payload.description) {
        payload.description = payload.description.slice(0, 5000)
      }

      // Upload screenshot to R2 if present
      let screenshotUrl: string | undefined
      let screenshotUploaded = false
      const screenshotFile = formData.get('screenshot')

      if (screenshotFile && screenshotFile instanceof File) {
        if (screenshotFile.size > 5 * 1024 * 1024) {
          // Skip screenshot silently if too large
        } else if (!screenshotFile.type.startsWith('image/jpeg')) {
          // Skip non-JPEG
        } else {
          try {
            const filename = `${formatDate()}-${generateId()}.jpg`
            await env.FEEDBACK_BUCKET.put(filename, screenshotFile.stream(), {
              httpMetadata: { contentType: 'image/jpeg' },
            })
            screenshotUrl = `${env.R2_PUBLIC_URL}/${filename}`
            screenshotUploaded = true
          } catch {
            // R2 upload failed — continue without screenshot
          }
        }
      }

      // Build Issue body
      const issueBody = buildIssueBody(payload, screenshotUrl)

      // Create GitHub Issue
      const labels = ['feedback', `feedback:${payload.type}`, 'from:app']
      const ghResponse = await fetch(
        `https://api.github.com/repos/${env.GITHUB_REPO}/issues`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${env.GITHUB_TOKEN}`,
            Accept: 'application/vnd.github+json',
            'User-Agent': 'niamoto-feedback-proxy/1.0',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: `[${TYPE_LABEL[payload.type]}] ${sanitizeMarkdown(payload.title)}`,
            body: issueBody,
            labels,
          }),
        }
      )

      if (!ghResponse.ok) {
        console.error('GitHub API error:', await ghResponse.text())
        return Response.json(
          { error: 'github_error' },
          { status: 502, headers: corsHeaders(request) }
        )
      }

      const ghData = (await ghResponse.json()) as { html_url: string }

      return Response.json(
        {
          success: true,
          issue_url: ghData.html_url,
          screenshot_uploaded: screenshotUploaded,
        },
        { status: 201, headers: corsHeaders(request) }
      )
    } catch (err) {
      console.error('Worker error:', err)
      return Response.json(
        { error: 'internal_error' },
        { status: 500, headers: corsHeaders(request) }
      )
    }
  },
}
