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

import { useState, useCallback, useRef, useMemo, useEffect } from 'react'
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

// Parse a single image markdown syntax
function parseImageMarkdown(line: string): JSONContent | null {
  const imageMatch = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)
  if (!imageMatch) return null

  const [, altPart, src] = imageMatch
  // Check for width in alt text: "alt|300" or just "alt"
  const altParts = altPart.split('|')
  const alt = altParts[0]
  const width = altParts[1] ? parseInt(altParts[1], 10) : undefined
  // Convert relative paths to API URL for display
  const imageSrc = src.startsWith('files/') ? `/api/site/${src}` : src
  // Use imageResize type to match tiptap-extension-resize-image
  return {
    type: 'imageResize',
    attrs: {
      src: imageSrc,
      alt,
      title: alt,
      wrapperStyle: width ? `width: ${width}px` : 'display: flex',
      containerStyle: null,
    },
  }
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
        content: [{ type: 'text', text: trimmed.slice(4) }],
      })
      continue
    }
    if (trimmed.startsWith('## ')) {
      content.push({
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: trimmed.slice(3) }],
      })
      continue
    }
    if (trimmed.startsWith('# ')) {
      content.push({
        type: 'heading',
        attrs: { level: 1 },
        content: [{ type: 'text', text: trimmed.slice(2) }],
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
            content: [{ type: 'text', text: trimmed.slice(2) }],
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
              content: [{ type: 'text', text: item.slice(2) }],
            },
          ],
        })),
      })
      continue
    }

    // Check if block contains images (single or multiple on separate lines)
    const lines = trimmed.split('\n')
    const imageLines = lines.filter((l) => l.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/))

    if (imageLines.length > 0 && imageLines.length === lines.length) {
      // All lines are images - parse each one
      for (const line of lines) {
        const imageNode = parseImageMarkdown(line.trim())
        if (imageNode) {
          content.push(imageNode)
        }
      }
      continue
    }

    // Single image on its own
    const imageNode = parseImageMarkdown(trimmed)
    if (imageNode) {
      content.push(imageNode)
      continue
    }

    // Regular paragraph
    content.push({
      type: 'paragraph',
      content: trimmed ? [{ type: 'text', text: trimmed }] : [],
    })
  }

  return {
    type: 'doc',
    content,
  }
}

