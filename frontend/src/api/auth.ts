import { apiClient } from './client'

export const CAMPUSES = ['五山校区', '大学城校区', '广州国际校区'] as const
export type Campus = typeof CAMPUSES[number]

export interface CurrentUser {
  id: number
  nickname: string
  campus: Campus
  created_at: string
  student_no_masked: string
  is_admin?: boolean
}

export interface RegistrationInput {
  nickname: string
  student_no: string
  password: string
  campus: Campus | ''
}

export interface LoginInput {
  student_no: string
  password: string
}

function parseCurrentUser(data: unknown): CurrentUser {
  if (typeof data !== 'object' || data === null
    || !('id' in data) || typeof data.id !== 'number' || !Number.isInteger(data.id)
    || !('nickname' in data) || typeof data.nickname !== 'string'
    || !('campus' in data) || !CAMPUSES.some(campus => campus === data.campus)
    || !('created_at' in data) || typeof data.created_at !== 'string'
    || !('student_no_masked' in data) || typeof data.student_no_masked !== 'string' || !data.student_no_masked.includes('*')) {
    throw new Error('Invalid current user response')
  }
  return {
    id: data.id, nickname: data.nickname, campus: data.campus as Campus,
    created_at: data.created_at, student_no_masked: data.student_no_masked,
    is_admin: 'is_admin' in data && data.is_admin === true,
  }
}

export const authApi = {
  register: (payload: RegistrationInput) => apiClient.post('/auth/register', payload),
  login: async (payload: LoginInput) => parseCurrentUser(await apiClient.post('/auth/login', payload)),
  me: async (signal?: AbortSignal) => parseCurrentUser(await apiClient.get('/auth/me', signal)),
  logout: () => apiClient.post('/auth/logout'),
}
