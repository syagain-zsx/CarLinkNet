import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    ElMessage.error(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : '请求失败')
    return Promise.reject(err)
  }
)

export default http
