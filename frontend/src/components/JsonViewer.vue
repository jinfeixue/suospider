<template>
  <div class="json-viewer">
    <div class="json-toolbar">
      <el-space>
        <el-button size="small" @click="toggleExpand">
          {{ allExpanded ? '折叠全部' : '展开全部' }}
        </el-button>
        <el-button size="small" @click="copyJson">复制</el-button>
        <el-tag size="small" type="info">{{ itemCount }} 项</el-tag>
      </el-space>
    </div>
    <div class="json-content">
      <div v-if="Array.isArray(data) && data.length > 0">
        <el-table :data="paginatedData" stripe border size="small" max-height="400">
          <el-table-column
            v-for="col in columns"
            :key="col"
            :prop="col"
            :label="col"
            :min-width="getColumnWidth(col)"
            show-overflow-tooltip
          />
        </el-table>
        <el-pagination
          v-if="data.length > pageSize"
          style="margin-top: 10px; text-align: right"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="data.length"
          layout="total, prev, pager, next"
        />
      </div>
      <div v-else-if="typeof data === 'object' && data !== null">
        <pre class="json-raw">{{ JSON.stringify(data, null, 2) }}</pre>
      </div>
      <div v-else class="json-empty">暂无数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  data: { type: [Array, Object], default: () => [] },
  pageSize: { type: Number, default: 20 },
})

const currentPage = ref(1)
const allExpanded = ref(true)

const itemCount = computed(() => {
  if (Array.isArray(props.data)) return props.data.length
  if (typeof props.data === 'object') return Object.keys(props.data).length
  return 0
})

const columns = computed(() => {
  if (!Array.isArray(props.data) || props.data.length === 0) return []
  // Collect all unique keys from all items
  const keys = new Set()
  props.data.forEach(item => {
    if (typeof item === 'object' && item !== null) {
      Object.keys(item).forEach(k => keys.add(k))
    }
  })
  return Array.from(keys)
})

const paginatedData = computed(() => {
  if (!Array.isArray(props.data)) return []
  const start = (currentPage.value - 1) * props.pageSize
  return props.data.slice(start, start + props.pageSize)
})

function getColumnWidth(col) {
  if (col === 'id') return 80
  if (col === 'url') return 200
  if (col.includes('time') || col.includes('date')) return 170
  return 120
}

function toggleExpand() {
  allExpanded.value = !allExpanded.value
}

function copyJson() {
  const text = JSON.stringify(props.data, null, 2)
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}
</script>

<style scoped>
.json-viewer {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}
.json-toolbar {
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}
.json-content {
  padding: 12px;
}
.json-raw {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  background: #f8f8f8;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.json-empty {
  text-align: center;
  color: #999;
  padding: 30px;
}
</style>
