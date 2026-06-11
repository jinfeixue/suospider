<template>
  <div class="smart-wizard">
    <el-steps :active="currentStep" finish-status="success">
      <el-step title="输入URL" />
      <el-step title="AI分析" />
      <el-step title="字段映射" />
      <el-step title="完成" />
    </el-steps>

    <!-- 步骤1：输入URL -->
    <div v-if="currentStep === 0" class="step-content">
      <el-card>
        <template #header>
          <span>智能采集向导</span>
        </template>
        <el-form :model="form" label-width="120px">
          <el-form-item label="列表页URL" required>
            <el-input v-model="form.url" placeholder="请输入列表页URL，如 https://news.sina.com.cn/" />
          </el-form-item>
          <el-form-item label="任务名称">
            <el-input v-model="form.task_name" placeholder="请输入任务名称" />
          </el-form-item>
          <el-form-item label="大模型" required>
            <el-select v-model="form.llm_config_id" placeholder="请选择大模型" style="width: 100%">
              <el-option
                v-for="llm in llmConfigs"
                :key="llm.id"
                :label="`${llm.name} (${llm.provider} - ${llm.model})`"
                :value="llm.id"
              />
            </el-select>
            <div v-if="llmConfigs.length === 0" style="margin-top: 5px">
              <el-alert type="warning" :closable="false" show-icon>
                <template #title>
                  智能采集依赖大模型，请先到
                  <el-link type="warning" @click="$router.push('/llm-config')" style="vertical-align: baseline">
                    系统配置 > 大模型配置
                  </el-link>
                  中添加配置
                </template>
              </el-alert>
            </div>
          </el-form-item>
          <el-form-item label="数据源" required>
            <el-select v-model="form.datasource_id" placeholder="请选择数据源" style="width: 100%" @change="onDatasourceChange">
              <el-option
                v-for="ds in datasourceList"
                :key="ds.id"
                :label="`${ds.name} (${ds.host}:${ds.port})`"
                :value="ds.id"
              />
            </el-select>
            <div v-if="datasourceList.length === 0" style="margin-top: 5px">
              <el-alert type="warning" :closable="false" show-icon>
                <template #title>
                  采集数据需要存储到数据库，请先到
                  <el-link type="warning" @click="$router.push('/datasource')" style="vertical-align: baseline">
                    系统配置 > 数据源配置
                  </el-link>
                  中添加配置
                </template>
              </el-alert>
            </div>
          </el-form-item>
          <el-form-item label="最大采集页数">
            <el-input-number v-model="form.max_pages" :min="1" :max="1000" />
          </el-form-item>
          <el-form-item label="请求间隔">
            <el-input-number v-model="form.request_interval" :min="1" :max="60" />
            <span style="margin-left: 10px">秒</span>
          </el-form-item>
        </el-form>
      </el-card>
      <div class="step-buttons">
        <el-button
          type="primary"
          size="large"
          @click="startAnalysis"
          :disabled="!canStartAnalysis"
        >
          <el-icon><MagicStick /></el-icon>
          开始AI分析
        </el-button>
      </div>
    </div>

    <!-- 步骤2：AI分析中 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-card>
        <template #header>
          <span>AI分析网页结构</span>
        </template>
        <div v-if="analyzing" class="analysis-loading">
          <el-icon class="is-loading" :size="40"><Loading /></el-icon>
          <p>AI正在分析网页结构，请稍候...</p>
          <el-steps direction="vertical" :active="analysisProgress" class="progress-steps">
            <el-step title="获取网页内容" />
            <el-step title="分析页面结构" />
            <el-step title="识别翻页方式" />
            <el-step title="识别字段XPath" />
          </el-steps>
        </div>
        <div v-else-if="analysisResult" class="analysis-result">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="页面标题">
              {{ analysisResult.title }}
            </el-descriptions-item>
            <el-descriptions-item label="页面类型">
              <el-tag :type="analysisResult.page_type?.includes('列表') || analysisResult.page_type === 'list' ? 'success' : 'info'">
                {{ analysisResult.page_type || '未知' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="详情页链接">
              <el-tag v-if="analysisResult.detail_link_xpath" type="success">已识别</el-tag>
              <el-tag v-else type="warning">未识别</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="翻页方式">
              <el-tag v-if="analysisResult.pagination">
                {{ analysisResult.pagination.type === 'next_button' ? '按钮翻页' : analysisResult.pagination.type === 'url_pattern' ? '页码递增' : analysisResult.pagination.type }}
              </el-tag>
              <el-tag v-else type="warning">未检测到</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="使用引擎">
              <el-tag>{{ analysisResult.engine }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="analysisResult.detail_url" class="pagination-info" style="margin-top: 10px">
            <p>已分析详情页：<el-link type="primary" :href="analysisResult.detail_url" target="_blank">{{ analysisResult.detail_url }}</el-link></p>
          </div>
          <div v-if="analysisResult.pagination" class="pagination-info">
            <h4>翻页配置</h4>
            <p v-if="analysisResult.pagination.type === 'next_button'">
              XPath: <code>{{ analysisResult.pagination.xpath }}</code>
            </p>
            <p v-else>
              URL规律: <code>{{ analysisResult.pagination.pattern }}</code>
            </p>
          </div>
        </div>
      </el-card>
      <div class="step-buttons">
        <el-button @click="currentStep = 0">上一步</el-button>
        <el-button type="primary" @click="goToFieldMapping" :disabled="!analysisResult">
          下一步：字段映射
        </el-button>
      </div>
    </div>

    <!-- 步骤3：字段映射 -->
    <div v-if="currentStep === 2" class="step-content field-mapping">
      <el-row :gutter="20">
        <!-- 左侧：网页渲染视图 -->
        <el-col :span="12">
          <el-card class="preview-card">
            <template #header>
              <div class="card-header">
                <span>网页预览</span>
                <el-tag size="small" type="info">点击元素生成XPath</el-tag>
              </div>
            </template>
            <div class="web-preview" ref="webPreviewRef">
              <div v-if="analysisResult" class="preview-container">
                <iframe
                  :srcdoc="analysisResult.html"
                  class="preview-iframe"
                  @load="initPreviewInteraction"
                ></iframe>
              </div>
              <div v-else class="preview-placeholder">
                <el-icon :size="60"><Monitor /></el-icon>
                <p>请先完成AI分析</p>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：字段配置 -->
        <el-col :span="12">
          <el-card class="config-card">
            <template #header>
              <div class="card-header">
                <span>字段配置</span>
                <el-button type="primary" size="small" @click="addField">
                  <el-icon><Plus /></el-icon> 添加字段
                </el-button>
              </div>
            </template>
            <div class="field-list">
              <div v-for="(field, index) in fieldConfig" :key="index" class="field-item">
                <el-row :gutter="8" align="middle">
                  <el-col :span="7">
                    <el-select v-model="field.name" placeholder="选择字段" filterable style="width: 100%">
                      <el-option-group label="常用字段">
                        <el-option
                          v-for="f in commonFields"
                          :key="f.name"
                          :label="f.label"
                          :value="f.name"
                        />
                      </el-option-group>
                      <el-option-group label="其他字段" v-if="otherFields.length > 0">
                        <el-option
                          v-for="f in otherFields"
                          :key="f.name"
                          :label="f.label"
                          :value="f.name"
                        />
                      </el-option-group>
                    </el-select>
                  </el-col>
                  <el-col :span="15">
                    <el-input v-model="field.xpath" placeholder="XPath表达式或点击左侧预览生成" clearable>
                      <template #prepend>
                        <el-tag :type="field.confidence >= 80 ? 'success' : field.confidence >= 60 ? 'warning' : 'danger'" size="small">
                          {{ field.confidence }}%
                        </el-tag>
                      </template>
                      <template #append>
                        <el-button @click="copyXPath(field.xpath)" :icon="CopyDocument" />
                      </template>
                    </el-input>
                  </el-col>
                  <el-col :span="2">
                    <el-button type="danger" :icon="Delete" circle @click="removeField(index)" size="small" />
                  </el-col>
                </el-row>
              </div>
            </div>
            <div class="field-actions">
              <el-button @click="reanalyze">重新分析</el-button>
              <el-button type="primary" @click="generateAndCreateTask" :loading="creating">
                <el-icon><VideoPlay /></el-icon> 开始采集
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 步骤4：完成 -->
    <div v-if="currentStep === 3" class="step-content">
      <el-result icon="success" :title="`任务创建成功`" sub-title="采集脚本已生成，可以开始运行">
        <template #extra>
          <div class="result-actions">
            <el-button type="primary" size="large" @click="goToTaskList">
              <el-icon><List /></el-icon> 查看任务列表
            </el-button>
            <el-button size="large" @click="resetWizard">
              <el-icon><Plus /></el-icon> 新建任务
            </el-button>
          </div>
        </template>
      </el-result>
    </div>

    <!-- XPath选择对话框 -->
    <el-dialog v-model="xpathDialogVisible" title="选择目标字段" width="500px">
      <el-form label-width="80px">
        <el-form-item label="XPath">
          <el-input v-model="xpathDialogXPath" type="textarea" :rows="3" readonly />
        </el-form-item>
        <el-form-item label="目标字段">
          <el-select v-model="xpathDialogFieldIndex" placeholder="选择要绑定的字段" style="width: 100%">
            <el-option
              v-for="(field, idx) in fieldConfig"
              :key="idx"
              :label="`${field.name || '(未命名)'} — ${getFieldLabel(field.name)}`"
              :value="idx"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="xpathDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmXPathAssign">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, MagicStick, Plus, Delete, VideoPlay, List, Monitor, CopyDocument } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()
const currentStep = ref(0)
const analyzing = ref(false)
const analysisProgress = ref(0)
const analysisResult = ref(null)
const datasourceList = ref([])
const columnsList = ref([])
const llmConfigs = ref([])
const fieldConfig = ref([])
const webPreviewRef = ref(null)
const creating = ref(false)
const createdTaskId = ref(null)

// XPath对话框
const xpathDialogVisible = ref(false)
const xpathDialogXPath = ref('')
const xpathDialogFieldIndex = ref(0)

const form = ref({
  url: '',
  task_name: '',
  datasource_id: null,
  llm_config_id: null,
  max_pages: 5,
  request_interval: 2
})

const commonFieldNames = ['title', 'content', 'chubanriqi', 'zuozhe', 'keyword', 'abstract', 'kanming', 'wwwimages', 'author', 'zuozhedanwei', 'nianjuanqi']

const commonFields = computed(() => {
  return columnsList.value.filter(f => commonFieldNames.includes(f.name))
})

const otherFields = computed(() => {
  return columnsList.value.filter(f => !commonFieldNames.includes(f.name))
})

const canStartAnalysis = computed(() => {
  return form.value.url && form.value.llm_config_id && form.value.datasource_id
})

const getFieldLabel = (name) => {
  const col = columnsList.value.find(c => c.name === name)
  return col ? col.label : name
}

const loadDatasources = async () => {
  try {
    const res = await api.get('/datasource/')
    datasourceList.value = res.data || []
  } catch (error) {
    console.error('加载数据源列表失败:', error)
  }
}

const loadColumns = async (datasourceId) => {
  if (!datasourceId) {
    columnsList.value = []
    return
  }
  try {
    const res = await api.get(`/datasource/${datasourceId}/columns`)
    columnsList.value = res.data || []
  } catch (error) {
    console.error('加载字段列表失败:', error)
    columnsList.value = []
  }
}

const onDatasourceChange = async (datasourceId) => {
  await loadColumns(datasourceId)
}

const loadLLMConfigs = async () => {
  try {
    const res = await api.get('/llm-config/')
    llmConfigs.value = res.data || []
    if (!form.value.llm_config_id) {
      const defaultConfig = llmConfigs.value.find(c => c.is_default)
      if (defaultConfig) {
        form.value.llm_config_id = defaultConfig.id
      } else if (llmConfigs.value.length > 0) {
        form.value.llm_config_id = llmConfigs.value[0].id
      }
    }
  } catch (error) {
    console.error('加载大模型配置失败:', error)
  }
}

const goToFieldMapping = async () => {
  currentStep.value = 2
  // 进入字段映射时加载字段列表
  if (form.value.datasource_id && columnsList.value.length === 0) {
    await loadColumns(form.value.datasource_id)
  }
}

const startAnalysis = async () => {
  if (!form.value.url) {
    ElMessage.warning('请输入URL')
    return
  }
  if (!form.value.llm_config_id) {
    ElMessage.warning('请选择大模型')
    return
  }
  if (!form.value.datasource_id) {
    ElMessage.warning('请选择数据源')
    return
  }

  currentStep.value = 1
  analyzing.value = true
  analysisProgress.value = 0

  const progressTimer = setInterval(() => {
    if (analysisProgress.value < 3) {
      analysisProgress.value++
    }
  }, 1000)

  try {
    const res = await api.post('/ai/analyze', {
      url: form.value.url,
      llm_config_id: form.value.llm_config_id
    })
    const data = res.data
    analysisResult.value = data

    // 转换为字段配置
    const fields = data.field_xpaths || []
    const nameMap = {
      '标题': 'title', '正文': 'content', '正文内容': 'content',
      '日期': 'chubanriqi', '发布日期': 'chubanriqi', '时间': 'chubanriqi',
      '作者': 'zuozhe', '关键词': 'keyword',
      '摘要': 'abstract', '简介': 'abstract',
      '来源': 'kanming', '刊名': 'kanming', '图片': 'wwwimages',
    }
    fieldConfig.value = fields.map(field => {
      let name = field.name
      if (nameMap[name]) name = nameMap[name]
      return { name, xpath: field.xpath, confidence: field.confidence || 0 }
    })

    clearInterval(progressTimer)
    analysisProgress.value = 3
    analyzing.value = false
  } catch (error) {
    clearInterval(progressTimer)
    analyzing.value = false
    ElMessage.error('分析失败: ' + (error.response?.data?.detail || error.message))
  }
}

const initPreviewInteraction = () => {
  nextTick(() => {
    const iframe = document.querySelector('.preview-iframe')
    if (iframe && iframe.contentDocument) {
      iframe.contentDocument.addEventListener('click', (e) => {
        e.preventDefault()
        e.stopPropagation()
        const element = e.target
        // 高亮选中的元素
        const iframeDoc = iframe.contentDocument
        iframeDoc.querySelectorAll('.xpath-highlight').forEach(el => el.classList.remove('xpath-highlight'))
        element.classList.add('xpath-highlight')
        // 注入高亮样式
        if (!iframeDoc.getElementById('xpath-highlight-style')) {
          const style = iframeDoc.createElement('style')
          style.id = 'xpath-highlight-style'
          style.textContent = '.xpath-highlight { outline: 3px solid #409eff !important; outline-offset: 2px; }'
          iframeDoc.head.appendChild(style)
        }
        const xpath = generateXPath(element)
        openXPathDialog(xpath)
      })
    }
  })
}

const generateXPath = (element) => {
  let xpath = ''
  if (element.id) {
    xpath = `//*[@id="${element.id}"]`
  } else if (element.className && typeof element.className === 'string') {
    const classes = element.className.split(' ').filter(c => c.trim()).slice(0, 2).join(' ')
    if (classes) {
      xpath = `//*[contains(@class, "${classes}")]`
    }
  }
  if (!xpath) {
    const parts = []
    let current = element
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let tag = current.tagName.toLowerCase()
      let index = 1
      let sibling = current.previousSibling
      while (sibling) {
        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === current.tagName) {
          index++
        }
        sibling = sibling.previousSibling
      }
      parts.unshift(`${tag}[${index}]`)
      current = current.parentNode
      if (parts.length >= 5) break
    }
    xpath = '/' + parts.join('/')
  }
  // 自动判断是否需要加 /text()
  const leafTag = element.tagName?.toLowerCase()
  const blockTags = ['div', 'section', 'article', 'main', 'nav', 'header', 'footer', 'ul', 'ol', 'table', 'form']
  if (blockTags.includes(leafTag)) {
    xpath += '//text()'
  } else {
    xpath += '/text()'
  }
  return xpath
}

