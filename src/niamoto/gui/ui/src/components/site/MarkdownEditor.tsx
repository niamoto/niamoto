/**
 * MarkdownEditor - WYSIWYG markdown editor using Novel
 *
 * Features:
 * - Notion-style block editor
 * - Slash commands
 * - Markdown import/export
 * - Real-time editing
 */

import { useState, useCallback } from 'react'
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
} from 'lucide-react'
import { cn } from '@/lib/utils'

// Slash command suggestions
const suggestionItems = createSuggestionItems([
  {
    title: 'Texte',
    description: 'Texte simple',
    icon: <Text size={18} />,
    searchTerms: ['p', 'paragraph', 'texte'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).toggleNode('paragraph', 'paragraph').run()
    },
  },
  {
    title: 'Titre 1',
    description: 'Grand titre de section',
    icon: <Heading1 size={18} />,
    searchTerms: ['title', 'h1', 'heading', 'titre'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).setNode('heading', { level: 1 }).run()
    },
  },
  {
    title: 'Titre 2',
    description: 'Titre de sous-section',
    icon: <Heading2 size={18} />,
    searchTerms: ['subtitle', 'h2', 'heading', 'titre'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run()
    },
  },
  {
    title: 'Titre 3',
    description: 'Petit titre',
    icon: <Heading3 size={18} />,
    searchTerms: ['h3', 'heading', 'titre'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).setNode('heading', { level: 3 }).run()
    },
  },
  {
    title: 'Liste',
    description: 'Liste a puces',
    icon: <List size={18} />,
    searchTerms: ['unordered', 'ul', 'bullet', 'liste'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).toggleBulletList().run()
    },
  },
  {
    title: 'Liste numerotee',
    description: 'Liste ordonnee',
    icon: <ListOrdered size={18} />,
    searchTerms: ['ordered', 'ol', 'number', 'liste'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).toggleOrderedList().run()
    },
  },
  {
    title: 'Taches',
    description: 'Liste de taches',
    icon: <CheckSquare size={18} />,
    searchTerms: ['todo', 'task', 'checkbox', 'tache'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).toggleTaskList().run()
    },
  },
  {
    title: 'Citation',
    description: 'Bloc de citation',
    icon: <TextQuote size={18} />,
    searchTerms: ['blockquote', 'quote', 'citation'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).toggleBlockquote().run()
    },
  },
  {
    title: 'Code',
    description: 'Bloc de code',
    icon: <Code size={18} />,
    searchTerms: ['codeblock', 'code', 'pre'],
    command: ({ editor, range }: any) => {
      editor.chain().focus().deleteRange(range).toggleCodeBlock().run()
    },
  },
])

// Configure slash command extension
const slashCommand = Command.configure({
  suggestion: {
    items: () => suggestionItems,
    render: renderItems,
  },
})

// Build extensions array
const extensions = [
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
        return `Titre ${node.attrs.level}`
      }
      return 'Tapez / pour afficher les commandes...'
    },
  }),
  slashCommand,
]

interface MarkdownEditorProps {
  initialContent?: string
  onChange?: (markdown: string) => void
  placeholder?: string
  className?: string
}

// Convert markdown to Tiptap JSON content
function markdownToContent(markdown: string): JSONContent {
  const blocks = markdown.split('\n\n').filter(Boolean)

  return {
    type: 'doc',
    content: blocks.map((block) => {
      const trimmed = block.trim()

      // Headings
      if (trimmed.startsWith('### ')) {
        return {
          type: 'heading',
          attrs: { level: 3 },
          content: [{ type: 'text', text: trimmed.slice(4) }],
        }
      }
      if (trimmed.startsWith('## ')) {
        return {
          type: 'heading',
          attrs: { level: 2 },
          content: [{ type: 'text', text: trimmed.slice(3) }],
        }
      }
      if (trimmed.startsWith('# ')) {
        return {
          type: 'heading',
          attrs: { level: 1 },
          content: [{ type: 'text', text: trimmed.slice(2) }],
        }
      }

      // Blockquote
      if (trimmed.startsWith('> ')) {
        return {
          type: 'blockquote',
          content: [
            {
              type: 'paragraph',
              content: [{ type: 'text', text: trimmed.slice(2) }],
            },
          ],
        }
      }

      // Code block
      if (trimmed.startsWith('```')) {
        const lines = trimmed.split('\n')
        const code = lines.slice(1, -1).join('\n')
        return {
          type: 'codeBlock',
          content: code ? [{ type: 'text', text: code }] : [],
        }
      }

      // Bullet list item
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const items = trimmed.split('\n').filter((l) => l.startsWith('- ') || l.startsWith('* '))
        return {
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
        }
      }

      // Regular paragraph
      return {
        type: 'paragraph',
        content: trimmed ? [{ type: 'text', text: trimmed }] : [],
      }
    }),
  }
}

