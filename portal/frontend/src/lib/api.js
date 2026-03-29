import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  paramsSerializer: {
    // FastAPI ожидает массивы как: user_ids=1&user_ids=2, а не user_ids[]=1
    indexes: null,
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('portal_jwt')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

