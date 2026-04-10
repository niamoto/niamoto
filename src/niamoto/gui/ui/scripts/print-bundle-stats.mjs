import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { gzipSync } from 'node:zlib'

const projectRoot = process.cwd()
const assetsDir = path.join(projectRoot, 'dist', 'assets')

function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  const units = ['kB', 'MB', 'GB']
  let value = bytes
  let unitIndex = -1

  do {
    value /= 1024
    unitIndex += 1
  } while (value >= 1024 && unitIndex < units.length - 1)

  return `${value.toFixed(2)} ${units[unitIndex]}`
}

function collectStats(extension) {
  return readdirSync(assetsDir)
    .filter((name) => name.endsWith(extension))
    .map((name) => {
      const filePath = path.join(assetsDir, name)
      const content = readFileSync(filePath)

      return {
        name,
        size: statSync(filePath).size,
        gzipSize: gzipSync(content).length,
      }
    })
    .sort((left, right) => right.size - left.size)
}

function printSection(title, rows) {
  console.log(`\n${title}`)
  console.log('-'.repeat(title.length))

  rows.forEach((row) => {
    console.log(
      `${row.name.padEnd(42)} ${formatBytes(row.size).padStart(10)}  gzip ${formatBytes(row.gzipSize).padStart(10)}`
    )
  })
}

const jsFiles = collectStats('.js')
const cssFiles = collectStats('.css')

printSection('Top JavaScript bundles', jsFiles.slice(0, 10))

if (cssFiles.length > 0) {
  printSection('Top CSS bundles', cssFiles.slice(0, 5))
}

const totalJs = jsFiles.reduce((sum, file) => sum + file.size, 0)
const totalCss = cssFiles.reduce((sum, file) => sum + file.size, 0)

console.log('\nBundle summary')
console.log('--------------')
console.log(`JavaScript: ${formatBytes(totalJs)}`)
console.log(`CSS:        ${formatBytes(totalCss)}`)
