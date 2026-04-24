import { describe, expect, it } from 'vitest'

import {
  buildMarkdownCommandMenu,
  groupMarkdownCommandMenu,
} from './markdownCommandMenu'

const translations: Record<string, string> = {
  'markdownEditor.groups.text': 'Text',
  'markdownEditor.groups.structure': 'Structure',
  'markdownEditor.groups.lists': 'Lists',
  'markdownEditor.groups.media': 'Media',
  'markdownEditor.commands.text': 'Text',
  'markdownEditor.commands.textDesc': 'Start with plain body text',
  'markdownEditor.commands.heading1': 'Heading 1',
  'markdownEditor.commands.heading1Desc': 'Create a large section heading',
  'markdownEditor.commands.heading2': 'Heading 2',
  'markdownEditor.commands.heading2Desc': 'Add a subsection heading',
  'markdownEditor.commands.heading3': 'Heading 3',
  'markdownEditor.commands.heading3Desc': 'Add a compact subheading',
  'markdownEditor.commands.quote': 'Quote',
  'markdownEditor.commands.quoteDesc': 'Highlight a quotation',
  'markdownEditor.commands.code': 'Code',
  'markdownEditor.commands.codeDesc': 'Insert a code block',
  'markdownEditor.commands.list': 'List',
  'markdownEditor.commands.listDesc': 'Create a bullet list',
  'markdownEditor.commands.numberedList': 'Numbered list',
  'markdownEditor.commands.numberedListDesc': 'Create a numbered list',
  'markdownEditor.commands.tasks': 'Tasks',
  'markdownEditor.commands.tasksDesc': 'Create a checklist',
  'markdownEditor.commands.image': 'Image',
  'markdownEditor.commands.imageDesc': 'Insert an image into the page',
}

function t(key: string) {
  return translations[key] ?? key
}

describe('markdownCommandMenu', () => {
  it('builds the command catalog in a stable desktop-oriented order', () => {
    const commands = buildMarkdownCommandMenu(t)

    expect(commands.map((command) => command.key)).toEqual([
      'text',
      'heading1',
      'heading2',
      'heading3',
      'quote',
      'code',
      'list',
      'numberedList',
      'tasks',
      'image',
    ])
  })

  it('groups commands into the expected visible sections', () => {
    const groups = groupMarkdownCommandMenu(buildMarkdownCommandMenu(t), t)

    expect(groups.map((group) => group.label)).toEqual([
      'Text',
      'Structure',
      'Lists',
      'Media',
    ])

    expect(groups[1]?.items.map((item) => item.key)).toEqual([
      'heading1',
      'heading2',
      'heading3',
      'quote',
      'code',
    ])
  })

  it('keeps bilingual search aliases on common commands', () => {
    const commands = buildMarkdownCommandMenu(t)
    const heading = commands.find((command) => command.key === 'heading1')
    const tasks = commands.find((command) => command.key === 'tasks')

    expect(heading?.searchTerms).toEqual(
      expect.arrayContaining(['heading', 'titre', 'h1'])
    )
    expect(tasks?.searchTerms).toEqual(
      expect.arrayContaining(['todo', 'tache', 'checklist'])
    )
  })
})
