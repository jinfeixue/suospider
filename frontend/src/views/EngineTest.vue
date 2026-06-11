<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>引擎在线调试</span>
          <el-tag type="info">独立调试工具</el-tag>
        </div>
      </template>

      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="采集引擎">
              <el-select v-model="form.engine" style="width: 100%">
                <el-option label="requests (静态页面)" value="requests" />
                <el-option label="httpx (HTTP/2)" value="httpx" />
                <el-option label="Playwright (动态JS)" value="playwright" />
                <el-option label="DrissionPage" value="drission" />
                <el-option label="curlcffi (反指纹)" value="curlcffi" />
                <el-option label="urllib3" value="urllib3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="form.timeout" :min="1" :max="60" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="重试次数">
              <el-input-number v-model="form.max_retries" :min="0" :max="5" style="width: 100%" />
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

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="目标URL">
              <el-input v-model="form.url" placeholder="https://example.com" clearable>
                <template #prepend>URL</template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="自定义Headers">
              <el-input v-model="headersText" type="textarea" :rows="3" placeholder='{"User-Agent": "Mozilla/5.0 ..."}' />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Cookie">
              <el-input v-model="form.cookie" placeholder="key=value; ..." />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="代理IP">
              <el-input v-model="form.proxy" placeholder="http://ip:port" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- XPath测试 -->
        <el-divider content-position="left">XPath测试</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="XPath表达式">
              <el-input v-model="form.xpath" placeholder="//h1/text() 或 //a/@href" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item>
              <el-button @click="testXPath" :disabled="!resultContent" :loading="xpathTesting">
                <el-icon><Search /></el-icon> 测试XPath
              </el-button>
              <el-button @click="clearResults">
                <el-icon><Delete /></el-icon> 清空结果
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row v-if="xpathResults.length > 0">
          <el-col :span="24">
            <el-alert type="success" :closable="false">
              <template #title>
                XPath匹配到 {{ xpathResults.length }} 个结果
              </template>
            </el-alert>
            <div style="max-height: 200px; overflow-y: auto; margin-top: 10px; background: #f5f5f5; padding: 10px; border-radius: 4px;">
              <div v-for="(item, index) in xpathResults" :key="index" style="padding: 4px 0; border-bottom: 1px solid #eee;">
                <el-tag size="small" style="margin-right: 10px;">{{ index + 1 }}</el-tag>
                <span style="word-break: break-all;">{{ item }}</span>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 结果展示 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>采集结果</span>
          <el-space>
            <el-tag v-if="resultInfo.status_code" :type="resultInfo.status_code === 200 ? 'success' : 'danger'">
              状态码: {{ resultInfo.status_code }}
            </el-tag>
            <el-tag v-if="resultInfo.content_length" type="info">
              内容长度: {{ formatSize(resultInfo.content_length) }}
            </el-tag>
            <el-tag v-if="resultInfo.elapsed" type="warning">
              耗时: {{ resultInfo.elapsed }}s
            </el-tag>
            <el-tag v-if="resultInfo.encoding" type="info">
              编码: {{ resultInfo.encoding }}
            </el-tag>
          </el-space>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="页面预览" name="preview">
          <div v-if="resultContent" style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; max-height: 600px; overflow: auto; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all;">{{ resultContent }}</div>
          <el-empty v-else description="输入URL并点击测试采集" />
        </el-tab-pane>
        <el-tab-pane label="HTML源码" name="html">
          <div v-if="resultHtml" style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; max-height: 600px; overflow: auto; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all;">{{ resultHtml }}</div>
          <el-empty v-else description="输入URL并点击测试采集" />
        </el-tab-pane>
        <el-tab-pane label="响应头" name="headers">
          <div v-if="resultHeaders" style="background: #f5f5f5; padding: 15px; border-radius: 4px; max-height: 400px; overflow: auto;">
            <div v-for="(value, key) in resultHeaders" :key="key" style="padding: 4px 0; border-bottom: 1px solid #eee;">
              <strong>{{ key }}:</strong> {{ value }}
            </div>
          </div>
          <el-empty v-else description="输入URL并点击测试采集" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { testEngine } from '../api'
import { ElMessage } from 'element-plus'
import { VideoPlay, Search, Delete } from '@element-plus/icons-vue'

const form = reactive({
  engine: 'requests',
  url: '',
  timeout: 30,
  max_retries: 3,
  cookie: '',
  proxy: '',
  xpath: '',
})
const headersText = ref('{}')

const testing = ref(false)
const xpathTesting = ref(false)
const activeTab = ref('preview')

const resultContent = ref('')
const resultHtml = ref('')
const resultHeaders = ref(null)
const resultInfo = reactive({
  status_code: null,
  content_length: null,
  elapsed: null,
  encoding: null,
})
const xpathResults = ref([])

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const handleTest = async () => {
  if (!form.url) {
    ElMessage.warning('请输入URL')
    return
  }

  // Validate URL
  if (!form.url.startsWith('http://') && !form.url.startsWith('https://')) {
    ElMessage.warning('URL必须以http://或https://开头')
    return
  }

  testing.value = true
  resultContent.value = ''
  resultHtml.value = ''
  resultHeaders.value = null
  xpathResults.value = []
  resultInfo.status_code = null
  resultInfo.content_length = null
  resultInfo.elapsed = null
  resultInfo.encoding = null

  try {
    let headers = {}
    try {
      headers = JSON.parse(headersText.value)
    } catch (e) {
      ElMessage.error('Headers JSON格式错误')
      testing.value = false
      return
    }

    const res = await testEngine({
      engine: form.engine,
      url: form.url,
      timeout: form.timeout,
      max_retries: form.max_retries,
      headers: headers,
      cookie: form.cookie,
      proxy: form.proxy,
    })

    resultInfo.status_code = res.data.status_code
    resultInfo.content_length = res.data.content_length
    resultInfo.elapsed = res.data.elapsed
    resultInfo.encoding = res.data.encoding
    resultContent.value = res.data.preview || ''
    resultHtml.value = res.data.html || res.data.preview || ''
    resultHeaders.value = res.data.headers || {}

    ElMessage.success('采集成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '采集失败')
  } finally {
    testing.value = false
  }
}

const testXPath = () => {
  if (!form.xpath) {
    ElMessage.warning('请输入XPath表达式')
    return
  }
  if (!resultHtml.value) {
    ElMessage.warning('请先测试采集获取页面内容')
    return
  }

  xpathTesting.value = true
  xpathResults.value = []

  try {
    // Use browser's DOMParser for XPath evaluation
    const parser = new DOMParser()
    const doc = parser.parseFromString(resultHtml.value, 'text/html')
    
    const xpathResult = document.evaluate(
      form.xpath,
      doc,
      null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
      null
    )

    const results = []
    for (let i = 0; i < xpathResult.snapshotLength; i++) {
      const node = xpathResult.snapshotItem(i)
      if (node) {
        results.push(node.textContent?.trim() || node.getAttribute('href') || node.outerHTML || '')
      }
    }

    xpathResults.value = results
    if (results.length === 0) {
      ElMessage.warning('XPath未匹配到任何结果')
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
  resultContent.value = ''
  resultHtml.value = ''
  resultHeaders.value = null
  xpathResults.value = []
  resultInfo.status_code = null
  resultInfo.content_length = null
  resultInfo.elapsed = null
  resultInfo.encoding = null
}
</script>
