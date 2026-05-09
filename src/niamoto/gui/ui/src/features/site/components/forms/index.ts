/**
 * Template-specific form components
 *
 * These forms provide dedicated editing interfaces for specific templates
 * that require structured data rather than markdown content.
 */

export { MarkdownContentField } from './MarkdownContentField'
export { IndexPageForm, type IndexPageContext } from './IndexPageForm'
export { BibliographyForm, type BibliographyPageContext } from './BibliographyForm'
export { TeamForm, type TeamPageContext } from './TeamForm'
export { ResourcesForm, type ResourcesPageContext } from './ResourcesForm'
export { ContactForm, type ContactPageContext } from './ContactForm'
export { GlossaryForm, type GlossaryPageContext } from './GlossaryForm'

/**
 * Map of templates that have dedicated forms
 */
const TEMPLATE_FORMS = {
  'index.html': 'IndexPageForm',
  'bibliography.html': 'BibliographyForm',
  'team.html': 'TeamForm',
  'resources.html': 'ResourcesForm',
  'contact.html': 'ContactForm',
  'glossary.html': 'GlossaryForm',
} as const

/**
 * Check if a template has a dedicated form
 */
export function hasTemplateForm(template: string): boolean {
  return template in TEMPLATE_FORMS
}
