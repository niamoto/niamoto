import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ScrollbarProvider } from '@/components/common'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

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
