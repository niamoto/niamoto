export type MarkdownCommandKey =
  | 'text'
  | 'heading1'
  | 'heading2'
  | 'heading3'
  | 'image'
  | 'list'
  | 'numberedList'
  | 'tasks'
  | 'quote'
  | 'code'

export type MarkdownCommandGroupKey = 'text' | 'structure' | 'lists' | 'media'

export interface MarkdownCommandMenuItem {
  key: MarkdownCommandKey
  group: MarkdownCommandGroupKey
  title: string
  description: string
  searchTerms: string[]
}

export interface MarkdownCommandMenuGroup<TItem extends MarkdownCommandMenuItem = MarkdownCommandMenuItem> {
  key: MarkdownCommandGroupKey
  label: string
  items: TItem[]
}

type Translate = (key: string) => string

const GROUP_ORDER: MarkdownCommandGroupKey[] = ['text', 'structure', 'lists', 'media']

const COMMAND_DEFINITIONS: Array<{
  key: MarkdownCommandKey
  group: MarkdownCommandGroupKey
  titleKey: string
  descriptionKey: string
  searchTerms: string[]
}> = [
  {
    key: 'text',
    group: 'text',
    titleKey: 'markdownEditor.commands.text',
    descriptionKey: 'markdownEditor.commands.textDesc',
    searchTerms: ['p', 'paragraph', 'texte', 'text', 'body', 'paragraphe'],
  },
  {
    key: 'heading1',
    group: 'structure',
    titleKey: 'markdownEditor.commands.heading1',
    descriptionKey: 'markdownEditor.commands.heading1Desc',
    searchTerms: ['title', 'heading', 'titre', 'section', 'h1', 'heading 1'],
  },
  {
    key: 'heading2',
    group: 'structure',
    titleKey: 'markdownEditor.commands.heading2',
    descriptionKey: 'markdownEditor.commands.heading2Desc',
    searchTerms: ['subtitle', 'heading', 'titre', 'subsection', 'h2', 'heading 2'],
  },
  {
    key: 'heading3',
    group: 'structure',
    titleKey: 'markdownEditor.commands.heading3',
    descriptionKey: 'markdownEditor.commands.heading3Desc',
    searchTerms: ['small title', 'heading', 'titre', 'subheading', 'h3', 'heading 3'],
  },
  {
    key: 'quote',
    group: 'structure',
    titleKey: 'markdownEditor.commands.quote',
    descriptionKey: 'markdownEditor.commands.quoteDesc',
    searchTerms: ['blockquote', 'quote', 'citation', 'citation block', 'pullquote'],
  },
  {
    key: 'code',
    group: 'structure',
    titleKey: 'markdownEditor.commands.code',
    descriptionKey: 'markdownEditor.commands.codeDesc',
    searchTerms: ['codeblock', 'code', 'pre', 'snippet', 'bloc code'],
  },
  {
    key: 'list',
    group: 'lists',
    titleKey: 'markdownEditor.commands.list',
    descriptionKey: 'markdownEditor.commands.listDesc',
    searchTerms: ['unordered', 'ul', 'bullet', 'liste', 'list', 'bullets'],
  },
  {
    key: 'numberedList',
    group: 'lists',
    titleKey: 'markdownEditor.commands.numberedList',
    descriptionKey: 'markdownEditor.commands.numberedListDesc',
    searchTerms: ['ordered', 'ol', 'number', 'liste', 'list', 'numbered'],
  },
  {
    key: 'tasks',
    group: 'lists',
    titleKey: 'markdownEditor.commands.tasks',
    descriptionKey: 'markdownEditor.commands.tasksDesc',
    searchTerms: ['todo', 'task', 'checkbox', 'tache', 'tasks', 'checklist'],
  },
  {
    key: 'image',
    group: 'media',
    titleKey: 'markdownEditor.commands.image',
    descriptionKey: 'markdownEditor.commands.imageDesc',
    searchTerms: ['image', 'photo', 'picture', 'img', 'media', 'illustration'],
  },
]

export function buildMarkdownCommandMenu(t: Translate): MarkdownCommandMenuItem[] {
  return COMMAND_DEFINITIONS.map((definition) => ({
    key: definition.key,
    group: definition.group,
    title: t(definition.titleKey),
    description: t(definition.descriptionKey),
    searchTerms: definition.searchTerms,
  }))
}

export function groupMarkdownCommandMenu<TItem extends MarkdownCommandMenuItem>(
  items: TItem[],
  t: Translate
): MarkdownCommandMenuGroup<TItem>[] {
  return GROUP_ORDER.map((group) => ({
    key: group,
    label: t(`markdownEditor.groups.${group}`),
    items: items.filter((item) => item.group === group),
  })).filter((group) => group.items.length > 0)
}
