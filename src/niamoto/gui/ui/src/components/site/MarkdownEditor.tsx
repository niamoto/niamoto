/**
 * MarkdownEditor - WYSIWYG markdown editor using Novel
 *
 * Features:
 * - Notion-style block editor
 * - Slash commands
 * - Image insertion via /image command
 * - Markdown import/export
 * - Real-time editing
 */

import { useState, useCallback, useRef, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  EditorRoot,
  EditorCommand,
  EditorCommandItem,
  EditorCommandEmpty,
  EditorContent,
  EditorCommandList,
  StarterKit,
  Placeholder,
  TaskList,
  TaskItem,
  TiptapLink,
  Command,
  createSuggestionItems,
  renderItems,
  handleCommandNavigation,
  type JSONContent,
} from 'novel'
import ImageResize from 'tiptap-extension-resize-image'
import {
  CheckSquare,
  Code,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Text,
  TextQuote,
  Image as ImageIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ImagePickerDialog, type SelectedImage } from './ImagePickerDialog'

interface MarkdownEditorProps {
  initialContent?: string
  onChange?: (markdown: string) => void
  placeholder?: string
  className?: string
  readOnly?: boolean
}

// Extract all images from a line (handles multiple images on same line)
// e.g., "![a](x.png) ![b](y.png)" → [{alt, src}, ...]
function extractImagesFromLine(line: string): Array<{ altPart: string; src: string }> | null {
  const regex = /!\[([^\]]*)\]\(([^)]+)\)/g
  const results: Array<{ altPart: string; src: string }> = []
  let match
  while ((match = regex.exec(line)) !== null) {
    results.push({ altPart: match[1], src: match[2] })
  }
  // Only return if the ENTIRE line is images (possibly with spaces between)
  if (results.length === 0) return null
  const stripped = line.replace(/!\[[^\]]*\]\([^)]+\)/g, '').trim()
  if (stripped.length > 0) return null // line has non-image text
  return results
}

// Parse a single image markdown syntax
// Format: ![alt](src) or ![alt|300](src) or ![alt|300|center](src) or ![alt|center](src)
function parseImageMarkdown(line: string): JSONContent | null {
  const imageMatch = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)
  if (!imageMatch) return null

  const [, altPart, src] = imageMatch
  // Parse alt text parts: "alt", "alt|300", "alt|center", "alt|300|center"
  const altParts = altPart.split('|')
  const alt = altParts[0]
  let width: number | undefined
  let align: string | undefined
  for (let i = 1; i < altParts.length; i++) {
    const part = altParts[i].trim()
    if (part === 'center' || part === 'right' || part === 'left') {
      align = part
    } else if (/^\d+$/.test(part)) {
      width = parseInt(part, 10)
    }
  }
  // Convert relative paths to API URL for display
  const imageSrc = src.startsWith('files/') ? `/api/site/${src}` : src
  // Build containerStyle with width + alignment (matches tiptap-extension-resize-image format)
  const containerParts: string[] = []
  containerParts.push(`width: ${width ? width + 'px' : '100%'}`)
  containerParts.push('height: auto')
  containerParts.push('cursor: pointer')
  if (align === 'center') containerParts.push('margin: 0 auto')
  else if (align === 'right') containerParts.push('margin: 0 0 0 auto')
  return {
    type: 'imageResize',
    attrs: {
      src: imageSrc,
      alt,
      title: alt,
      wrapperStyle: 'display: flex',
      containerStyle: containerParts.join('; ') + ';',
    },
  }
}

// Build an imageResize node from extracted alt/src parts
function buildImageNode(altPart: string, src: string): JSONContent {
  const altParts = altPart.split('|')
  const alt = altParts[0]
  let width: number | undefined
  let align: string | undefined
  for (let i = 1; i < altParts.length; i++) {
    const part = altParts[i].trim()
    if (part === 'center' || part === 'right' || part === 'left') {
      align = part
    } else if (/^\d+$/.test(part)) {
      width = parseInt(part, 10)
    }
  }
  const imageSrc = src.startsWith('files/') ? `/api/site/${src}` : src
  const containerParts: string[] = []
  containerParts.push(`width: ${width ? width + 'px' : '100%'}`)
  containerParts.push('height: auto')
  containerParts.push('cursor: pointer')
  if (align === 'center') containerParts.push('margin: 0 auto')
  else if (align === 'right') containerParts.push('margin: 0 0 0 auto')
  return {
    type: 'imageResize',
    attrs: {
      src: imageSrc,
      alt,
      title: alt,
      wrapperStyle: 'display: flex',
      containerStyle: containerParts.join('; ') + ';',
    },
  }
}

