<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>引擎管理与调试</span>
          <el-button type="primary" size="small" @click="showAddEngine">
            <el-icon><Plus /></el-icon> 新增引擎
          </el-button>
        </div>
      </template>

      <!-- 引擎选择行 -->
      <el-row :gutter="20" style="margin-bottom: 20px">
        <el-col :span="8">
          <el-select v-model="selectedEngineName" placeholder="选择引擎" style="width: 100%" @change="handleEngineChange">
            <el-option-group label="内置引擎">
              <el-option v-for="eng in builtinEngines" :key="eng.name" :label="eng.name" :value="eng.name">
                <span>{{ eng.name }}</span>
                <span style="color: #999; font-size: 12px; margin-left: 10px">{{ eng.description }}</span>
              </el-option>
            </el-option-group>
            <el-option-group label="自定义引擎" v-if="customEngines.length > 0">
              <el-option v-for="eng in customEngines" :key="eng.name" :label="eng.name" :value="eng.name">
                <span>{{ eng.name }}</span>
                <span style="color: #999; font-size: 12px; margin-left: 10px">{{ eng.description }}</span>
                <el-button type="danger" size="small" circle style="float: right; margin-top: 5px" @click.stop="deleteEngine(eng)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-option>
            </el-option-group>
          </el-select>
        </el-col>
        <el-col :span="16">
          <el-tag v-if="currentEngine?.is_builtin" type="info">内置引擎</el-tag>
          <el-tag v-else type="success">自定义引擎</el-tag>
          <span v-if="currentEngine?.description" style="margin-left: 10px; color: #666">{{ currentEngine.description }}</span>
        </el-col>
      </el-row>

      <!-- 引擎代码编辑器 - Monaco Editor -->
      <el-divider content-position="left">引擎代码</el-divider>
      <div style="margin-bottom: 20px">
        <div style="background: #1e1e1e; padding: 8px 12px; border: 1px solid #333; border-bottom: none; border-radius: 4px 4px 0 0; font-size: 12px; color: #ccc; display: flex; justify-content: space-between; align-items: center">
          <span>实现 fetch(url, headers, timeout, **kwargs) 方法，返回网页HTML源代码</span>
          <el-button v-if="!currentEngine?.is_builtin" type="primary" size="small" @click="saveEngine">
            <el-icon><Check /></el-icon> 保存代码
          </el-button>
        </div>
        <div ref="codeEditor" style="height: 400px; border: 1px solid #333; border-radius: 0 0 4px 4px; overflow: hidden;"></div>
      </div>

      <!-- 在线调试 -->
      <el-divider content-position="left">在线调试</el-divider>
      <el-form :model="testForm" label-width="80px">
        <el-row :gutter="10">
          <el-col :span="12">
            <el-form-item label="测试URL">
              <el-input v-model="testForm.url" placeholder="https://example.com" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="testForm.timeout" :min="1" :max="60" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item>
              <el-button type="primary" :loading="testing" @click="handleTest" style="width: 100%">
                <el-icon><VideoPlay /></el-icon> 测试采集
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>
        <!-- 请求设置（仅requests/httpx/curlcffi引擎） -->
        <template v-if="supportsRequestSettings">
          <el-row :gutter="10">
            <el-col :span="24">
              <el-form-item label="Headers">
                <el-input v-model="testForm.headersText" type="textarea" :rows="3" placeholder='JSON格式，如: {"User-Agent": "...", "Referer": "https://..."}' />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="Cookies">
                <el-input v-model="testForm.cookie" type="textarea" :rows="2" placeholder='JSON格式，如: {"session_id": "abc123", "token": "xyz"}' />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="代理">
                <el-input v-model="testForm.proxy" placeholder="http://ip:port 或 socks5://ip:port" />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
      </el-form>

      <!-- 测试结果 -->
      <div v-if="testResult">
        <el-divider content-position="left">测试结果</el-divider>
        <el-descriptions :column="4" border size="small" style="margin-bottom: 15px">
          <el-descriptions-item label="状态码">
            <el-tag :type="testResultInfo.status_code === 200 ? 'success' : 'danger'">
              {{ testResultInfo.status_code }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="内容大小">{{ formatSize(testResultInfo.content_length) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ testResultInfo.elapsed }}s</el-descriptions-item>
          <el-descriptions-item label="编码">{{ testResultInfo.encoding }}</el-descriptions-item>
        </el-descriptions>

        <!-- XPath测试 -->
        <el-row :gutter="10" style="margin-bottom: 15px">
          <el-col :span="14">
            <el-input v-model="testXPath" placeholder="输入XPath表达式，如: //title/text()" clearable />
          </el-col>
          <el-col :span="4">
            <el-button @click="handleTestXPath" :loading="xpathTesting" style="width: 100%">
              <el-icon><Search /></el-icon> 测试XPath
            </el-button>
          </el-col>
          <el-col :span="6">
            <el-button @click="clearResults" style="width: 100%">
              <el-icon><Delete /></el-icon> 清空结果
            </el-button>
          </el-col>
        </el-row>

        <div v-if="xpathResults.length > 0" style="margin-bottom: 15px">
          <el-alert type="success" :closable="false">
            <template #title>匹配到 {{ xpathResults.length }} 个结果</template>
          </el-alert>
          <div style="max-height: 200px; overflow-y: auto; margin-top: 10px; background: #f5f5f5; padding: 10px; border-radius: 4px;">
            <div v-for="(item, index) in xpathResults" :key="index" style="padding: 4px 0; border-bottom: 1px solid #eee;">
              <el-tag size="small" style="margin-right: 10px">{{ index + 1 }}</el-tag>
              <span style="word-break: break-all">{{ item }}</span>
            </div>
          </div>
        </div>

        <!-- 页面预览和源码 -->
        <el-tabs v-model="previewTab" @tab-change="handlePreviewTabChange">
          <el-tab-pane label="页面预览" name="preview">
            <div style="border: 1px solid #dcdfe6; border-radius: 4px; height: 500px; overflow: auto; background: #fff;">
              <iframe ref="previewIframe" :srcdoc="testResult" style="width: 100%; height: 100%; border: none;"></iframe>
            </div>
          </el-tab-pane>
          <el-tab-pane label="网页源代码" name="html">
            <div style="position: relative;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span style="font-size: 12px; color: #666;">
                  <span v-if="testHtmlLoading" style="color: #409eff;">正在加载完整源码...</span>
                  <span v-else>源码长度: {{ testHtml ? testHtml.length : 0 }} 字符</span>
                </span>
                <el-button type="primary" size="small" @click="copyHtml" :disabled="testHtmlLoading">
                  <el-icon><CopyDocument /></el-icon> 复制全部
                </el-button>
              </div>
              <textarea 
                :value="testHtmlLoading ? '正在加载...' : (testHtml || '暂无内容')" 
                readonly
                style="width: 100%; height: 600px; background: #1e1e1e; color: #d4d4d4; padding: 15px; border: 1px solid #333; border-radius: 4px; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; line-height: 1.5; resize: vertical; outline: none; white-space: pre; overflow: auto;"
              ></textarea>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>

    <!-- 添加引擎对话框 -->
    <el-dialog v-model="addDialogVisible" title="新增自定义引擎" width="500">
      <el-form :model="newEngine" label-width="100px">
        <el-form-item label="引擎名称" required>
          <el-input v-model="newEngine.name" placeholder="my_engine" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newEngine.description" placeholder="引擎描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addEngine">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Check, VideoPlay, Search, CopyDocument } from '@element-plus/icons-vue'
import * as monaco from 'monaco-editor'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  maxContentLength: Infinity,
  maxBodyLength: Infinity,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const engines = ref([])
const selectedEngineName = ref('requests')
const loadingEngines = ref(false)
const testing = ref(false)
const xpathTesting = ref(false)
const addDialogVisible = ref(false)
const previewTab = ref('preview')
const testXPath = ref('')
const xpathResults = ref([])
const previewIframe = ref(null)

const codeEditor = ref(null)
let editor = null

const testForm = reactive({
  url: '',
  timeout: 30,
  headersText: '{}',
  cookie: '',
  proxy: '',
})

const testResult = ref(null)
const testHtml = ref('')
const testHtmlFile = ref('')
const testHtmlLoading = ref(false)
const testResultInfo = reactive({
  status_code: null,
  content_length: null,
  elapsed: null,
  encoding: null,
})

const newEngine = reactive({
  name: '',
  description: '',
})

const builtinEngines = computed(() => engines.value.filter(e => e.is_builtin))
const customEngines = computed(() => engines.value.filter(e => !e.is_builtin))
const currentEngine = computed(() => engines.value.find(e => e.name === selectedEngineName.value))

// 判断当前引擎是否支持请求设置（headers/cookies/proxy）
const supportsRequestSettings = computed(() => {
  const engineName = selectedEngineName.value?.toLowerCase() || ''
  return ['requests', 'httpx', 'curlcffi'].includes(engineName)
})

const loadEngines = async () => {
  loadingEngines.value = true
  try {
    const res = await api.get('/engines/list')
    engines.value = res.data.data || []
  } catch (e) {
    console.error('加载引擎失败:', e)
  } finally {
    loadingEngines.value = false
  }
}

const handleEngineChange = async (name) => {
  selectedEngineName.value = name
  await nextTick()
  updateEditorContent()
}

const initEditor = () => {
  if (!codeEditor.value) return
  
  // 创建代码编辑器
  editor = monaco.editor.create(codeEditor.value, {
    value: '',
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
    folding: true,
    bracketPairColorization: { enabled: true },
    readOnly: false,
  })

  // 监听内容变化
  editor.onDidChangeModelContent(() => {
    if (currentEngine.value && !currentEngine.value.is_builtin) {
      currentEngine.value.code = editor.getValue()
    }
  })

  // Ctrl+S 保存快捷键
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    saveEngine()
  })
}

