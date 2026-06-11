<template>
  <div v-loading="loading">
    <!-- Task info -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>任务详情: {{ task.name }}</span>
          <el-space>
            <el-button type="success" :disabled="task.status === 'running'" @click="handleRun">
              <el-icon><VideoPlay /></el-icon> 启动
            </el-button>
            <el-button type="warning" :disabled="task.status !== 'running'" @click="handleStop">
              <el-icon><VideoPause /></el-icon> 停止
            </el-button>
            <el-button @click="goToConfig">{{ task.task_type === 'smart' ? '智能采集配置' : '可视化配置' }}</el-button>
            <el-button @click="$router.push(`/editor/${task.id}/full`)">编辑脚本</el-button>
          </el-space>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">
          <el-tag :type="task.task_type === 'smart' ? 'success' : 'info'">
            {{ task.task_type === 'smart' ? '智能采集' : '专业采集' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="分组">{{ task.group_name }}</el-descriptions-item>
        <el-descriptions-item label="引擎"><el-tag>{{ task.engine }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="statusType(task.status)">{{ task.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="采集量">{{ task.total_crawled }}</el-descriptions-item>
        <el-descriptions-item label="解析量">{{ task.total_parsed }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="3">{{ task.description || '无' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Scripts -->
    <el-card style="margin-bottom: 20px">
      <template #header><span>关联脚本</span></template>
      <el-tabs v-model="activeScript">
        <el-tab-pane v-for="s in scripts" :key="s.script_type" :label="scriptLabel(s.script_type)" :name="s.script_type">
          <div style="margin-bottom: 10px">
            <el-button size="small" @click="$router.push(`/editor/${task.id}/${s.script_type}`)">编辑</el-button>
            <el-button size="small" @click="handleRegenerate(s.script_type)">重新生成</el-button>
          </div>
          <pre style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; max-height: 300px; overflow: auto; font-size: 13px">{{ s.code.substring(0, 2000) }}{{ s.code.length > 2000 ? '\n...(truncated)' : '' }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Run history -->
    <el-card>
      <template #header><span>运行历史</span></template>
      <el-table :data="runs" stripe>
        <el-table-column prop="id" label="运行ID" width="80" />
        <el-table-column prop="trigger" label="触发方式" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180" />
        <el-table-column prop="duration_seconds" label="耗时(秒)" width="100" />
        <el-table-column prop="error_message" label="错误信息" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/logs/${row.id}`)">日志</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTask, getScripts, getTaskRuns, runTask, stopTask, regenerateScript } from '../api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id
const loading = ref(false)
const task = ref({})
const scripts = ref([])
const runs = ref([])
const activeScript = ref('full')

const statusType = (s) => ({ idle: 'info', running: '', paused: 'warning', error: 'danger', success: 'success', failed: 'danger', cancelled: 'warning' }[s] || 'info')
const scriptLabel = (t) => ({ crawl: '采集脚本', parse: '解析脚本', full: '完整脚本' }[t] || t)

const goToConfig = () => {
  if (task.value.task_type === 'smart') {
    router.push(`/tasks/${taskId}/smart-config`)
  } else {
    router.push(`/tasks/${taskId}/config`)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const [tRes, sRes, rRes] = await Promise.all([
      getTask(taskId), getScripts(taskId), getTaskRuns(taskId)
    ])
    task.value = tRes.data
    scripts.value = sRes.data
    runs.value = rRes.data
  } catch (e) {} finally { loading.value = false }
}

const handleRun = async () => {
  try { await runTask(taskId); ElMessage.success('已启动'); await loadData() } catch (e) {}
}
const handleStop = async () => {
  try { await stopTask(taskId); ElMessage.success('已停止'); await loadData() } catch (e) {}
}
const handleRegenerate = async (type) => {
  try { await regenerateScript(taskId, type); ElMessage.success('脚本已重新生成'); await loadData() } catch (e) {}
}

onMounted(loadData)
</script>
