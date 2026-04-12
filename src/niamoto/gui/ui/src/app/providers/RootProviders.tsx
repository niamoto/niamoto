import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { ScrollbarProvider } from '@/components/common'
import { queryClient } from './queryClient'

interface RootProvidersProps {
  children: ReactNode
}

export function RootProviders({ children }: RootProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ScrollbarProvider>{children}</ScrollbarProvider>
    </QueryClientProvider>
  )
}