// Convert Tiptap JSON content to markdown
function contentToMarkdown(content: JSONContent): string {
  if (!content.content) return ''

  return content.content
    .map((node) => {
      const getText = (n: JSONContent): string => {
        if (n.text) return n.text
        if (n.content) return n.content.map(getText).join('')
        return ''
      }

      switch (node.type) {
        case 'heading':
          const level = node.attrs?.level || 1
          return '#'.repeat(level) + ' ' + getText(node)

        case 'paragraph':
          return getText(node)

        case 'blockquote':
          return (
            '> ' +
            (node.content || [])
              .map((p: JSONContent) => getText(p))
              .join('\n> ')
          )

        case 'bulletList':
          return (node.content || [])
            .map((item: JSONContent) => '- ' + getText(item))
            .join('\n')

        case 'orderedList':
          return (node.content || [])
            .map((item: JSONContent, i: number) => `${i + 1}. ` + getText(item))
            .join('\n')

        case 'taskList':
          return (node.content || [])
            .map((item: JSONContent) => {
              const checked = item.attrs?.checked ? 'x' : ' '
              return `- [${checked}] ` + getText(item)
            })
            .join('\n')

        case 'codeBlock':
          return '```\n' + getText(node) + '\n```'

        case 'horizontalRule':
          return '---'

        default:
          return getText(node)
      }
    })
    .filter((text) => text !== undefined)
    .join('\n\n')
}

export function MarkdownEditor({
  initialContent = '',
  onChange,
  className,
}: MarkdownEditorProps) {
  const [content] = useState<JSONContent | undefined>(() =>
    initialContent ? markdownToContent(initialContent) : undefined
  )

  // Handle content updates
  const handleUpdate = useCallback(
    ({ editor }: { editor: any }) => {
      if (onChange) {
        const json = editor.getJSON()
        const md = contentToMarkdown(json)
        onChange(md)
      }
    },
    [onChange]
  )

  return (
    <div
      className={cn(
        'relative min-h-[300px] w-full rounded-lg border bg-background',
        className
      )}
    >
      <EditorRoot>
        <EditorContent
          initialContent={content}
          extensions={extensions}
          className="relative min-h-[300px] w-full border-none bg-transparent p-4"
          editorProps={{
            handleDOMEvents: {
              keydown: (_view, event) => handleCommandNavigation(event),
            },
            attributes: {
              class:
                'prose dark:prose-invert focus:outline-none max-w-full min-h-[250px] [&_h1]:text-3xl [&_h1]:font-bold [&_h1]:mb-4 [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h3]:text-xl [&_h3]:font-medium [&_h3]:mb-2 [&_p]:text-base [&_p]:mb-2',
            },
          }}
          onUpdate={handleUpdate}
        >
          {/* Slash commands menu */}
          <EditorCommand className="z-50 h-auto max-h-[330px] w-72 overflow-y-auto rounded-md border border-muted bg-background px-1 py-2 shadow-md transition-all">
            <EditorCommandEmpty className="px-2 text-muted-foreground">
              Aucun resultat
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
        </EditorContent>
      </EditorRoot>
    </div>
  )
}

export default MarkdownEditor
