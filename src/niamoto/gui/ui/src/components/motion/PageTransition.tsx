/**
 * PageTransition — Subtle fade + slide for routed page content.
 * Wraps the router outlet, not the entire shell.
 * Respects prefers-reduced-motion.
 */

import { AnimatePresence, motion } from 'motion/react'
import { useLocation } from 'react-router-dom'
import { useReducedMotion } from '@/components/motion/useReducedMotion'

interface PageTransitionProps {
  children: React.ReactNode
}

export function PageTransition({ children }: PageTransitionProps) {
  const location = useLocation()
  const reducedMotion = useReducedMotion()

  if (reducedMotion) {
    return <>{children}</>
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{
          duration: 0.15,
          ease: [0.22, 1, 0.36, 1],
        }}
        className="h-full"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
