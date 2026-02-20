import api from '../api'
import { API_ENDPOINTS } from '../constants/api'
import type { Organization, Project } from '../types/workspace'

export const workspaceService = {
    // Organizations
    getOrganizations: () => api.get<Organization[]>(API_ENDPOINTS.ORGANIZATIONS.BASE),
    createOrganization: (data: Partial<Organization>) => api.post<Organization>(API_ENDPOINTS.ORGANIZATIONS.BASE, data),
    getOrganization: (orgId: string) => api.get<Organization>(`${API_ENDPOINTS.ORGANIZATIONS.BASE}/${orgId}`),

    // Projects
    getProjects: (orgId?: string) => api.get<Project[]>(API_ENDPOINTS.PROJECTS.BASE, { params: { org_id: orgId } }),
    createProject: (data: Partial<Project>) => api.post<Project>(API_ENDPOINTS.PROJECTS.BASE, data),
    getProject: (projectId: string) => api.get<Project>(`${API_ENDPOINTS.PROJECTS.BASE}/${projectId}`)
}
