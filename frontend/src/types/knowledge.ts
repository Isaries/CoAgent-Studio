export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  space_id?: string
  room_id?: string
  source_type: 'conversation' | 'document' | 'merged'
  build_status: 'idle' | 'building' | 'ready' | 'error'
  extraction_model?: string
  summarization_model?: string
  node_count: number
  edge_count: number
  last_built_at?: string
  created_at: string
}

export interface KBCreate {
  name: string
  description?: string
  space_id?: string
  room_id?: string
  source_type?: string
  extraction_model?: string
  summarization_model?: string
}

export interface KBUpdate {
  name?: string
  description?: string
  extraction_model?: string
  summarization_model?: string
}
