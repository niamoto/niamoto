import { useState, useEffect, useCallback } from 'react'
import { useConfig } from './useConfig'
import { parseTransformConfig, serializeTransformConfig, validateTransformConfig } from '@/utils/transformConfigParser'
import type { UIGroup } from '@/types/transform'

export function useTransformConfig() {
  const { config, loading, error, saving, updateConfig } = useConfig('transform')
  const [groups, setGroups] = useState<UIGroup[]>([])
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  // Parse configuration when loaded
  useEffect(() => {
    if (config) {
      // Ensure config is an array
      const configArray = Array.isArray(config) ? config : []
      const validation = validateTransformConfig(configArray)
      if (validation.valid) {
        const parsedGroups = parseTransformConfig(configArray)
        setGroups(parsedGroups)
        setValidationErrors([])
      } else {
        setValidationErrors(validation.errors)
        // Still try to parse even with errors for partial data
        const parsedGroups = parseTransformConfig(configArray)
        setGroups(parsedGroups)
      }
    }
  }, [config])

  // Add a new group
  const addGroup = useCallback((name: string, displayName: string, description?: string) => {
    const newGroup: UIGroup = {
      id: `group-${name}-${Date.now()}`,
      name,
      displayName,
      description,
      sources: [],
      widgets: [],
      icon: name === 'taxon' ? 'taxon' : name === 'plot' ? 'plot' : name === 'shape' ? 'shape' : 'custom'
    }
    setGroups(prev => [...prev, newGroup])
  }, [])

  // Update an existing group
  const updateGroup = useCallback((groupId: string, updates: Partial<UIGroup>) => {
    setGroups(prev => prev.map(group =>
      group.id === groupId ? { ...group, ...updates } : group
    ))
  }, [])

  // Delete a group
  const deleteGroup = useCallback((groupId: string) => {
    setGroups(prev => prev.filter(group => group.id !== groupId))
  }, [])

  // Save configuration back to YAML
  const saveConfig = useCallback(async () => {
    const serialized = serializeTransformConfig(groups)
    const validation = validateTransformConfig(serialized)

    if (!validation.valid) {
      setValidationErrors(validation.errors)
      throw new Error(`Configuration validation failed: ${validation.errors.join(', ')}`)
    }

    try {
      const result = await updateConfig({
        content: serialized,
        backup: true
      })
      setValidationErrors([])
      return result
    } catch (err) {
      throw err
    }
  }, [groups, updateConfig])

  // Get a specific group by ID
  const getGroup = useCallback((groupId: string) => {
    return groups.find(g => g.id === groupId)
  }, [groups])

  // Get a group by name (group_by value)
  const getGroupByName = useCallback((name: string) => {
    return groups.find(g => g.name === name)
  }, [groups])

  return {
    groups,
    loading,
    error,
    saving,
    validationErrors,
    addGroup,
    updateGroup,
    deleteGroup,
    saveConfig,
    getGroup,
    getGroupByName,
    setGroups  // For bulk updates from UI
  }
}
