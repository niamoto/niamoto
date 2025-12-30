/**
 * Import Wizard - Import data files
 * Route: /sources/import
 */

import { ImportWizard } from '@/components/panels/ImportWizard'

export default function ImportPage() {
  return (
    <div className="h-full overflow-auto">
      <ImportWizard />
    </div>
  )
}
