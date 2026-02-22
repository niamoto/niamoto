/**
 * Placeholder de chargement pour les previews widgets.
 */

interface PreviewSkeletonProps {
  width?: number
  height?: number
}

export function PreviewSkeleton({ width = 120, height = 90 }: PreviewSkeletonProps) {
  return (
    <div
      className="animate-pulse bg-gray-100 rounded flex items-center justify-center"
      style={{ width, height }}
    >
      <svg
        className="w-6 h-6 text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 5a1 1 0 011-1h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V5z"
        />
      </svg>
    </div>
  )
}
