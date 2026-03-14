/**
 * Types for Layout Editor
 */

export interface WidgetLayout {
  index: number
  plugin: string
  title: string
  description?: string
  data_source: string
  colspan: 1 | 2
  order: number
  is_navigation: boolean
}

export interface NavigationWidgetInfo {
  plugin: string
  title: string
  params: Record<string, unknown>
  is_hierarchical: boolean
}

export interface LayoutResponse {
  group_by: string
  widgets: WidgetLayout[]
  navigation_widget: NavigationWidgetInfo | null
  total_widgets: number
}

export interface WidgetLayoutUpdate {
  index: number
  title?: string
  description?: string
  colspan?: 1 | 2
  order: number
}

export interface LayoutUpdateRequest {
  widgets: WidgetLayoutUpdate[]
}

export interface LayoutUpdateResponse {
  success: boolean
  message: string
  widgets_updated: number
}

export interface GroupInfo {
  name: string
  widget_count: number
}

export interface GroupsListResponse {
  groups: GroupInfo[]
  total: number
}
