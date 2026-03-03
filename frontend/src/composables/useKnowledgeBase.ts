import { ref } from 'vue';
import * as knowledgeService from '@/services/knowledgeService';
import type { KnowledgeBase, KBCreate, KBUpdate } from '@/types/knowledge';

export function useKnowledgeBase() {
  const knowledgeBases = ref<KnowledgeBase[]>([]);
  const currentKB = ref<KnowledgeBase | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchKBs(params?: { space_id?: string; room_id?: string }) {
    loading.value = true;
    error.value = null;
    try {
      knowledgeBases.value = await knowledgeService.listKBs(params);
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to load knowledge bases';
    } finally {
      loading.value = false;
    }
  }

  async function createKB(payload: KBCreate): Promise<KnowledgeBase | null> {
    try {
      const kb = await knowledgeService.createKB(payload);
      knowledgeBases.value.push(kb);
      return kb;
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to create knowledge base';
      return null;
    }
  }

  async function updateKB(kbId: string, payload: KBUpdate): Promise<KnowledgeBase | null> {
    try {
      const kb = await knowledgeService.updateKB(kbId, payload);
      const idx = knowledgeBases.value.findIndex(k => k.id === kbId);
      if (idx !== -1) knowledgeBases.value[idx] = kb;
      return kb;
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to update knowledge base';
      return null;
    }
  }

  async function deleteKB(kbId: string): Promise<boolean> {
    try {
      await knowledgeService.deleteKB(kbId);
      knowledgeBases.value = knowledgeBases.value.filter(k => k.id !== kbId);
      return true;
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to delete knowledge base';
      return false;
    }
  }

  async function buildKB(kbId: string): Promise<boolean> {
    try {
      await knowledgeService.buildKB(kbId);
      return true;
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to trigger build';
      return false;
    }
  }

  async function mergeKB(targetKbId: string, sourceKbId: string): Promise<boolean> {
    try {
      await knowledgeService.mergeKB(targetKbId, sourceKbId);
      return true;
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to merge knowledge bases';
      return false;
    }
  }

  return {
    knowledgeBases,
    currentKB,
    loading,
    error,
    fetchKBs,
    createKB,
    updateKB,
    deleteKB,
    buildKB,
    mergeKB,
  };
}
