<template>
  <el-tag :type="tagType" :size="size" :effect="effect">
    {{ label }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  size: { type: String, default: 'default' },
  effect: { type: String, default: 'light' },
})

const statusMap = {
  // Task status
  idle: { type: 'info', label: '空闲' },
  running: { type: '', label: '运行中' },
  paused: { type: 'warning', label: '暂停' },
  error: { type: 'danger', label: '错误' },
  // Run status
  pending: { type: 'info', label: '等待中' },
  success: { type: 'success', label: '成功' },
  failed: { type: 'danger', label: '失败' },
  timeout: { type: 'warning', label: '超时' },
  cancelled: { type: 'warning', label: '已取消' },
  // Log levels
  INFO: { type: 'info', label: 'INFO' },
  DEBUG: { type: 'info', label: 'DEBUG' },
  WARNING: { type: 'warning', label: 'WARN' },
  ERROR: { type: 'danger', label: 'ERROR' },
  WARN: { type: 'warning', label: 'WARN' },
}

const tagType = computed(() => statusMap[props.status]?.type || 'info')
const label = computed(() => statusMap[props.status]?.label || props.status)
</script>
