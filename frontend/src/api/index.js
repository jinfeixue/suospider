import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 180000,  // 3分钟，AI分析需要较长时间
  maxContentLength: Infinity,
  maxBodyLength: Infinity,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code !== 0) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(data)
    }
    return data
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    } else {
      ElMessage.error(error.response?.data?.detail || error.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (data) => api.post('/auth/login', data)
export const getMe = () => api.get('/auth/me')

// Tasks
export const getTasks = (params) => api.get('/tasks', { params })
export const getTask = (id) => api.get(`/tasks/${id}`)
export const createTask = (data) => api.post('/tasks', data)
export const updateTask = (id, data) => api.put(`/tasks/${id}`, data)
export const deleteTask = (id) => api.delete(`/tasks/${id}`)
export const runTask = (id, scriptType = 'full') => api.post(`/tasks/${id}/run?script_type=${scriptType}`)
export const stopTask = (id) => api.post(`/tasks/${id}/stop`)
export const resetParseFlag = (id) => api.post(`/tasks/${id}/reset-parse`)
export const getTaskRuns = (id) => api.get(`/tasks/${id}/runs`)

// Groups - 使用新的持久化接口
export const getGroups = async () => {
  try {
    const res = await api.get('/groups/names')
    return res
  } catch (e) {
    // 兼容旧接口
    const res = await api.get('/tasks/groups')
    return res
  }
}
export const getGroupList = () => api.get('/groups')
export const createGroup = (data) => api.post('/groups', data)
export const updateGroup = (id, data) => api.put(`/groups/${id}`, data)
export const deleteGroup = (id) => api.delete(`/groups/${id}`)

// Scripts
export const getScripts = (taskId) => api.get(`/tasks/${taskId}/scripts`)
export const getScript = (taskId, type) => api.get(`/tasks/${taskId}/scripts/${type}`)
export const updateScript = (taskId, type, code) => api.put(`/tasks/${taskId}/scripts/${type}`, { code })
export const regenerateScript = (taskId, type) => api.post(`/tasks/${taskId}/scripts/${type}/regenerate`)
export const validateScript = (code) => api.post('/scripts/validate', { code })

// Logs
export const getLogs = (params) => api.get('/logs', { params })
export const getAllLogs = (params) => api.get('/logs/all', { params })

// Data
export const getData = (runId) => api.get(`/data/${runId}`)
export const exportData = (runId, format) => `/api/v1/data/${runId}/export?format=${format}`
export const getDataStats = () => api.get('/data/stats/overview')
export const getRecentRuns = (limit) => api.get('/data/runs/recent', { params: { limit } })
export const testDbConnection = (data) => api.post('/data/test-db', data)
export const createDatabase = (data) => api.post('/data/create-db', data)

// Engines
export const getEngines = () => api.get('/engines')
export const testEngine = (data) => api.post('/engines/test', data)

// LLM Configs
export const getLLMConfigs = () => api.get('/llm-config/')
export const getLLMConfig = (id) => api.get(`/llm-config/${id}`)
export const createLLMConfig = (data) => api.post('/llm-config/', data)
export const updateLLMConfig = (id, data) => api.put(`/llm-config/${id}`, data)
export const deleteLLMConfig = (id) => api.delete(`/llm-config/${id}`)
export const testLLMConfig = (id) => api.post(`/llm-config/${id}/test`)
export const setDefaultLLMConfig = (id) => api.post(`/llm-config/${id}/set-default`)

// DataSources
export const getDataSources = () => api.get('/datasource/')
export const getDataSource = (id) => api.get(`/datasource/${id}`)
export const createDataSource = (data) => api.post('/datasource/', data)
export const updateDataSource = (id, data) => api.put(`/datasource/${id}`, data)
export const deleteDataSource = (id) => api.delete(`/datasource/${id}`)
export const testDataSource = (id) => api.post(`/datasource/${id}/test`)
export const initDataSourceDB = (id) => api.post(`/datasource/${id}/init-db`)
export const getDataSourceColumns = (id) => api.get(`/datasource/${id}/columns`)

// AI Analysis
export const analyzeWebpage = (data) => api.post('/ai/analyze', data)
export const smartCreateTask = (data) => api.post('/ai/smart-create', data)

// Schedules
export const getSchedules = (taskId) => api.get(`/tasks/${taskId}/schedules`)
export const createSchedule = (taskId, data) => api.post(`/tasks/${taskId}/schedules`, data)
export const deleteSchedule = (id) => api.delete(`/schedules/${id}`)
export const toggleSchedule = (id) => api.post(`/schedules/${id}/toggle`)

export default api
