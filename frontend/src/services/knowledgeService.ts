import api from '@/api'
import type { KnowledgeBase, KBCreate, KBUpdate } from '@/types/knowledge'

export async function listKBs(params?: {
  space_id?: string
  room_id?: string
}): Promise<KnowledgeBase[]> {
  const { data } = await api.get('/knowledge/', { params })
  return data
}

export async function createKB(payload: KBCreate): Promise<KnowledgeBase> {
  const { data } = await api.post('/knowledge/', payload)
  return data
}

export async function getKB(kbId: string): Promise<KnowledgeBase> {
  const { data } = await api.get(`/knowledge/${kbId}`)
  return data
}

export async function updateKB(kbId: string, payload: KBUpdate): Promise<KnowledgeBase> {
  const { data } = await api.put(`/knowledge/${kbId}`, payload)
  return data
}

export async function deleteKB(kbId: string): Promise<void> {
  await api.delete(`/knowledge/${kbId}`)
}

export async function buildKB(kbId: string): Promise<{ status: string }> {
  const { data } = await api.post(`/knowledge/${kbId}/build`)
  return data
}

export async function getKBStatus(
  kbId: string
): Promise<{ build_status: string; node_count: number; edge_count: number }> {
  const { data } = await api.get(`/knowledge/${kbId}/status`)
  return data
}

export async function mergeKB(kbId: string, sourceKbId: string): Promise<void> {
  await api.post(`/knowledge/${kbId}/merge`, { source_kb_id: sourceKbId })
}

export async function queryKB(kbId: string, question: string): Promise<any> {
  const { data } = await api.post(`/knowledge/${kbId}/query`, { question })
  return data
}

export async function uploadDocument(kbId: string, file: File): Promise<void> {
  const formData = new FormData()
  formData.append('file', file)
  await api.post(`/knowledge/${kbId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