// Convert Tiptap JSON content to markdown (with optional DOM-based widths)
function contentToMarkdownWithWidths(content: JSONContent, imageWidths?: Map<string, number>): string {
  if (!content.content) return ''

  const nodes = content.content
  const results: string[] = []

  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i]
    const prevNode = i > 0 ? nodes[i - 1] : null

    const getText = (n: JSONContent): string => {
      if (n.text) return n.text
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

      case 'codeBlock':
        markdown = '```\n' + getText(node) + '\n```'
        break

      case 'horizontalRule':
        markdown = '---'
        break

      case 'image':
      case 'imageResize': {
        const imgSrc = node.attrs?.src || ''
        const imgAlt = node.attrs?.alt || ''
        // First try to get width from DOM-based map (for resize detection)
        // Then fallback to wrapperStyle attribute
        let imgWidth: number | undefined = imageWidths?.get(imgSrc)
        if (!imgWidth) {
          const wrapperStyle = node.attrs?.wrapperStyle || ''
          const widthMatch = wrapperStyle.match(/width:\s*(\d+)px/)
          imgWidth = widthMatch ? parseInt(widthMatch[1], 10) : undefined
        }
        // Convert API URL back to relative path for markdown
        const markdownSrc = imgSrc.replace('/api/site/', '')
        // Include width in alt if set: ![alt|width](src)
        const altWithWidth = imgWidth ? `${imgAlt}|${imgWidth}` : imgAlt
        markdown = `![${altWithWidth}](${markdownSrc})`
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

// Wrapper for backward compatibility
function contentToMarkdown(content: JSONContent): string {
  return contentToMarkdownWithWidths(content)
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

  // Ref to the editor container for MutationObserver and DOM reading
  const editorContainerRef = useRef<HTMLDivElement>(null)

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
            // Delete the slash command text first (this closes the menu)
            editor.chain().focus().deleteRange(range).run()
            // Store editor reference for later use (range is now handled)
            editorRef.current = editor
            // Open the image picker dialog
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
        HTMLAttributes: {
          class: 'editor-image rounded-md max-w-full h-auto my-4',
        },
        allowBase64: true,
        inline: false,
      }),
      slashCommand,
    ],
    [slashCommand, t]
  )

  // Build extensions - exclude slash command in read-only mode
  const editorExtensions = readOnly ? extensions.filter((ext) => ext.name !== 'command') : extensions

  // Helper to read image widths from DOM
  const getImageWidthsFromDOM = useCallback((): Map<string, number> => {
    const imageWidths = new Map<string, number>()
    if (!editorContainerRef.current) return imageWidths

    const imageWrappers = editorContainerRef.current.querySelectorAll('div[draggable="true"]')
    imageWrappers.forEach((wrapper) => {
      const innerDiv = wrapper.querySelector('div')
      const img = wrapper.querySelector('img')
      if (innerDiv && img) {
        const style = innerDiv.getAttribute('style') || ''
        const widthMatch = style.match(/width:\s*(\d+)px/)
        if (widthMatch) {
          const src = img.getAttribute('src') || ''
          imageWidths.set(src, parseInt(widthMatch[1], 10))
        }
      }
    })
    return imageWidths
  }, [])

  // Handle content updates
  const handleUpdate = useCallback(
    ({ editor }: { editor: any }) => {
      // Use ref to always have latest onChange callback
      const currentOnChange = onChangeRef.current
      if (currentOnChange) {
        const json = editor.getJSON()
        // Always read widths from DOM to preserve resize state
        const imageWidths = getImageWidthsFromDOM()
        const md = contentToMarkdownWithWidths(json, imageWidths)
        currentOnChange(md)

        // Track empty state for help overlay
        setIsEmpty(!md || md.trim() === '')
      }
    },
    [getImageWidthsFromDOM]
  )

  // MutationObserver to detect image resize changes
  // tiptap-extension-resize-image modifies DOM style directly without triggering onUpdate
  useEffect(() => {
    if (readOnly || !editorContainerRef.current) return

    // Capture element reference at effect creation to ensure proper cleanup
    const element = editorContainerRef.current

    const observer = new MutationObserver((mutations) => {
      // Check if any mutation is a style change on an image wrapper
      const hasImageStyleChange = mutations.some((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
          const target = mutation.target as HTMLElement
          // Check if it's an image wrapper (div inside the draggable container)
          return target.parentElement?.hasAttribute('draggable') ||
                 target.hasAttribute('draggable')
        }
        return false
      })

      if (hasImageStyleChange) {
        // Trigger onChange after a small delay to let the resize complete
        setTimeout(() => {
          const currentOnChange = onChangeRef.current
          if (currentOnChange && editorRef.current) {
            // Read widths from DOM since the extension doesn't update node attributes
            const imageWidths = getImageWidthsFromDOM()
            const json = editorRef.current.getJSON()
            const md = contentToMarkdownWithWidths(json, imageWidths)
            currentOnChange(md)
          }
        }, 100)
      }
    })

    // Observe the editor container for style changes
    observer.observe(element, {
      attributes: true,
      attributeFilter: ['style'],
      subtree: true,
    })

    return () => observer.disconnect()
  }, [readOnly, getImageWidthsFromDOM])

  // Handle image selection from dialog (supports multiple images for gallery)
  const handleImageSelect = useCallback((images: SelectedImage[]) => {
    const editor = editorRef.current

    if (editor && images.length > 0) {
      // Insert all images consecutively (creates gallery effect)
      // Build content array with consecutive image nodes
      const imageNodes = images.map((image) => {
        const imageSrc = image.path.startsWith('files/') ? `/api/site/${image.path}` : image.path
        return {
          type: 'imageResize',
          attrs: {
            src: imageSrc,
            alt: image.altText,
            title: image.altText,
            wrapperStyle: 'display: flex',
            containerStyle: null,
          },
        }
      })

      // Insert all images at once
      editor.chain().focus().insertContent(imageNodes).run()

      // Manually trigger onChange since setImage may not trigger onUpdate
      // Use ref to always have latest onChange callback
      requestAnimationFrame(() => {
        setTimeout(() => {
          const currentOnChange = onChangeRef.current
          if (currentOnChange) {
            const json = editor.getJSON()
            const md = contentToMarkdown(json)
            currentOnChange(md)
          }
        }, 50)
      })

      // Note: Don't clear editorRef - it's needed for resize detection via MutationObserver
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

        /* ========================================
           Gallery: consecutive images side-by-side
           Target the actual DOM structure from tiptap-extension-resize-image:
           <div style="display: flex" contenteditable="false" draggable="true">
             <div style="width: Xpx"><img></div>
           </div>
           ======================================== */

        /* Image wrapper - inline display for gallery, respect user-defined width */
        .ProseMirror > div[draggable="true"] {
          display: inline-block !important;
          vertical-align: top;
          margin: 4px;
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
        ref={editorContainerRef}
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
              // Store editor reference for image insertion and resize detection
              editorRef.current = editor
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
            onUpdate={readOnly ? undefined : handleUpdate}
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