const updateEditorContent = () => {
  if (editor && currentEngine.value) {
    const code = currentEngine.value.code || ''
    editor.setValue(code)
    editor.updateOptions({ readOnly: currentEngine.value.is_builtin })
  }
}

const showAddEngine = () => {
  newEngine.name = ''
  newEngine.description = ''
  addDialogVisible.value = true
}

const addEngine = async () => {
  if (!newEngine.name) {
    ElMessage.warning('请输入引擎名称')
    return
  }
  
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(newEngine.name)) {
    ElMessage.warning('引擎名称只能包含字母、数字和下划线')
    return
  }
  
  try {
    await api.post('/engines/create', {
      name: newEngine.name,
      description: newEngine.description,
      code: '',
    })
    
    ElMessage.success('引擎创建成功')
    addDialogVisible.value = false
    await loadEngines()
    selectedEngineName.value = newEngine.name
    await nextTick()
    updateEditorContent()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

const saveEngine = async () => {
  if (!currentEngine.value || currentEngine.value.is_builtin) return
  
  try {
    await api.put(`/engines/${currentEngine.value.name}`, {
      description: currentEngine.value.description,
      code: editor.getValue(),
    })
    ElMessage.success('保存成功')
    await loadEngines()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

const deleteEngine = async (engine) => {
  try {
    await ElMessageBox.confirm(`确定删除引擎 "${engine.name}" ?`, '确认')
    await api.delete(`/engines/${engine.name}`)
    ElMessage.success('删除成功')
    
    if (selectedEngineName.value === engine.name) {
      selectedEngineName.value = 'requests'
    }
    await loadEngines()
    await nextTick()
    updateEditorContent()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

const handleTest = async () => {
  if (!testForm.url) {
    ElMessage.warning('请输入测试URL')
    return
  }
  
  testing.value = true
  testResult.value = null
  testHtml.value = ''
  xpathResults.value = []
  testResultInfo.status_code = null
  testResultInfo.content_length = null
  testResultInfo.elapsed = null
  testResultInfo.encoding = null
  
  try {
    let headers = {}
    try {
      headers = JSON.parse(testForm.headersText)
    } catch (e) {
      headers = {}
    }
    
    const res = await api.post('/engines/test', {
      engine: selectedEngineName.value,
      url: testForm.url,
      timeout: testForm.timeout,
      headers: headers,
      cookie: testForm.cookie,
      proxy: testForm.proxy,
    })
    
    if (res.data.code === 0) {
      const data = res.data.data
      testResultInfo.status_code = data.status_code
      testResultInfo.content_length = data.content_length
      testResultInfo.elapsed = data.elapsed
      testResultInfo.encoding = data.encoding
      testResult.value = data.preview || ''
      testHtmlFile.value = data.html_temp_id || ''
      testHtml.value = ''  // 清空，切换到源码tab时再加载
      ElMessage.success('测试成功')
    } else {
      ElMessage.error(res.data.message || '测试失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '测试失败')
  } finally {
    testing.value = false
  }
}

const handleTestXPath = () => {
  if (!testXPath.value) {
    ElMessage.warning('请输入XPath表达式')
    return
  }
  if (!testHtml.value) {
    ElMessage.warning('请先测试采集')
    return
  }
  
  xpathTesting.value = true
  xpathResults.value = []
  
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(testHtml.value, 'text/html')
    
    const result = document.evaluate(
      testXPath.value,
      doc,
      null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
      null
    )
    
    const results = []
    for (let i = 0; i < result.snapshotLength; i++) {
      const node = result.snapshotItem(i)
      if (node) {
        results.push(node.textContent?.trim() || node.getAttribute('href') || node.outerHTML || '')
      }
    }
    
    xpathResults.value = results
    if (results.length === 0) {
      ElMessage.warning('未匹配到结果')
    } else {
      ElMessage.success(`匹配到 ${results.length} 个结果`)
    }
  } catch (e) {
    ElMessage.error('XPath表达式错误: ' + e.message)
  } finally {
    xpathTesting.value = false
  }
}

const clearResults = () => {
  testResult.value = null
  testHtml.value = ''
  xpathResults.value = []
  testResultInfo.status_code = null
  testResultInfo.content_length = null
  testResultInfo.elapsed = null
  testResultInfo.encoding = null
  if (htmlEditor) {
    htmlEditor.setValue('')
  }
}

const handlePreviewTabChange = async (tab) => {
  if (tab === 'html' && testHtmlFile.value && !testHtml.value) {
    // 切换到源码tab时，从静态文件加载完整HTML
    testHtmlLoading.value = true
    try {
      const url = `/temp/test_${testHtmlFile.value}.html`
      const res = await fetch(url)
      if (res.ok) {
        testHtml.value = await res.text()
      } else {
        testHtml.value = '加载失败: HTTP ' + res.status
      }
    } catch (e) {
      testHtml.value = '加载失败: ' + (e.message || '网络错误')
    } finally {
      testHtmlLoading.value = false
    }
  }
}

const copyHtml = async () => {
  try {
    await navigator.clipboard.writeText(testHtml.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    const textarea = document.createElement('textarea')
    textarea.value = testHtml.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制到剪贴板')
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(async () => {
  await loadEngines()
  await nextTick()
  initEditor()
  updateEditorContent()
})

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
  }
})
</script>
