<template>
  <div>
    <!-- Toolbar -->
    <el-card style="margin-bottom: 20px">
      <el-row :gutter="10" align="middle">
        <el-col :span="5">
          <div style="display: flex; gap: 5px">
            <el-select v-model="filterGroup" placeholder="分组筛选" clearable @change="loadTasks" style="flex: 1">
              <el-option v-for="g in groups" :key="g.name" :label="g.name" :value="g.name" />
            </el-select>
            <el-button type="primary" @click="showGroupManage = true" title="管理分组">
              <el-icon><Setting /></el-icon>
            </el-button>
          </div>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="loadTasks">
            <el-option label="空闲" value="idle" />
            <el-option label="运行中" value="running" />
            <el-option label="暂停" value="paused" />
            <el-option label="错误" value="error" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-button type="primary" @click="handleAddTask">
            <el-icon><Plus /></el-icon> 新建任务
          </el-button>
          <el-button @click="loadTasks">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-tag v-if="autoRefresh" type="success" style="margin-left: 10px">
            自动刷新中 ({{ refreshCountdown }}s)
          </el-tag>
        </el-col>
      </el-row>
    </el-card>

    <!-- Task table -->
    <el-card>
      <el-table :data="tasks" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="50" />
        <el-table-column prop="name" label="任务名称" min-width="120">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/tasks/${row.id}`)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" label="类型" width="65">
          <template #default="{ row }">
            <el-tag size="small" :type="row.task_type === 'smart' ? 'success' : 'info'">
              {{ row.task_type === 'smart' ? '智能' : '专业' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="group_name" label="分组" width="90">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.group_name || '默认分组' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="engine" label="引擎" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.engine }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="65">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_crawled" label="采集量" width="70" align="center">
          <template #default="{ row }">
            <el-link v-if="row.total_crawled > 0" type="primary" @click="viewTaskData(row)">{{ row.total_crawled }}</el-link>
            <span v-else :style="{ color: row.status === 'running' ? '#409eff' : '' }">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_parsed" label="解析量" width="70" align="center">
          <template #default="{ row }">
            <el-link v-if="row.total_parsed > 0" type="success" @click="viewTaskData(row)">{{ row.total_parsed }}</el-link>
            <span v-else :style="{ color: row.status === 'running' ? '#67c23a' : '' }">0</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_at" label="最后运行" width="150" />
        <el-table-column label="操作" min-width="280" fixed="right" align="center">
          <template #header>
            <span style="display: inline-block; width: 100%; text-align: center;">操作</span>
          </template>
          <template #default="{ row }">
            <div style="display: flex; gap: 8px; flex-wrap: nowrap; align-items: center; justify-content: center;">
              <el-dropdown :disabled="row.status === 'running'" @command="(cmd) => handleRun(row, cmd)" size="small">
                <el-button size="small" type="success" :disabled="row.status === 'running'">
                  <el-icon><VideoPlay /></el-icon> 启动
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="full">完整运行</el-dropdown-item>
                    <el-dropdown-item command="crawl">仅采集</el-dropdown-item>
                    <el-dropdown-item command="parse">仅解析</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button size="small" type="warning" :disabled="row.status !== 'running'" @click="handleStop(row)">
                <el-icon><VideoPause /></el-icon> 停止
              </el-button>
              <el-button size="small" @click="goToConfig(row)" title="配置">
                <el-icon><Setting /></el-icon>
              </el-button>
              <el-button size="small" @click="$router.push(`/editor/${row.id}/full`)" title="编辑">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)" title="删除">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 15px; text-align: right"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadTasks"
      />
    </el-card>

    <!-- 分组管理对话框 -->
    <el-dialog v-model="showGroupManage" title="分组管理" width="500">
      <div style="margin-bottom: 15px">
        <div style="display: flex; gap: 10px">
          <el-input v-model="newGroupName" placeholder="输入新分组名称" @keyup.enter="addGroup" />
          <el-button type="primary" @click="addGroup">
            <el-icon><Plus /></el-icon> 添加分组
          </el-button>
        </div>
      </div>
      <el-divider />
      <div style="max-height: 400px; overflow-y: auto;">
        <el-table :data="groups" size="small">
          <el-table-column prop="name" label="分组名称" />
          <el-table-column label="任务数" width="80">
            <template #default="{ row }">
              {{ getGroupCount(row.name) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button v-if="row.name !== '默认分组'" type="primary" size="small" text @click="renameGroup(row)">
                重命名
              </el-button>
              <el-button v-if="row.name !== '默认分组'" type="danger" size="small" text @click="deleteGroup(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 重命名分组对话框 -->
    <el-dialog v-model="showRenameGroup" title="重命名分组" width="400">
      <el-form label-width="80px">
        <el-form-item label="新名称">
          <el-input v-model="renameGroupForm.newName" placeholder="输入新的分组名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRenameGroup = false">取消</el-button>
        <el-button type="primary" @click="handleRenameGroup">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="showCreate" title="新建专业采集任务" width="500">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="createForm.name" placeholder="输入任务名称" />
        </el-form-item>
        <el-form-item label="分组">
          <div style="display: flex; gap: 10px; width: 100%">
            <el-select v-model="createForm.group_name" style="flex: 1" placeholder="选择分组">
              <el-option v-for="g in groups" :key="g.name" :label="g.name" :value="g.name" />
            </el-select>
            <el-button @click="showGroupManage = true" title="管理分组">
              <el-icon><Setting /></el-icon>
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="引擎">
          <el-select v-model="createForm.engine" style="width: 100%">
            <el-option v-for="eng in engines" :key="eng.name" :label="eng.name" :value="eng.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标URL">
          <el-input v-model="createForm.config_json.url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 数据查看对话框 -->
    <el-dialog v-model="showDataDialog" :title="`数据列表 - ${currentDataTask?.name || ''}`" width="90%" top="5vh">
      <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <el-tag type="info" style="margin-right: 10px">共 {{ taskDataList.length }} 条数据</el-tag>
          <el-tag v-if="currentDataTask" type="success">{{ currentDataTask.group_name || '默认分组' }}</el-tag>
        </div>
        <el-space>
          <el-button type="success" @click="exportDataTask">
            <el-icon><Download /></el-icon> 导出Excel
          </el-button>
          <el-button type="warning" @click="exportDataTaskJson">
            <el-icon><Download /></el-icon> 导出JSON
          </el-button>
        </el-space>
      </div>

      <el-table :data="taskDataList" stripe max-height="500" v-loading="dataLoading" @row-click="showDataDetail" highlight-current-row style="cursor: pointer;">
        <el-table-column prop="id" label="ID" width="60" fixed />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="100" show-overflow-tooltip />
        <el-table-column prop="chubanriqi" label="出版日期" width="120" />
        <el-table-column prop="parseflag" label="解析状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.parseflag === 1 ? 'success' : 'info'" size="small">
              {{ row.parseflag === 1 ? '已解析' : '未解析' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creationtime" label="入库时间" width="150" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click.stop="showDataDetail(row)">
              <el-icon><View /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 数据详情抽屉 -->
    <el-drawer v-model="showDataDrawer" :title="`数据详情 #${detailData?.id || ''}`" size="45%" direction="rtl">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="ID">{{ detailData.id }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.title" label="标题">
            <div style="max-width: 500px; word-break: break-all;">{{ detailData.title }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailData.url" label="URL">
            <el-link type="primary" :href="detailData.url" target="_blank" style="max-width: 500px; word-break: break-all;">{{ detailData.url }}</el-link>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailData.content" label="正文内容">
            <div style="max-height: 300px; overflow-y: auto; white-space: pre-wrap; background: #f5f7fa; padding: 10px; border-radius: 4px; font-size: 13px;">{{ detailData.content }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailData.abstract" label="摘要">
            <div style="max-height: 150px; overflow-y: auto; white-space: pre-wrap;">{{ detailData.abstract }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailData.author || detailData.zuozhe" label="作者">{{ detailData.author || detailData.zuozhe }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.chubanriqi" label="出版日期">{{ detailData.chubanriqi }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.keyword" label="关键词">{{ detailData.keyword }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.kanming" label="来源/刊名">{{ detailData.kanming }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.wwwimages" label="图片">
            <div style="max-width: 500px; word-break: break-all;">{{ detailData.wwwimages }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailData.tag" label="标签">{{ detailData.tag }}</el-descriptions-item>
          <el-descriptions-item label="解析状态">
            <el-tag :type="detailData.parseflag === 1 ? 'success' : 'info'">
              {{ detailData.parseflag === 1 ? '已解析' : '未解析' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailData.creationtime" label="入库时间">{{ detailData.creationtime }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.lastmodifiedtime" label="最后修改">{{ detailData.lastmodifiedtime }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.spider_name" label="任务标识">{{ detailData.spider_name }}</el-descriptions-item>
        </el-descriptions>

        <!-- 扩展字段 -->
        <div v-if="hasExtraFields" style="margin-top: 15px;">
          <el-divider content-position="left">扩展字段</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item v-for="(val, key) in extraFields" :key="key" :label="key">
              <div style="max-width: 500px; word-break: break-all;">{{ val }}</div>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTasks, createTask, deleteTask, runTask, stopTask, getGroupList, createGroup, updateGroup, deleteGroup as apiDeleteGroup } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, View } from '@element-plus/icons-vue'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const tasks = ref([])
const groups = ref([])
const engines = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filterGroup = ref('')
const filterStatus = ref('')
const showCreate = ref(false)
const showGroupManage = ref(false)
const showRenameGroup = ref(false)
const creating = ref(false)
const newGroupName = ref('')

// 数据查看相关
const showDataDialog = ref(false)
const showDataDrawer = ref(false)
const currentDataTask = ref(null)
const taskDataList = ref([])
const detailData = ref(null)
const dataLoading = ref(false)

// 已知字段列表（不显示在扩展字段中）
const knownFields = ['id', 'title', 'url', 'content', 'abstract', 'author', 'zuozhe', 'chubanriqi', 'kanming', 'keyword', 'parseflag', 'creationtime', 'lastmodifiedtime', 'spider_name', 'solrid', 'tag', 'wwwimages', 'html']

// 扩展字段
const extraFields = computed(() => {
  if (!detailData.value) return {}
  const result = {}
  for (const [key, val] of Object.entries(detailData.value)) {
    if (!knownFields.includes(key) && val !== null && val !== undefined && val !== '') {
      result[key] = val
    }
  }
  return result
})

const hasExtraFields = computed(() => Object.keys(extraFields.value).length > 0)

// 根据路由判断任务类型筛选
const taskTypeFilter = computed(() => {
  if (route.path === '/smart-tasks') return 'smart'
  if (route.path === '/professional-tasks') return 'professional'
  return null // 全部
})

// 自动刷新相关
const autoRefresh = ref(false)
const refreshCountdown = ref(10)
let refreshTimer = null
let countdownTimer = null

const createForm = reactive({
  name: '',
  description: '',
  group_name: '默认分组',
  engine: 'requests',
  config_json: { url: '' },
  task_type: 'professional',
})

const renameGroupForm = reactive({
  id: null,
  oldName: '',
  newName: '',
})

const statusType = (s) => ({ idle: 'info', running: '', paused: 'warning', error: 'danger' }[s] || 'info')

const getGroupCount = (groupName) => {
  return tasks.value.filter(t => t.group_name === groupName).length
}

// 检查是否有运行中的任务
const hasRunningTasks = () => {
  return tasks.value.some(t => t.status === 'running')
}

// 启动自动刷新
const startAutoRefresh = () => {
  if (refreshTimer) return
  autoRefresh.value = true
  refreshCountdown.value = 60

  // 倒计时
  countdownTimer = setInterval(() => {
    refreshCountdown.value--
    if (refreshCountdown.value <= 0) {
      refreshCountdown.value = 60
    }
  }, 1000)

  // 定时刷新（每60秒）
  refreshTimer = setInterval(async () => {
    await loadTasks(true) // silent refresh
    if (!hasRunningTasks()) {
      stopAutoRefresh()
    }
  }, 60000)
}

// 停止自动刷新
const stopAutoRefresh = () => {
  autoRefresh.value = false
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

const loadTasks = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, group: filterGroup.value || undefined, status: filterStatus.value || undefined }
    if (taskTypeFilter.value) {
      params.task_type = taskTypeFilter.value
    }
    const res = await getTasks(params)
    tasks.value = res.data.items
    total.value = res.data.total
    
    // 如果有运行中的任务，启动自动刷新
    if (hasRunningTasks() && !autoRefresh.value) {
      startAutoRefresh()
    }
  } catch (e) {} finally { if (!silent) loading.value = false }
}

const loadGroups = async () => {
  try { 
    const res = await getGroupList()
    groups.value = res.data || []
  } catch (e) {
    console.error('加载分组失败:', e)
  }
}

const loadEngines = async () => {
  try {
    const res = await api.get('/engines/list')
    engines.value = res.data.data || []
  } catch (e) {
    console.error('加载引擎失败:', e)
  }
}

const addGroup = async () => {
  const name = newGroupName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分组名称')
    return
  }
  
  try {
    await createGroup({ name })
    ElMessage.success('分组创建成功')
    newGroupName.value = ''
    await loadGroups()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

const renameGroup = (group) => {
  renameGroupForm.id = group.id
  renameGroupForm.oldName = group.name
  renameGroupForm.newName = group.name
  showRenameGroup.value = true
}

const handleRenameGroup = async () => {
  const name = renameGroupForm.newName.trim()
  if (!name) {
    ElMessage.warning('请输入分组名称')
    return
  }
  
  try {
    await updateGroup(renameGroupForm.id, { name })
    ElMessage.success('分组重命名成功')
    showRenameGroup.value = false
    await loadGroups()
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重命名失败')
  }
}

const deleteGroup = async (group) => {
  try {
    await ElMessageBox.confirm(
      `确定删除分组 "${group.name}" ? 分组下的任务将移到"默认分组"。`,
      '确认删除',
      { type: 'warning' }
    )
    
    await apiDeleteGroup(group.id)
    ElMessage.success('分组已删除')
    await loadGroups()
    await loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

const handleCreate = async () => {
  if (!createForm.name) { ElMessage.warning('请输入任务名称'); return }
  creating.value = true
  try {
    await createTask(createForm)
    ElMessage.success('任务创建成功')
    showCreate.value = false
    createForm.name = ''
    createForm.description = ''
    createForm.config_json = { url: '' }
    createForm.task_type = 'professional'
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally { creating.value = false }
}

const handleRun = async (task, scriptType = 'full') => {
  try { 
    await runTask(task.id, scriptType)
    ElMessage.success('任务已启动')
    await loadTasks()
    // 启动自动刷新
    startAutoRefresh()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '启动失败')
  }
}

const handleStop = async (task) => {
  try { 
    await stopTask(task.id)
    ElMessage.success('任务已停止')
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '停止失败')
  }
}

const handleDelete = async (task) => {
  await ElMessageBox.confirm(`确定删除任务 "${task.name}" ?`, '确认')
  try { await deleteTask(task.id); ElMessage.success('已删除'); await loadTasks() } catch (e) {}
}

const handleAddTask = () => {
  // 智能采集菜单 - 直接跳转向导
  if (route.path === '/smart-tasks') {
    router.push('/smart-wizard')
    return
  }
  // 专业采集菜单 - 直接显示专业采集表单
  if (route.path === '/professional-tasks') {
    createForm.task_type = 'professional'
    showCreate.value = true
    return
  }
  // 全部任务 - 显示专业采集表单
  createForm.task_type = 'professional'
  showCreate.value = true
}

const goToConfig = (row) => {
  if (row.task_type === 'smart') {
    router.push(`/tasks/${row.id}/smart-config`)
  } else {
    router.push(`/tasks/${row.id}/config`)
  }
}

// 查看任务数据
const viewTaskData = async (row) => {
  currentDataTask.value = row
  showDataDialog.value = true
  dataLoading.value = true
  taskDataList.value = []

  try {
    const res = await api.get(`/data/task/${row.id}`)
    if (res.data.code === 0) {
      taskDataList.value = res.data.data || []
    }
  } catch (e) {
    console.error('加载数据失败:', e)
    ElMessage.error('加载数据失败')
  } finally {
    dataLoading.value = false
  }
}

// 查看数据详情
const showDataDetail = (row) => {
  detailData.value = row
  showDataDrawer.value = true
}

// 导出任务数据
const exportDataTask = async () => {
  if (!currentDataTask.value) return
  try {
    const res = await api.get(`/data/task/${currentDataTask.value.id}/export?format=excel`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${currentDataTask.value.name}_数据.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

// 导出任务数据为JSON
const exportDataTaskJson = async () => {
  if (!currentDataTask.value) return
  try {
    const res = await api.get(`/data/task/${currentDataTask.value.id}/export?format=json`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${currentDataTask.value.name}_数据.json`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  loadTasks()
  loadGroups()
  loadEngines()
})

// 监听路由变化，重新加载任务列表
watch(() => route.path, () => {
  page.value = 1
  loadTasks()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.detail-content {
  padding: 10px;
}
</style>
