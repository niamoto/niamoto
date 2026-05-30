/**
 * PageTransition — Lightweight route polish without exit overlays.
 * Wraps the router outlet, not the entire shell.
 * Respects prefers-reduced-motion.
 */

import { motion } from 'motion/react'
import { useLocation } from 'react-router-dom'
import { useReducedMotion } from '@/components/motion/useReducedMotion'

interface PageTransitionProps {
  children: React.ReactNode
  transitionKey?: string
}

export function PageTransition({
  children,
  transitionKey,
}: PageTransitionProps) {
  const location = useLocation()
  const reducedMotion = useReducedMotion()

  if (reducedMotion) {
    return <>{children}</>
  }

  return (
    <motion.div
      key={transitionKey ?? location.pathname}
      initial={{ opacity: 0.98, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.18,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="h-full"
    >
      {children}
    </motion.div>
  )
}
