<template>
  <div>
    <el-card style="margin-bottom: 10px">
      <el-row :gutter="10" align="middle">
        <el-col :span="6">
          <el-select v-model="selectedRunId" placeholder="选择运行记录" clearable filterable @change="loadLogs">
            <el-option label="全部日志" :value="null" />
            <el-option v-for="r in runs" :key="r.id" :label="`Run #${r.id} - ${r.status} (${r.started_at || ''})`" :value="r.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="logLevel" placeholder="日志级别" clearable @change="loadLogs">
            <el-option label="DEBUG" value="DEBUG" />
            <el-option label="INFO" value="INFO" />
            <el-option label="WARNING" value="WARNING" />
            <el-option label="ERROR" value="ERROR" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="keyword" placeholder="搜索关键词" clearable @keyup.enter="loadLogs" />
        </el-col>
        <el-col :span="8">
          <el-button type="primary" @click="loadLogs">搜索</el-button>
          <el-button @click="toggleRealtime" :type="realtime ? 'danger' : 'success'">
            {{ realtime ? '停止实时' : '实时日志' }}
          </el-button>
          <el-button @click="clearLogs">清空</el-button>
          <el-tag v-if="realtime" type="success" style="margin-left: 10px">● 实时连接中</el-tag>
        </el-col>
      </el-row>
    </el-card>

    <!-- Log display -->
    <el-card body-style="padding: 0">
      <div ref="logContainer" style="height: calc(100vh - 250px); overflow-y: auto; background: #1e1e1e; padding: 15px; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px">
        <div v-for="(log, i) in logs" :key="i" :style="{ color: logColor(log.level) }">
          <span style="color: #666">[{{ log.timestamp }}]</span>
          <span :style="{ color: levelColor(log.level), fontWeight: 'bold' }"> [{{ log.level }}]</span>
          <span> {{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" style="color: #666; text-align: center; padding: 40px">
          暂无日志。点击"实时日志"开始监听。
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getAllLogs, getLogs, getRecentRuns } from '../api'

const route = useRoute()
const logContainer = ref(null)
const logs = ref([])
const runs = ref([])
const selectedRunId = ref(null)
const logLevel = ref('')
const keyword = ref('')
const realtime = ref(false)
let ws = null

const logColor = (level) => ({ INFO: '#d4d4d4', WARNING: '#dcdcaa', ERROR: '#f44747', DEBUG: '#6a9955' }[level] || '#d4d4d4')
const levelColor = (level) => ({ INFO: '#4ec9b0', WARNING: '#d7ba7d', ERROR: '#f44747', DEBUG: '#6a9955' }[level] || '#d4d4d4')

const loadRuns = async () => {
  try {
    const res = await getRecentRuns(100)
    runs.value = res.data || []
  } catch (e) {}
}

const loadLogs = async () => {
  try {
    let res
    if (selectedRunId.value) {
      res = await getLogs({ run_id: selectedRunId.value, level: logLevel.value || undefined, keyword: keyword.value || undefined, page_size: 500 })
    } else {
      res = await getAllLogs({ page_size: 200 })
    }
    // Reverse to show oldest first (newest at bottom)
    logs.value = (res.data.items || []).reverse()
    await nextTick()
    scrollToBottom()
  } catch (e) {}
}

const scrollToBottom = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

const toggleRealtime = () => {
  if (realtime.value) {
    closeWs()
    realtime.value = false
  } else {
    openWs()
    realtime.value = true
  }
}

const openWs = () => {
  // Connect to backend WebSocket server (port 8000)
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = 'localhost:8000'  // Backend server
  const runId = selectedRunId.value || ''
  const url = runId ? `${protocol}//${host}/ws/log/${runId}` : `${protocol}//${host}/ws/logs`

  console.log('Connecting to WebSocket:', url)
  ws = new WebSocket(url)
  ws.onopen = () => {
    console.log('WebSocket connected')
  }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'log') {
        logs.value.push(data)
        // Keep max 5000 logs
        if (logs.value.length > 5000) logs.value.splice(0, 1000)
        nextTick(scrollToBottom)
      }
    } catch (e) { console.error('WebSocket message error:', e) }
  }
  ws.onclose = () => {
    console.log('WebSocket closed')
    if (realtime.value) {
      // Reconnect after 3s
      setTimeout(() => {
        if (realtime.value) openWs()
      }, 3000)
    }
  }
  ws.onerror = (e) => { console.error('WebSocket error:', e) }
}

const closeWs = () => {
  if (ws) { ws.close(); ws = null }
}

const clearLogs = () => { logs.value = [] }

onMounted(async () => {
  // Load runs for the dropdown
  await loadRuns()
  // Load runs for the selected task
  if (route.params.runId) {
    selectedRunId.value = parseInt(route.params.runId)
  }
  await loadLogs()
})

onBeforeUnmount(() => { closeWs() })
</script>
