/**
 * CardEntrance — Staggered entrance animation for card groups.
 * Wrap a group of cards; each direct child animates in sequence.
 * Respects prefers-reduced-motion.
 */

import { motion } from 'motion/react'
import { useReducedMotion } from '@/components/motion/useReducedMotion'

interface CardEntranceProps {
  children: React.ReactNode
  className?: string
  /** Delay in seconds between each child (default 0.04) */
  stagger?: number
}

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.04,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, scale: 0.97 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.2,
      ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
    },
  },
}

export function CardEntrance({ children, className, stagger = 0.04 }: CardEntranceProps) {
  const reducedMotion = useReducedMotion()

  if (reducedMotion) {
    return <div className={className}>{children}</div>
  }

  const variants = stagger !== 0.04
    ? { ...containerVariants, visible: { transition: { staggerChildren: stagger } } }
    : containerVariants

  return (
    <motion.div
      className={className}
      variants={variants}
      initial="hidden"
      animate="visible"
    >
      {children}
    </motion.div>
  )
}

/** Wrap each card item with this for staggered animation */
export function CardEntranceItem({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={itemVariants}>
      {children}
    </motion.div>
  )
}
