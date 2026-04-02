import { create } from 'zustand'

interface ProjectCreationState {
  isOpen: boolean
  open: () => void
  close: () => void
}

export const useProjectCreationStore = create<ProjectCreationState>((set) => ({
  isOpen: false,
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
}))
