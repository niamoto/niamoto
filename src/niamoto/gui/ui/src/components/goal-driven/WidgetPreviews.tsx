import { type WidgetInstance } from '@/stores/goalDrivenStore'

export function WidgetPreview({ widget }: { widget: WidgetInstance }) {
  switch (widget.type) {
    case 'interactive_map':
      return <MapPreview />
    case 'info_cards':
      return <InfoCardsPreview />
    case 'horizontal_bar_chart':
      return <HorizontalBarChartPreview />
    case 'histogram':
      return <HistogramPreview />
    case 'vertical_bar_chart':
      return <VerticalBarChartPreview />
    case 'pie_chart':
      return <PieChartPreview />
    case 'donut_chart':
      return <DonutChartPreview />
    case 'stacked_bar_chart':
      return <StackedBarChartPreview />
    case 'circular_gauge':
      return <CircularGaugePreview />
    case 'linear_gauge':
      return <LinearGaugePreview />
    case 'stat_card':
      return <StatCardPreview />
    case 'table':
      return <TablePreview />
    case 'heatmap':
      return <HeatmapPreview />
    default:
      return <div className="text-muted-foreground text-sm">Preview indisponible</div>
  }
}

function MapPreview() {
  return (
    <div className="h-full bg-gradient-to-br from-blue-100 to-green-100 dark:from-blue-950 dark:to-green-950 rounded flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 opacity-20">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-red-500 rounded-full"
            style={{
              left: `${Math.random() * 90 + 5}%`,
              top: `${Math.random() * 90 + 5}%`
            }}
          />
        ))}
      </div>
      <span className="text-sm font-medium text-blue-600 dark:text-blue-400">Carte Interactive</span>
    </div>
  )
}

function InfoCardsPreview() {
  return (
    <div className="h-full flex gap-2 p-2">
      {['Occurrences', 'Famille', 'Provinces'].map((label, i) => (
        <div key={i} className="flex-1 bg-gradient-to-br from-primary/10 to-primary/5 rounded border border-primary/20 p-2 flex flex-col">
          <span className="text-xs text-muted-foreground">{label}</span>
          <span className="text-lg font-bold mt-auto">{Math.floor(Math.random() * 1000)}</span>
        </div>
      ))}
    </div>
  )
}

