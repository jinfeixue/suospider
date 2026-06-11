<template>
  <div>
    <!-- Stats cards -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6" v-for="item in statCards" :key="item.label">
        <el-card shadow="hover">
          <div style="display: flex; align-items: center">
            <el-icon :size="40" :color="item.color"><component :is="item.icon" /></el-icon>
            <div style="margin-left: 15px">
              <div style="font-size: 28px; font-weight: 700">{{ item.value }}</div>
              <div style="color: #999; font-size: 14px">{{ item.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Quick actions -->
    <el-card style="margin-bottom: 20px">
      <template #header><span>快速操作</span></template>
      <el-space>
        <el-button type="primary" @click="$router.push('/smart-wizard')">
          <el-icon><MagicStick /></el-icon> 智能采集
        </el-button>
        <el-button type="success" @click="$router.push('/professional-tasks')">
          <el-icon><List /></el-icon> 专业采集
        </el-button>
        <el-button @click="$router.push('/tasks')">
          <el-icon><FolderOpened /></el-icon> 全部任务
        </el-button>
        <el-button @click="$router.push('/datasource')">
          <el-icon><Connection /></el-icon> 数据源配置
        </el-button>
        <el-button @click="$router.push('/llm-config')">
          <el-icon><Cpu /></el-icon> 大模型配置
        </el-button>
        <el-button @click="$router.push('/editor')">
          <el-icon><Edit /></el-icon> 代码编辑
        </el-button>
        <el-button @click="$router.push('/logs')">
          <el-icon><Document /></el-icon> 日志中心
        </el-button>
      </el-space>
    </el-card>

    <!-- Recent runs -->
    <el-card>
      <template #header><span>最近任务运行</span></template>
      <el-table :data="recentRuns" stripe>
        <el-table-column prop="id" label="运行ID" width="80" />
        <el-table-column prop="task_id" label="任务ID" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" />
        <el-table-column prop="duration_seconds" label="耗时(秒)" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDataStats } from '../api'

const recentRuns = ref([])

const statCards = ref([
  { label: '总任务数', value: 0, icon: 'List', color: '#409eff' },
  { label: '运行中', value: 0, icon: 'VideoPlay', color: '#67c23a' },
  { label: '总采集量', value: 0, icon: 'Download', color: '#e6a23c' },
  { label: '总解析量', value: 0, icon: 'Finished', color: '#f56c6c' },
])

const statusType = (s) => ({ success: 'success', running: '', failed: 'danger', cancelled: 'warning', pending: 'info' }[s] || 'info')

onMounted(async () => {
  try {
    const res = await getDataStats()
    const d = res.data
    statCards.value[0].value = d.total_tasks
    statCards.value[1].value = d.running_tasks
    statCards.value[2].value = d.total_crawled
    statCards.value[3].value = d.total_parsed
    recentRuns.value = d.recent_runs || []
  } catch (e) {}
})
</script>
