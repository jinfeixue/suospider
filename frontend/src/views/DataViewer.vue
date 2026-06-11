<template>
  <div>
    <!-- 筛选工具栏 -->
    <el-card style="margin-bottom: 20px">
      <el-row :gutter="10" align="middle">
        <el-col :span="4">
          <el-select v-model="filterGroup" placeholder="按分组筛选" clearable @change="loadTasks">
            <el-option v-for="g in groups" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterTaskType" placeholder="按类型筛选" clearable @change="loadTasks">
            <el-option label="智能采集" value="smart" />
            <el-option label="专业采集" value="professional" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-input v-model="searchKeyword" placeholder="搜索任务名称" clearable @keyup.enter="loadTasks" />
        </el-col>
        <el-col :span="5">
          <el-button type="primary" @click="loadTasks">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetFilter">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 任务列表 -->
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>任务数据列表</span>
          <el-tag type="info">共 {{ filteredTasks.length }} 个任务</el-tag>
        </div>
      </template>

      <el-table :data="filteredTasks" stripe v-loading="loading" @row-click="selectTask" highlight-current-row style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="任务名称" min-width="180">
          <template #default="{ row }">
            <el-link type="primary">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.task_type === 'smart' ? 'success' : 'info'">
              {{ row.task_type === 'smart' ? '智能' : '专业' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="group_name" label="分组" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.group_name || '默认分组' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_crawled" label="采集量" width="80" align="center" />
        <el-table-column prop="total_parsed" label="解析量" width="80" align="center" />
        <el-table-column prop="last_run_at" label="最后运行" width="170" />
        <el-table-column label="操作" min-width="200" fixed="right">
          <template #header>
            <div style="text-align: center;">操作</div>
          </template>
          <template #default="{ row }">
            <div style="display: flex; gap: 8px; justify-content: center;">
              <el-button size="small" type="primary" @click.stop="viewData(row)">
                <el-icon><View /></el-icon> 查看数据
              </el-button>
              <el-dropdown @command="(cmd) => handleExport(row, cmd)">
                <el-button size="small" type="success">
                  <el-icon><Download /></el-icon> 导出
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                    <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 数据列表对话框 -->
    <el-dialog v-model="showDataDialog" :title="`数据列表 - ${currentTask?.name || ''}`" width="90%" top="5vh">
      <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <el-tag type="info" style="margin-right: 10px">共 {{ taskData.length }} 条数据</el-tag>
          <el-tag v-if="currentTask" type="success">{{ currentTask.group_name || '默认分组' }}</el-tag>
        </div>
        <el-space>
          <el-button type="success" @click="exportTaskData(currentTask)">
            <el-icon><Download /></el-icon> 导出Excel
          </el-button>
          <el-button type="warning" @click="exportJson(currentTask)">
            <el-icon><Download /></el-icon> 导出JSON
          </el-button>
        </el-space>
      </div>

      <el-table :data="taskData" stripe max-height="500" v-loading="dataLoading" @row-click="showRowDetail" highlight-current-row style="cursor: pointer;">
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
            <el-button size="small" type="primary" @click.stop="showRowDetail(row)">
              <el-icon><View /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 数据详情抽屉 -->
    <el-drawer v-model="showDetailDrawer" :title="`数据详情 #${detailRow?.id || ''}`" size="45%" direction="rtl">
      <div v-if="detailRow" class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="ID">{{ detailRow.id }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.title" label="标题">
            <div style="max-width: 500px; word-break: break-all;">{{ detailRow.title }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.url" label="URL">
            <el-link type="primary" :href="detailRow.url" target="_blank" style="max-width: 500px; word-break: break-all;">{{ detailRow.url }}</el-link>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.content" label="正文内容">
            <div style="max-height: 300px; overflow-y: auto; white-space: pre-wrap; background: #f5f7fa; padding: 10px; border-radius: 4px; font-size: 13px;">{{ detailRow.content }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.abstract" label="摘要">
            <div style="max-height: 150px; overflow-y: auto; white-space: pre-wrap;">{{ detailRow.abstract }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.author || detailRow.zuozhe" label="作者">{{ detailRow.author || detailRow.zuozhe }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.chubanriqi" label="出版日期">{{ detailRow.chubanriqi }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.keyword" label="关键词">{{ detailRow.keyword }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.kanming" label="来源/刊名">{{ detailRow.kanming }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.wwwimages" label="图片">
            <div style="max-width: 500px; word-break: break-all;">{{ detailRow.wwwimages }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.tag" label="标签">{{ detailRow.tag }}</el-descriptions-item>
          <el-descriptions-item label="解析状态">
            <el-tag :type="detailRow.parseflag === 1 ? 'success' : 'info'">
              {{ detailRow.parseflag === 1 ? '已解析' : '未解析' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.creationtime" label="入库时间">{{ detailRow.creationtime }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.lastmodifiedtime" label="最后修改">{{ detailRow.lastmodifiedtime }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.spider_name" label="任务标识">{{ detailRow.spider_name }}</el-descriptions-item>
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
import { ref, computed, onMounted } from 'vue'
import { getTasks, getGroupList } from '../api'
import { ElMessage } from 'element-plus'
import { Search, Refresh, View, Download } from '@element-plus/icons-vue'
import api from '../api'

const tasks = ref([])
const groups = ref([])
const loading = ref(false)
const dataLoading = ref(false)
const filterGroup = ref('')
const filterTaskType = ref('')
const searchKeyword = ref('')
const showDataDialog = ref(false)
const currentTask = ref(null)
const taskData = ref([])

// 数据详情抽屉
const showDetailDrawer = ref(false)
const detailRow = ref(null)

// 已知字段列表（不显示在扩展字段中）
const knownFields = ['id', 'title', 'url', 'content', 'abstract', 'author', 'zuozhe', 'chubanriqi', 'kanming', 'keyword', 'parseflag', 'creationtime', 'lastmodifiedtime', 'spider_name', 'solrid', 'tag', 'wwwimages', 'html']

// 扩展字段
const extraFields = computed(() => {
  if (!detailRow.value) return {}
  const result = {}
  for (const [key, val] of Object.entries(detailRow.value)) {
    if (!knownFields.includes(key) && val !== null && val !== undefined && val !== '') {
      result[key] = val
    }
  }
  return result
})

const hasExtraFields = computed(() => Object.keys(extraFields.value).length > 0)

// 筛选后的任务列表
const filteredTasks = computed(() => {
  let result = tasks.value

  if (filterGroup.value) {
    result = result.filter(t => t.group_name === filterGroup.value)
  }

  if (filterTaskType.value) {
    result = result.filter(t => t.task_type === filterTaskType.value)
  }

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(t => t.name.toLowerCase().includes(keyword))
  }

  return result
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getTasks({ page: 1, page_size: 1000 })
    tasks.value = res.data.items || []
  } catch (e) {
    console.error('加载任务失败:', e)
  } finally {
    loading.value = false
  }
}

const loadGroups = async () => {
  try {
    const res = await getGroupList()
    groups.value = res.data || []
  } catch (e) {
    console.error('加载分组失败:', e)
  }
}

const resetFilter = () => {
  filterGroup.value = ''
  filterTaskType.value = ''
  searchKeyword.value = ''
}

const selectTask = (row) => {
  viewData(row)
}

const viewData = async (task) => {
  currentTask.value = task
  dataLoading.value = true
  showDataDialog.value = true
  taskData.value = []

  try {
    const res = await api.get(`/data/task/${task.id}`)
    // api interceptor returns response.data directly, so res = {code: 0, data: [...]}
    if (res.code === 0) {
      taskData.value = res.data || []
    }
  } catch (e) {
    console.error('加载数据失败:', e)
    ElMessage.error('加载数据失败')
  } finally {
    dataLoading.value = false
  }
}

// 点击数据行显示详情抽屉
const showRowDetail = (row) => {
  detailRow.value = row
  showDetailDrawer.value = true
}

const loadData = async () => {
  if (filterTaskId.value) {
    const task = tasks.value.find(t => t.id === filterTaskId.value)
    if (task) {
      await viewData(task)
    }
  }
}

const handleExport = (task, format) => {
  if (format === 'excel') {
    exportTaskData(task)
  } else {
    exportJson(task)
  }
}

const exportTaskData = async (task) => {
  try {
    const res = await api.get(`/data/task/${task.id}/export?format=excel`, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${task.name}_数据.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const exportJson = async (task) => {
  try {
    const res = await api.get(`/data/task/${task.id}/export?format=json`, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${task.name}_数据.json`)
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
})
</script>

<style scoped>
.detail-content {
  padding: 10px;
}
</style>