// Parse inline markdown formatting (bold, italic, code, links) into Tiptap text nodes with marks
function parseInlineContent(text: string): JSONContent[] {
  if (!text) return []

  const result: JSONContent[] = []
  let i = 0
  let plainStart = 0

  const pushPlain = (end: number) => {
    if (end > plainStart) {
      result.push({ type: 'text', text: text.slice(plainStart, end) })
    }
  }

  while (i < text.length) {
    // Bold: **text**
    if (text[i] === '*' && text[i + 1] === '*') {
      const endIdx = text.indexOf('**', i + 2)
      if (endIdx !== -1) {
        pushPlain(i)
        const inner = text.slice(i + 2, endIdx)
        result.push({ type: 'text', text: inner, marks: [{ type: 'bold' }] })
        i = endIdx + 2
        plainStart = i
        continue
      }
    }

    // Italic: *text* (not preceded by *)
    if (text[i] === '*' && text[i + 1] !== '*' && (i === 0 || text[i - 1] !== '*')) {
      const endIdx = text.indexOf('*', i + 1)
      if (endIdx !== -1 && text[endIdx + 1] !== '*') {
        pushPlain(i)
        const inner = text.slice(i + 1, endIdx)
        result.push({ type: 'text', text: inner, marks: [{ type: 'italic' }] })
        i = endIdx + 1
        plainStart = i
        continue
      }
    }

    // Inline code: `text`
    if (text[i] === '`') {
      const endIdx = text.indexOf('`', i + 1)
      if (endIdx !== -1) {
        pushPlain(i)
        const inner = text.slice(i + 1, endIdx)
        result.push({ type: 'text', text: inner, marks: [{ type: 'code' }] })
        i = endIdx + 1
        plainStart = i
        continue
      }
    }

    // Link: [text](url)
    if (text[i] === '[') {
      const closeBracket = text.indexOf(']', i + 1)
      if (closeBracket !== -1 && text[closeBracket + 1] === '(') {
        const closeParen = text.indexOf(')', closeBracket + 2)
        if (closeParen !== -1) {
          pushPlain(i)
          const linkText = text.slice(i + 1, closeBracket)
          const href = text.slice(closeBracket + 2, closeParen)
          result.push({
            type: 'text',
            text: linkText,
            marks: [{ type: 'link', attrs: { href, target: '_blank' } }],
          })
          i = closeParen + 1
          plainStart = i
          continue
        }
      }
    }

    i++
  }

  pushPlain(i)
  return result.length > 0 ? result : [{ type: 'text', text }]
}

// Convert markdown to Tiptap JSON content
function markdownToContent(markdown: string): JSONContent {
  // Split by double newlines first, then handle single newlines for images
  const blocks = markdown.split('\n\n').filter(Boolean)
  const content: JSONContent[] = []

  for (const block of blocks) {
    const trimmed = block.trim()

    // Headings
    if (trimmed.startsWith('### ')) {
      content.push({
        type: 'heading',
        attrs: { level: 3 },
        content: parseInlineContent(trimmed.slice(4)),
      })
      continue
    }
    if (trimmed.startsWith('## ')) {
      content.push({
        type: 'heading',
        attrs: { level: 2 },
        content: parseInlineContent(trimmed.slice(3)),
      })
      continue
    }
    if (trimmed.startsWith('# ')) {
      content.push({
        type: 'heading',
        attrs: { level: 1 },
        content: parseInlineContent(trimmed.slice(2)),
      })
      continue
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      content.push({
        type: 'blockquote',
        content: [
          {
            type: 'paragraph',
            content: parseInlineContent(trimmed.slice(2)),
          },
        ],
      })
      continue
    }

    // Code block
    if (trimmed.startsWith('```')) {
      const lines = trimmed.split('\n')
      const code = lines.slice(1, -1).join('\n')
      content.push({
        type: 'codeBlock',
        content: code ? [{ type: 'text', text: code }] : [],
      })
      continue
    }

    // Markdown table (lines starting with |)
    if (trimmed.startsWith('|') || trimmed.startsWith('| ')) {
      const tableLines = trimmed.split('\n')
      const isTable = tableLines.length >= 2 && tableLines.every((l) => l.trim().startsWith('|'))
      if (isTable) {
        content.push({
          type: 'codeBlock',
          attrs: { language: 'markdown' },
          content: [{ type: 'text', text: trimmed }],
        })
        continue
      }
    }

    // Bullet list item
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const items = trimmed.split('\n').filter((l) => l.startsWith('- ') || l.startsWith('* '))
      content.push({
        type: 'bulletList',
        content: items.map((item) => ({
          type: 'listItem',
          content: [
            {
              type: 'paragraph',
              content: parseInlineContent(item.slice(2)),
            },
          ],
        })),
      })
      continue
    }

    // Check if block contains images (single, multiple per line, or on separate lines)
    const lines = trimmed.split('\n')
    let allImages = true
    const imageNodes: JSONContent[] = []
    for (const line of lines) {
      const lineTrimmed = line.trim()
      // Single image on line
      const singleImage = parseImageMarkdown(lineTrimmed)
      if (singleImage) {
        imageNodes.push(singleImage)
        continue
      }
      // Multiple images on same line: ![a](x) ![b](y)
      const multiImages = extractImagesFromLine(lineTrimmed)
      if (multiImages) {
        for (const img of multiImages) {
          imageNodes.push(buildImageNode(img.altPart, img.src))
        }
        continue
      }
      // Not an image line
      allImages = false
      break
    }

    if (allImages && imageNodes.length > 0) {
      for (const node of imageNodes) {
        content.push(node)
      }
      continue
    }

    // Regular paragraph
    content.push({
      type: 'paragraph',
      content: trimmed ? parseInlineContent(trimmed) : [],
    })
  }

  return {
    type: 'doc',
    content,
  }
}

