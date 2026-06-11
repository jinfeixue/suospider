/**
 * App Store - global application state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getDataStats, getEngines } from '../api'

export const useAppStore = defineStore('app', () => {
  // State
  const stats = ref({
    total_tasks: 0,
    running_tasks: 0,
    total_runs: 0,
    total_crawled: 0,
  })
  const engines = ref([])
  const sidebarCollapsed = ref(false)
  const wsConnections = ref({})

  // Getters
  const availableEngines = computed(() => engines.value)
  const isAnyTaskRunning = computed(() => stats.value.running_tasks > 0)

  // Actions
  async function fetchStats() {
    try {
      const res = await getDataStats()
      stats.value = res.data
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  async function fetchEngines() {
    try {
      const res = await getEngines()
      engines.value = res.data
    } catch (e) {
      console.error('Failed to fetch engines:', e)
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // WebSocket management for real-time logs
  function connectLogWs(runId, onMessage) {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/log/${runId}`
    const ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('WS parse error:', e)
      }
    }

    ws.onclose = () => {
      delete wsConnections.value[runId]
    }

    wsConnections.value[runId] = ws
    return ws
  }

  function connectGlobalLogWs(onMessage) {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/logs`
    const ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('WS parse error:', e)
      }
    }

    wsConnections.value['global'] = ws
    return ws
  }

  function disconnectWs(key) {
    const ws = wsConnections.value[key]
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close()
    }
    delete wsConnections.value[key]
  }

  function disconnectAllWs() {
    Object.keys(wsConnections.value).forEach(key => {
      disconnectWs(key)
    })
  }

  return {
    stats,
    engines,
    sidebarCollapsed,
    wsConnections,
    availableEngines,
    isAnyTaskRunning,
    fetchStats,
    fetchEngines,
    toggleSidebar,
    connectLogWs,
    connectGlobalLogWs,
    disconnectWs,
    disconnectAllWs,
  }
})
