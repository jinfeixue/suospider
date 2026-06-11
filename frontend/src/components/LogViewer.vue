<template>
  <div class="log-viewer" ref="containerRef">
    <div class="log-toolbar">
      <el-space>
        <el-switch v-model="autoScroll" active-text="自动滚动" inactive-text="" />
        <el-switch v-model="showTimestamp" active-text="时间戳" inactive-text="" />
        <el-button size="small" @click="clearLogs">清空</el-button>
        <el-tag size="small">{{ logs.length }} 条</el-tag>
      </el-space>
    </div>
    <div class="log-content" ref="logRef">
      <div
        v-for="(log, index) in logs"
        :key="index"
        :class="['log-line', `log-${log.level?.toLowerCase() || 'info'}`]"
      >
        <span v-if="showTimestamp" class="log-timestamp">{{ log.timestamp }}</span>
        <span class="log-level">[{{ log.level || 'INFO' }}]</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      <div v-if="logs.length === 0" class="log-empty">暂无日志</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  maxHeight: { type: String, default: '500px' },
})

const containerRef = ref(null)
const logRef = ref(null)
const autoScroll = ref(true)
const showTimestamp = ref(true)

function clearLogs() {
  // Emit to parent to clear
}

function scrollToBottom() {
  if (autoScroll.value && logRef.value) {
    nextTick(() => {
      logRef.value.scrollTop = logRef.value.scrollHeight
    })
  }
}

watch(() => props.logs.length, scrollToBottom)
</script>

<style scoped>
.log-viewer {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}
.log-toolbar {
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}
.log-content {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 10px;
  overflow-y: auto;
  max-height: v-bind(maxHeight);
}
.log-line {
  padding: 1px 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-timestamp {
  color: #6a9955;
  margin-right: 8px;
}
.log-level {
  margin-right: 8px;
  font-weight: bold;
}
.log-info .log-level { color: #4fc1ff; }
.log-debug .log-level { color: #b5cea8; }
.log-warning .log-level { color: #cca700; }
.log-warn .log-level { color: #cca700; }
.log-error .log-level { color: #f44747; }
.log-error .log-message { color: #f44747; }
.log-empty {
  color: #6a9955;
  text-align: center;
  padding: 20px;
}
</style>