const openXPathDialog = (xpath) => {
  xpathDialogXPath.value = xpath
  // 自动选择第一个没有xpath的字段
  const emptyIdx = fieldConfig.value.findIndex(f => !f.xpath)
  xpathDialogFieldIndex.value = emptyIdx >= 0 ? emptyIdx : 0
  xpathDialogVisible.value = true
}

const confirmXPathAssign = () => {
  const idx = xpathDialogFieldIndex.value
  if (idx >= 0 && idx < fieldConfig.value.length) {
    fieldConfig.value[idx].xpath = xpathDialogXPath.value
    fieldConfig.value[idx].confidence = 90
    ElMessage.success(`已绑定到: ${fieldConfig.value[idx].name || '(未命名字段)'}`)
  }
  xpathDialogVisible.value = false
}

const addField = () => {
  fieldConfig.value.push({ name: '', xpath: '', confidence: 0 })
}

const removeField = (index) => {
  fieldConfig.value.splice(index, 1)
}

const copyXPath = async (xpath) => {
  try {
    await navigator.clipboard.writeText(xpath)
    ElMessage.success('已复制XPath')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const reanalyze = () => {
  currentStep.value = 0
  analysisResult.value = null
  fieldConfig.value = []
}

const generateAndCreateTask = async () => {
  creating.value = true
  try {
    // 构建fields字典
    const fields = {}
    fieldConfig.value.forEach(f => {
      if (f.name && f.xpath) {
        fields[f.name] = f.xpath
      }
    })

    const res = await api.post('/ai/smart-create', {
      url: form.value.url,
      task_name: form.value.task_name || '智能采集任务',
      max_pages: form.value.max_pages,
      request_interval: form.value.request_interval,
      datasource_id: form.value.datasource_id,
      llm_config_id: form.value.llm_config_id,
      fields: fields
    })

    ElMessage.success('任务创建成功并已启动')
    localStorage.removeItem('smartWizard')
    router.push('/smart-tasks')
  } catch (error) {
    ElMessage.error('创建失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    creating.value = false
  }
}

const goToTaskList = () => {
  router.push('/smart-tasks')
}

const resetWizard = () => {
  currentStep.value = 0
  form.value = {
    url: '',
    task_name: '',
    datasource_id: null,
    llm_config_id: null,
    max_pages: 5,
    request_interval: 2
  }
  analysisResult.value = null
  fieldConfig.value = []
  createdTaskId.value = null
}

// 保存状态到localStorage
const saveState = () => {
  try {
    localStorage.setItem('smartWizard', JSON.stringify({
      form: form.value,
      currentStep: currentStep.value,
      analysisResult: analysisResult.value,
      fieldConfig: fieldConfig.value,
    }))
  } catch (e) {}
}

// 从localStorage恢复状态
const restoreState = () => {
  try {
    const saved = localStorage.getItem('smartWizard')
    if (saved) {
      const state = JSON.parse(saved)
      if (state.form) form.value = { ...form.value, ...state.form }
      if (state.currentStep > 0) currentStep.value = state.currentStep
      if (state.analysisResult) analysisResult.value = state.analysisResult
      if (state.fieldConfig?.length) fieldConfig.value = state.fieldConfig
      return true
    }
  } catch (e) {}
  return false
}

// 监听状态变化自动保存
watch([currentStep, analysisResult, fieldConfig], () => {
  saveState()
}, { deep: true })

onMounted(async () => {
  // 尝试恢复状态
  const restored = restoreState()

  await loadDatasources()
  await loadLLMConfigs()

  // URL参数优先
  if (route.query.url) form.value.url = route.query.url
  if (route.query.max_pages) form.value.max_pages = parseInt(route.query.max_pages)
  if (route.query.request_interval) form.value.request_interval = parseInt(route.query.request_interval)
  if (route.query.llm_config_id) form.value.llm_config_id = parseInt(route.query.llm_config_id)

  // 恢复数据源字段列表
  if (form.value.datasource_id) {
    await loadColumns(form.value.datasource_id)
  }
})
</script>

<style scoped>
.smart-wizard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}
.step-content { margin-top: 30px; }
.step-buttons { margin-top: 20px; text-align: center; }
.analysis-loading { text-align: center; padding: 40px; }
.analysis-loading p { margin-top: 20px; font-size: 16px; color: #606266; }
.progress-steps { margin-top: 30px; max-width: 300px; margin-left: auto; margin-right: auto; }
.analysis-result { padding: 20px; }
.pagination-info { margin-top: 20px; padding: 15px; background: #f5f7fa; border-radius: 4px; }
.pagination-info h4 { margin: 0 0 10px 0; color: #303166; }
.pagination-info code { background: #e6e8eb; padding: 2px 6px; border-radius: 3px; }
.field-mapping { height: calc(100vh - 250px); }
.preview-card, .config-card { height: 100%; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.web-preview { height: 600px; border: 1px solid #dcdfe6; border-radius: 4px; overflow: hidden; position: relative; }
.preview-container { position: relative; width: 100%; height: 100%; }
.preview-iframe { width: 100%; height: 100%; border: none; }
.preview-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #909399; }
.preview-placeholder p { margin-top: 10px; }
.field-list { max-height: 500px; overflow-y: auto; }
.field-item { padding: 8px 0; border-bottom: 1px solid #ebeef5; }
.field-item:last-child { border-bottom: none; }
.field-actions { margin-top: 20px; display: flex; justify-content: space-between; }
.result-actions { display: flex; gap: 20px; }
</style>
