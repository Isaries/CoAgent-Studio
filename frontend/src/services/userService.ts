import api from '../api'
import type { User, CreateUserPayload, UpdateUserPayload } from '../types/user'

export const userService = {
    async getUsers(params?: { skip?: number; limit?: number; search?: string }) {
        return api.get<User[]>('/users/', { params })
    },

    async getUser(id: string) {
        return api.get<User>(`/users/${id}`)
    },

    async createUser(payload: CreateUserPayload) {
        return api.post<User>('/users/', payload)
    },

    async updateUser(id: string, payload: UpdateUserPayload) {
        return api.put<User>(`/users/${id}`, payload)
    },

    async deleteUser(id: string) {
        return api.delete(`/users/${id}`)
    }
}
