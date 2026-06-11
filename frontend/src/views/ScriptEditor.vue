<template>
  <div>
    <el-card style="margin-bottom: 10px">
      <el-row :gutter="10" align="middle">
        <el-col :span="6">
          <el-select v-model="selectedTaskId" placeholder="选择任务" filterable @change="loadScripts">
            <el-option v-for="t in taskList" :key="t.id" :label="`[${t.id}] ${t.name}`" :value="t.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="scriptType" @change="loadScriptCode">
            <el-option label="完整脚本" value="full" />
            <el-option label="采集脚本" value="crawl" />
            <el-option label="解析脚本" value="parse" />
          </el-select>
        </el-col>
        <el-col :span="14" style="text-align: right">
          <el-space>
            <el-button @click="handleValidate">语法校验</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">保存 (Ctrl+S)</el-button>
            <el-button @click="handleRegenerate">重新生成</el-button>
            <el-tag v-if="version" type="info">版本: v{{ version }}</el-tag>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <!-- Monaco Editor -->
    <el-card body-style="padding: 0">
      <div ref="editorContainer" style="height: calc(100vh - 260px); border: 1px solid #ddd"></div>
    </el-card>

    <!-- Validation result -->
    <el-alert
      v-if="validationMsg"
      :title="validationMsg"
      :type="validationOk ? 'success' : 'error'"
      show-icon
      closable
      style="margin-top: 10px"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getTasks, getScripts, getScript, updateScript, regenerateScript, validateScript } from '../api'
import { ElMessage } from 'element-plus'
import * as monaco from 'monaco-editor'

const route = useRoute()
const editorContainer = ref(null)
let editor = null

const taskList = ref([])
const selectedTaskId = ref(null)
const scriptType = ref('full')
const saving = ref(false)
const version = ref(null)
const validationMsg = ref('')
const validationOk = ref(false)

const initEditor = () => {
  editor = monaco.editor.create(editorContainer.value, {
    value: '# Loading...',
    language: 'python',
    theme: 'vs-dark',
    fontSize: 14,
    minimap: { enabled: true },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 4,
    wordWrap: 'on',
    lineNumbers: 'on',
    renderLineHighlight: 'all',
  })

  // Ctrl+S save shortcut
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    handleSave()
  })
}

const loadTasks = async () => {
  try {
    const res = await getTasks({ page_size: 999 })
    taskList.value = res.data.items
  } catch (e) {}
}

const loadScripts = async () => {
  if (!selectedTaskId.value) return
  await loadScriptCode()
}

const loadScriptCode = async () => {
  if (!selectedTaskId.value) return
  try {
    const res = await getScript(selectedTaskId.value, scriptType.value)
    const data = res.data
    version.value = data.version
    if (editor) {
      editor.setValue(data.code)
    }
  } catch (e) {
    if (editor) editor.setValue('# Script not found')
  }
}

const handleSave = async () => {
  if (!selectedTaskId.value || !editor) return
  saving.value = true
  try {
    const code = editor.getValue()
    const res = await updateScript(selectedTaskId.value, scriptType.value, code)
    version.value = res.data.version
    ElMessage.success('脚本已保存')
  } catch (e) {} finally { saving.value = false }
}

const handleValidate = async () => {
  if (!editor) return
  try {
    const res = await validateScript(editor.getValue())
    validationOk.value = res.data.valid
    validationMsg.value = res.data.message
  } catch (e) {
    validationOk.value = false
    validationMsg.value = 'Validation failed'
  }
}

const handleRegenerate = async () => {
  if (!selectedTaskId.value) return
  try {
    await regenerateScript(selectedTaskId.value, scriptType.value)
    ElMessage.success('脚本已重新生成')
    await loadScriptCode()
  } catch (e) {}
}

onMounted(async () => {
  await loadTasks()
  // Check route params for pre-selection
  if (route.params.taskId) {
    selectedTaskId.value = parseInt(route.params.taskId)
  } else if (taskList.value.length > 0) {
    // 默认选择最近一个任务
    selectedTaskId.value = taskList.value[0].id
  }
  if (route.params.type) {
    scriptType.value = route.params.type
  }
  await nextTick()
  initEditor()
  if (selectedTaskId.value) {
    await loadScriptCode()
  }
})

onBeforeUnmount(() => {
  if (editor) editor.dispose()
})
</script>