// Convert Tiptap JSON content to markdown
function contentToMarkdownWithWidths(content: JSONContent): string {
  if (!content.content) return ''

  const nodes = content.content
  const results: string[] = []

  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i]
    const prevNode = i > 0 ? nodes[i - 1] : null

    const getText = (n: JSONContent): string => {
      if (n.text) {
        let text = n.text
        if (n.marks) {
          for (const mark of [...n.marks].reverse()) {
            switch (mark.type) {
              case 'bold': text = `**${text}**`; break
              case 'italic': text = `*${text}*`; break
              case 'code': text = `\`${text}\``; break
              case 'link': text = `[${text}](${mark.attrs?.href || ''})`; break
            }
          }
        }
        return text
      }
      if (n.content) return n.content.map(getText).join('')
      return ''
    }

    const isImageNode = (n: JSONContent | null) =>
      n?.type === 'image' || n?.type === 'imageResize'

    let markdown: string

    switch (node.type) {
      case 'heading': {
        const level = node.attrs?.level || 1
        markdown = '#'.repeat(level) + ' ' + getText(node)
        break
      }

      case 'paragraph':
        markdown = getText(node)
        break

      case 'blockquote':
        markdown =
          '> ' +
          (node.content || [])
            .map((p: JSONContent) => getText(p))
            .join('\n> ')
        break

      case 'bulletList':
        markdown = (node.content || [])
          .map((item: JSONContent) => '- ' + getText(item))
          .join('\n')
        break

      case 'orderedList':
        markdown = (node.content || [])
          .map((item: JSONContent, idx: number) => `${idx + 1}. ` + getText(item))
          .join('\n')
        break

      case 'taskList':
        markdown = (node.content || [])
          .map((item: JSONContent) => {
            const checked = item.attrs?.checked ? 'x' : ' '
            return `- [${checked}] ` + getText(item)
          })
          .join('\n')
        break

      case 'codeBlock': {
        const codeText = getText(node)
        // Markdown tables stored as codeBlock: output raw (no backtick fences)
        if (codeText.trimStart().startsWith('|') && codeText.includes('|---')) {
          markdown = codeText
        } else {
          markdown = '```\n' + codeText + '\n```'
        }
        break
      }

      case 'horizontalRule':
        markdown = '---'
        break

      case 'image':
      case 'imageResize': {
        const imgSrc = node.attrs?.src || ''
        const imgAlt = node.attrs?.alt || ''
        const containerStyle = node.attrs?.containerStyle || ''
        // Read width from containerStyle (the extension stores it there)
        const widthMatch = containerStyle.match(/width:\s*([0-9.]+)px/)
        const imgWidth = widthMatch ? Math.round(parseFloat(widthMatch[1])) : undefined
        // Read alignment from containerStyle
        // Browser normalizes "margin: 0 auto" to various forms like "margin: 0px auto 0px auto"
        let imgAlign: string | undefined
        if (/margin:\s*0(?:px)?\s+auto/.test(containerStyle)) {
          imgAlign = 'center'
        } else if (/margin:\s*0(?:px)?\s+0(?:px)?\s+0(?:px)?\s+auto/.test(containerStyle)) {
          imgAlign = 'right'
        }
        // Convert API URL back to relative path for markdown
        const markdownSrc = imgSrc.replace('/api/site/', '')
        // Build alt with metadata: ![alt|width|center](src)
        let altWithMeta = imgAlt
        if (imgWidth) altWithMeta += `|${imgWidth}`
        if (imgAlign && imgAlign !== 'left') altWithMeta += `|${imgAlign}`
        markdown = `![${altWithMeta}](${markdownSrc})`
        break
      }

      default:
        markdown = getText(node)
    }

    // Add to results with appropriate separator
    if (results.length > 0) {
      // Use single newline between consecutive images (for gallery)
      // Use double newline for all other cases
      if (isImageNode(node) && isImageNode(prevNode)) {
        results.push('\n' + markdown)
      } else {
        results.push('\n\n' + markdown)
      }
    } else {
      results.push(markdown)
    }
  }

  return results.join('')
}