function HorizontalBarChartPreview() {
  const bars = [0.8, 0.65, 0.5, 0.4, 0.3]
  return (
    <div className="h-full p-4 flex flex-col justify-around">
      {bars.map((width, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-xs w-16 text-muted-foreground">Item {i + 1}</span>
          <div className="flex-1 h-4 bg-muted rounded overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-400 to-green-600"
              style={{ width: `${width * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function HistogramPreview() {
  const bars = [0.3, 0.5, 0.8, 0.9, 0.7, 0.5, 0.3, 0.2]
  return (
    <div className="h-full p-4 flex items-end justify-around gap-1">
      {bars.map((height, i) => (
        <div key={i} className="flex-1 flex flex-col items-center">
          <div
            className="w-full bg-gradient-to-t from-amber-400 to-amber-600 rounded-t"
            style={{ height: `${height * 100}%` }}
          />
          <span className="text-xs text-muted-foreground mt-1">{i * 10}</span>
        </div>
      ))}
    </div>
  )
}

function VerticalBarChartPreview() {
  const bars = [0.6, 0.8, 0.5, 0.7, 0.9, 0.4]
  return (
    <div className="h-full p-4 flex items-end justify-around gap-1">
      {bars.map((height, i) => (
        <div key={i} className="flex-1 flex flex-col items-center">
          <div
            className="w-full bg-gradient-to-t from-blue-400 to-blue-600 rounded-t"
            style={{ height: `${height * 100}%` }}
          />
        </div>
      ))}
    </div>
  )
}

function PieChartPreview() {
  return (
    <div className="h-full p-4 flex items-center justify-center">
      <svg viewBox="0 0 100 100" className="w-32 h-32">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#10b981" strokeWidth="20" strokeDasharray="75.4 188.4" />
        <circle cx="50" cy="50" r="40" fill="none" stroke="#3b82f6" strokeWidth="20" strokeDasharray="62.8 188.4" strokeDashoffset="-75.4" />
        <circle cx="50" cy="50" r="40" fill="none" stroke="#f59e0b" strokeWidth="20" strokeDasharray="50 188.4" strokeDashoffset="-138.2" />
      </svg>
    </div>
  )
}

function DonutChartPreview() {
  return (
    <div className="h-full p-4 flex items-center justify-center relative">
      <svg viewBox="0 0 100 100" className="w-32 h-32">
        <circle cx="50" cy="50" r="35" fill="none" stroke="#fb923c" strokeWidth="15" strokeDasharray="87.9 219.8" />
        <circle cx="50" cy="50" r="35" fill="none" stroke="#f97316" strokeWidth="15" strokeDasharray="87.9 219.8" strokeDashoffset="-87.9" />
        <circle cx="50" cy="50" r="35" fill="none" stroke="#ea580c" strokeWidth="15" strokeDasharray="44 219.8" strokeDashoffset="-175.8" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs text-muted-foreground">100%</span>
      </div>
    </div>
  )
}

function StackedBarChartPreview() {
  const stacks = [
    [0.3, 0.4, 0.3],
    [0.4, 0.3, 0.3],
    [0.2, 0.5, 0.3],
    [0.35, 0.35, 0.3]
  ]
  return (
    <div className="h-full p-4 flex items-end justify-around gap-2">
      {stacks.map((stack, i) => (
        <div key={i} className="flex-1 flex flex-col items-center h-full justify-end">
          {stack.map((seg, j) => (
            <div
              key={j}
              className={`w-full ${
                j === 0 ? 'bg-green-400' : j === 1 ? 'bg-green-500' : 'bg-green-600'
              }`}
              style={{ height: `${seg * 100}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

function CircularGaugePreview() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="10" className="text-muted opacity-20" />
          <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="10" strokeDasharray="251.2" strokeDashoffset="62.8" className="text-teal-500" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold">30m</span>
        </div>
      </div>
    </div>
  )
}

function LinearGaugePreview() {
  return (
    <div className="h-full flex items-center justify-center p-4">
      <div className="w-full space-y-2">
        <div className="h-8 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-emerald-400 to-emerald-600 rounded-full" style={{ width: '65%' }} />
        </div>
        <div className="text-center text-sm font-medium">65%</div>
      </div>
    </div>
  )
}

function StatCardPreview() {
  return (
    <div className="h-full bg-gradient-to-br from-primary/20 to-primary/10 dark:from-primary/10 dark:to-primary/5 rounded flex flex-col items-center justify-center p-4 border border-primary/30">
      <span className="text-3xl font-bold">5,486</span>
      <span className="text-sm text-muted-foreground mt-2">Total</span>
    </div>
  )
}

function TablePreview() {
  return (
    <div className="h-full p-2 overflow-hidden">
      <div className="space-y-1">
        <div className="flex gap-2 font-medium text-xs border-b pb-1">
          <div className="flex-1">Espèce</div>
          <div className="w-16">DBH</div>
          <div className="w-16">Hauteur</div>
        </div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-2 text-xs text-muted-foreground">
            <div className="flex-1 truncate">Espèce {i + 1}</div>
            <div className="w-16">{Math.floor(Math.random() * 50)}</div>
            <div className="w-16">{Math.floor(Math.random() * 30)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function HeatmapPreview() {
  return (
    <div className="h-full p-4 grid grid-cols-6 grid-rows-4 gap-1">
      {[...Array(24)].map((_, i) => {
        const intensity = Math.random()
        return (
          <div
            key={i}
            className="rounded"
            style={{
              backgroundColor: `rgba(59, 130, 246, ${intensity})`
            }}
          />
        )
      })}
    </div>
  )
}
