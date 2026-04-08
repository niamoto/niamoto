import { AnimatePresence, motion } from 'motion/react'
import { useReducedMotion } from '@/components/motion/useReducedMotion'

interface PanelTransitionProps {
  transitionKey: string
  children: React.ReactNode
  className?: string
  direction?: 'horizontal' | 'vertical'
}

export function PanelTransition({
  transitionKey,
  children,
  className = 'h-full',
  direction = 'horizontal',
}: PanelTransitionProps) {
  const reducedMotion = useReducedMotion()

  if (reducedMotion) {
    return <div className={className}>{children}</div>
  }

  const initial = direction === 'vertical'
    ? { opacity: 0, y: 6 }
    : { opacity: 0, x: 10 }
  const exit = direction === 'vertical'
    ? { opacity: 0, y: -4 }
    : { opacity: 0, x: -8 }

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={transitionKey}
        initial={initial}
        animate={{ opacity: 1, x: 0, y: 0 }}
        exit={exit}
        transition={{
          duration: 0.17,
          ease: [0.22, 1, 0.36, 1],
        }}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