export function MarkdownEditor({
  initialContent = '',
  onChange,
  className,
  readOnly = false,
}: MarkdownEditorProps) {
  const { t } = useTranslation('site')

  const [content] = useState<JSONContent | undefined>(() =>
    initialContent ? markdownToContent(initialContent) : undefined
  )

  // Track if editor is empty (for showing help overlay)
  const [isEmpty, setIsEmpty] = useState(!initialContent || initialContent.trim() === '')

  // State for image picker dialog
  const [imageDialogOpen, setImageDialogOpen] = useState(false)

  // Store editor reference for inserting image after dialog closes
  const editorRef = useRef<any>(null)

  // Store onChange ref to always have latest version in callbacks
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Create suggestion items with image command
  const suggestionItems = useMemo(
    () =>
      createSuggestionItems([
        {
          title: t('markdownEditor.commands.text'),
          description: t('markdownEditor.commands.textDesc'),
          icon: <Text size={18} />,
          searchTerms: ['p', 'paragraph', 'texte', 'text'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).toggleNode('paragraph', 'paragraph').run()
          },
        },
        {
          title: t('markdownEditor.commands.heading1'),
          description: t('markdownEditor.commands.heading1Desc'),
          icon: <Heading1 size={18} />,
          searchTerms: ['title', 'h1', 'heading', 'titre'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).setNode('heading', { level: 1 }).run()
          },
        },
        {
          title: t('markdownEditor.commands.heading2'),
          description: t('markdownEditor.commands.heading2Desc'),
          icon: <Heading2 size={18} />,
          searchTerms: ['subtitle', 'h2', 'heading', 'titre'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run()
          },
        },
        {
          title: t('markdownEditor.commands.heading3'),
          description: t('markdownEditor.commands.heading3Desc'),
          icon: <Heading3 size={18} />,
          searchTerms: ['h3', 'heading', 'titre'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).setNode('heading', { level: 3 }).run()
          },
        },
        {
          title: t('markdownEditor.commands.image'),
          description: t('markdownEditor.commands.imageDesc'),
          icon: <ImageIcon size={18} />,
          searchTerms: ['image', 'photo', 'picture', 'img'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).run()
            editorRef.current = editor
            setImageDialogOpen(true)
          },
        },
        {
          title: t('markdownEditor.commands.list'),
          description: t('markdownEditor.commands.listDesc'),
          icon: <List size={18} />,
          searchTerms: ['unordered', 'ul', 'bullet', 'liste', 'list'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).toggleBulletList().run()
          },
        },
        {
          title: t('markdownEditor.commands.numberedList'),
          description: t('markdownEditor.commands.numberedListDesc'),
          icon: <ListOrdered size={18} />,
          searchTerms: ['ordered', 'ol', 'number', 'liste', 'list'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).toggleOrderedList().run()
          },
        },
        {
          title: t('markdownEditor.commands.tasks'),
          description: t('markdownEditor.commands.tasksDesc'),
          icon: <CheckSquare size={18} />,
          searchTerms: ['todo', 'task', 'checkbox', 'tache', 'tasks'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).toggleTaskList().run()
          },
        },
        {
          title: t('markdownEditor.commands.quote'),
          description: t('markdownEditor.commands.quoteDesc'),
          icon: <TextQuote size={18} />,
          searchTerms: ['blockquote', 'quote', 'citation'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).toggleBlockquote().run()
          },
        },
        {
          title: t('markdownEditor.commands.code'),
          description: t('markdownEditor.commands.codeDesc'),
          icon: <Code size={18} />,
          searchTerms: ['codeblock', 'code', 'pre'],
          command: ({ editor, range }: any) => {
            editor.chain().focus().deleteRange(range).toggleCodeBlock().run()
          },
        },
      ]),
    [t]
  )

  // Configure slash command extension
  const slashCommand = useMemo(
    () =>
      Command.configure({
        suggestion: {
          items: () => suggestionItems,
          render: renderItems,
        },
      }),
    [suggestionItems]
  )

  // Build extensions array
  const extensions = useMemo(
    () => [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
        bulletList: {
          HTMLAttributes: {
            class: 'list-disc list-outside leading-3 -mt-2',
          },
        },
        orderedList: {
          HTMLAttributes: {
            class: 'list-decimal list-outside leading-3 -mt-2',
          },
        },
        listItem: {
          HTMLAttributes: {
            class: 'leading-normal -mb-2',
          },
        },
        blockquote: {
          HTMLAttributes: {
            class: 'border-l-4 border-primary pl-4',
          },
        },
        codeBlock: {
          HTMLAttributes: {
            class: 'rounded-md bg-muted p-4 font-mono text-sm',
          },
        },
        code: {
          HTMLAttributes: {
            class: 'rounded-md bg-muted px-1 py-0.5 font-mono text-sm',
          },
        },
      }),
      TiptapLink.configure({
        HTMLAttributes: {
          class: 'text-primary underline underline-offset-[3px] hover:text-primary/80 cursor-pointer',
        },
        openOnClick: false,
      }),
      TaskList.configure({
        HTMLAttributes: {
          class: 'not-prose',
        },
      }),
      TaskItem.configure({
        HTMLAttributes: {
          class: 'flex items-start gap-2',
        },
        nested: true,
      }),
      Placeholder.configure({
        placeholder: ({ node }: any) => {
          if (node.type.name === 'heading') {
            return t('markdownEditor.placeholder.heading', { level: node.attrs.level })
          }
          return t('markdownEditor.placeholder.slashCommands')
        },
      }),
      ImageResize.configure({
        inline: false,
      }),
      slashCommand,
    ],
    [slashCommand, t]
  )

  // Build extensions - exclude slash command in read-only mode
  const editorExtensions = readOnly ? extensions.filter((ext) => ext.name !== 'command') : extensions

  // Helper to serialize editor content to markdown
  const serializeToMarkdown = useCallback((editor: any): string => {
    const json = editor.getJSON()
    return contentToMarkdownWithWidths(json)
  }, [])

  // Handle image selection from dialog (supports multiple images for gallery)
  const handleImageSelect = useCallback((images: SelectedImage[]) => {
    const editor = editorRef.current

    if (editor && images.length > 0) {
      const imageNodes = images.map((image) => {
        const imageSrc = image.path.startsWith('files/') ? `/api/site/${image.path}` : image.path
        return {
          type: 'imageResize',
          attrs: {
            src: imageSrc,
            alt: image.altText,
            title: image.altText,
            wrapperStyle: 'display: flex',
            containerStyle: 'width: 100%; height: auto; cursor: pointer;',
          },
        }
      })

      editor.chain().focus().insertContent(imageNodes).run()
    }
  }, [])

  return (
    <>
      {/* Styles for image selection, resize, and gallery */}
      <style>{`
        /* Image selection highlight */
        .ProseMirror img.ProseMirror-selectednode {
          outline: 3px solid hsl(var(--primary));
          outline-offset: 2px;
          border-radius: 4px;
        }

        /* Image wrapper - respect alignment styles from the resize extension */
        .ProseMirror > div[draggable="true"] {
          margin: 4px 0;
          max-width: 100%;
          position: relative;
        }

        /* Inner div that contains the resized width - make it responsive */
        .ProseMirror > div[draggable="true"] > div {
          max-width: 100% !important;
        }

        .ProseMirror > div[draggable="true"] img {
          max-width: 100%;
          height: auto;
          border-radius: 6px;
          object-fit: cover;
          display: block;
          transition: box-shadow 0.2s;
        }

        /* Hover effect */
        .ProseMirror > div[draggable="true"]:hover img {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        /* Selection indicator for images */
        .ProseMirror > div[draggable="true"].ProseMirror-selectednode {
          outline: 3px solid hsl(var(--primary));
          outline-offset: 2px;
          border-radius: 8px;
        }
      `}</style>
      <div
        className={cn(
          'relative w-full rounded-lg border bg-background',
          readOnly ? 'min-h-0' : 'min-h-[300px]',
          className
        )}
      >
        {/* Help overlay for empty editor */}
        {isEmpty && !readOnly && (
          <div
            className="absolute inset-0 z-10 flex items-start justify-center pt-16 pointer-events-none"
            aria-hidden="true"
          >
            <div className="max-w-md text-center px-6 py-4 rounded-lg bg-muted/50 border border-dashed border-muted-foreground/30">
              <p className="text-sm font-medium text-muted-foreground mb-2">
                {t('markdownEditor.help.startWriting')}
              </p>
              <p className="text-xs text-muted-foreground/80 mb-3">
                {t('markdownEditor.help.typeOrUseCommands')}
              </p>
              <div className="flex flex-wrap gap-2 justify-center text-xs">
                <kbd className="px-2 py-1 bg-background rounded border font-mono">/titre</kbd>
                <kbd className="px-2 py-1 bg-background rounded border font-mono">/image</kbd>
                <kbd className="px-2 py-1 bg-background rounded border font-mono">/liste</kbd>
                <kbd className="px-2 py-1 bg-background rounded border font-mono">/citation</kbd>
              </div>
            </div>
          </div>
        )}

        <EditorRoot>
          <EditorContent
            initialContent={content}
            extensions={editorExtensions}
            editable={!readOnly}
            onCreate={({ editor }) => {
              editorRef.current = editor
              // Single listener for ALL document changes (text edits + image resize/alignment)
              // The extension's dispatchNodeView() uses view.dispatch(tr.setNodeMarkup(...))
              // which sets transaction.docChanged = true
              if (!readOnly) {
                editor.on('transaction', ({ transaction }: { transaction: any }) => {
                  if (!transaction.docChanged) return
                  const currentOnChange = onChangeRef.current
                  if (currentOnChange) {
                    const md = serializeToMarkdown(editor)
                    currentOnChange(md)
                    setIsEmpty(!md || md.trim() === '')
                  }
                })
              }
            }}
            className={cn(
              'relative w-full border-none bg-transparent p-4',
              readOnly ? 'min-h-0' : 'min-h-[300px]'
            )}
            editorProps={{
              handleDOMEvents: {
                keydown: (_view, event) => (readOnly ? false : handleCommandNavigation(event)),
              },
              attributes: {
                class: cn(
                  'focus:outline-none max-w-full [&_h1]:text-3xl [&_h1]:font-bold [&_h1]:mb-4 [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h3]:text-xl [&_h3]:font-medium [&_h3]:mb-2 [&_p]:text-base [&_p]:mb-2',
                  readOnly ? '' : 'min-h-[250px]'
                ),
              },
            }}
          >
            {/* Slash commands menu - only show in edit mode */}
            {!readOnly && (
              <EditorCommand className="z-50 h-auto max-h-[330px] w-72 overflow-y-auto rounded-md border border-muted bg-background px-1 py-2 shadow-md transition-all">
                <EditorCommandEmpty className="px-2 text-muted-foreground">
                  {t('markdownEditor.help.noResult')}
                </EditorCommandEmpty>
                <EditorCommandList>
                  {suggestionItems.map((item) => (
                    <EditorCommandItem
                      value={item.title}
                      onCommand={(val) => item.command?.(val)}
                      className="flex w-full items-center space-x-2 rounded-md px-2 py-1 text-left text-sm hover:bg-accent aria-selected:bg-accent"
                      key={item.title}
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-md border border-muted bg-background">
                        {item.icon}
                      </div>
                      <div>
                        <p className="font-medium">{item.title}</p>
                        <p className="text-xs text-muted-foreground">{item.description}</p>
                      </div>
                    </EditorCommandItem>
                  ))}
                </EditorCommandList>
              </EditorCommand>
            )}
          </EditorContent>
        </EditorRoot>
      </div>

      {/* Image picker dialog */}
      <ImagePickerDialog
        open={imageDialogOpen}
        onOpenChange={setImageDialogOpen}
        onSelect={handleImageSelect}
      />
    </>
  )
}

export default MarkdownEditor
