import React, { forwardRef, useMemo, type CSSProperties, type ReactNode } from 'react'

const ALLOWED_TAGS = new Set([
  'a',
  'blockquote',
  'br',
  'code',
  'del',
  'div',
  'em',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'img',
  'li',
  'ol',
  'p',
  'pre',
  'span',
  'strong',
  'table',
  'tbody',
  'td',
  'th',
  'thead',
  'tr',
  'ul',
])

const DROPPED_TAGS = new Set(['script', 'style', 'iframe', 'object', 'embed'])
const VOID_TAGS = new Set(['br', 'hr', 'img'])

function isSafeUrl(value: string): boolean {
  return (
    value.startsWith('/')
    || value.startsWith('#')
    || value.startsWith('http://')
    || value.startsWith('https://')
    || value.startsWith('mailto:')
  )
}

function isExternalUrl(value: string): boolean {
  return /^https?:\/\//.test(value)
}

function getTextAlignStyle(value: string | null): CSSProperties | undefined {
  const textAlign = value?.match(/(?:^|;)\s*text-align\s*:\s*(left|right|center|justify)\s*(?:;|$)/i)?.[1]
  return textAlign ? { textAlign: textAlign.toLowerCase() as CSSProperties['textAlign'] } : undefined
}

function renderNode(node: Node, key: string): ReactNode {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent
  }

  if (!(node instanceof Element)) {
    return null
  }

  const tagName = node.tagName.toLowerCase()
  if (DROPPED_TAGS.has(tagName)) {
    return null
  }

  const children = Array.from(node.childNodes).map((child, index) =>
    renderNode(child, `${key}-${index}`)
  )

  if (!ALLOWED_TAGS.has(tagName)) {
    return <React.Fragment key={key}>{children}</React.Fragment>
  }

  const props: Record<string, unknown> = { key }
  const id = node.getAttribute('id')
  const className = node.getAttribute('class')
  const title = node.getAttribute('title')
  const style = getTextAlignStyle(node.getAttribute('style'))

  if (id) props.id = id
  if (className) props.className = className
  if (title) props.title = title
  if (style) props.style = style

  if (tagName === 'a') {
    const href = node.getAttribute('href')
    if (href && isSafeUrl(href)) {
      props.href = href
      if (isExternalUrl(href)) {
        props.target = '_blank'
        props.rel = 'noreferrer noopener'
      }
    }
  }

  if (tagName === 'img') {
    const src = node.getAttribute('src')
    if (src && isSafeUrl(src)) props.src = src
    props.alt = node.getAttribute('alt') ?? ''
    const width = node.getAttribute('width')
    const height = node.getAttribute('height')
    if (width) props.width = width
    if (height) props.height = height
  }

  if (tagName === 'td' || tagName === 'th') {
    const colSpan = Number(node.getAttribute('colspan'))
    const rowSpan = Number(node.getAttribute('rowspan'))
    if (Number.isInteger(colSpan) && colSpan > 0) props.colSpan = colSpan
    if (Number.isInteger(rowSpan) && rowSpan > 0) props.rowSpan = rowSpan
  }

  if (VOID_TAGS.has(tagName)) {
    return React.createElement(tagName, props)
  }

  return React.createElement(tagName, props, children)
}

interface SafeHtmlContentProps {
  html: string
  className?: string
  onClick?: React.MouseEventHandler<HTMLDivElement>
}

export const SafeHtmlContent = forwardRef<HTMLDivElement, SafeHtmlContentProps>(
  ({ html, className, onClick }, ref) => {
    const content = useMemo(() => {
      if (typeof DOMParser === 'undefined') {
        return html
      }

      const document = new DOMParser().parseFromString(html, 'text/html')
      return Array.from(document.body.childNodes).map((node, index) =>
        renderNode(node, String(index))
      )
    }, [html])

    return (
      <div ref={ref} onClick={onClick} className={className}>
        {content}
      </div>
    )
  }
)

SafeHtmlContent.displayName = 'SafeHtmlContent'
