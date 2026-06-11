/**
 * Task Store - manages task list and current task state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getTasks as apiGetTasks,
  getTask as apiGetTask,
  createTask as apiCreateTask,
  updateTask as apiUpdateTask,
  deleteTask as apiDeleteTask,
  runTask as apiRunTask,
  stopTask as apiStopTask,
  getTaskRuns,
  getGroups as apiGetGroups,
} from '../api'

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const groups = ref([])
  const runs = ref([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const filters = ref({ group: '', status: '' })

  // Getters
  const runningTasks = computed(() => tasks.value.filter(t => t.status === 'running'))
  const idleTasks = computed(() => tasks.value.filter(t => t.status === 'idle'))

  // Actions
  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      const res = await apiGetTasks({
        page: page.value,
        page_size: pageSize.value,
        ...filters.value,
        ...params,
      })
      tasks.value = res.data.items
      total.value = res.data.total
    } catch (e) {
      console.error('Failed to fetch tasks:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id) {
    loading.value = true
    try {
      const res = await apiGetTask(id)
      currentTask.value = res.data
      return res.data
    } catch (e) {
      console.error('Failed to fetch task:', e)
      return null
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    const res = await apiCreateTask(data)
    await fetchTasks()
    await fetchGroups()
    return res.data
  }

  async function updateTask(id, data) {
    const res = await apiUpdateTask(id, data)
    await fetchTasks()
    if (currentTask.value?.id === id) {
      await fetchTask(id)
    }
    return res.data
  }

  async function deleteTask(id) {
    await apiDeleteTask(id)
    await fetchTasks()
    await fetchGroups()
  }

  async function runTask(id) {
    const res = await apiRunTask(id)
    await fetchTasks()
    return res.data
  }

  async function stopTask(id) {
    const res = await apiStopTask(id)
    await fetchTasks()
    return res.data
  }

  async function fetchRuns(taskId) {
    const res = await getTaskRuns(taskId)
    runs.value = res.data
    return res.data
  }

  async function fetchGroups() {
    try {
      const res = await apiGetGroups()
      groups.value = res.data
    } catch (e) {
      console.error('Failed to fetch groups:', e)
    }
  }

  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
  }

  function setPage(p) {
    page.value = p
  }

  return {
    tasks,
    currentTask,
    groups,
    runs,
    loading,
    total,
    page,
    pageSize,
    filters,
    runningTasks,
    idleTasks,
    fetchTasks,
    fetchTask,
    createTask,
    updateTask,
    deleteTask,
    runTask,
    stopTask,
    fetchRuns,
    fetchGroups,
    setFilters,
    setPage,
  }
})
