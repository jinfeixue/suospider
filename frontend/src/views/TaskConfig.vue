<template>
  <div v-loading="loading">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>专业采集配置: {{ task?.name || '加载中...' }}</span>
          <el-space>
            <el-button @click="$router.back()">返回</el-button>
            <el-button type="warning" :loading="resetting" @click="handleResetParse">重新解析</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
          </el-space>
        </div>
      </template>

      <el-form :model="config" label-width="100px">
        <!-- 存储配置 -->
        <el-divider content-position="left">存储配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="10">
            <el-form-item label="数据源" required>
              <el-select v-model="config.datasource_id" placeholder="请选择数据源" style="width: 100%" @change="onDatasourceChange">
                <el-option
                  v-for="ds in datasourceList"
                  :key="ds.id"
                  :label="`${ds.name} (${ds.host}:${ds.port})`"
                  :value="ds.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="表名">
              <el-input v-model="config.db_table" placeholder="crawler_feachdata" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label-width="0">
              <el-button type="success" size="small" @click="$router.push('/datasource')">管理数据源</el-button>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 基础配置 -->
        <el-divider content-position="left">基础配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="入口URL" required>
              <el-input v-model="config.url" placeholder="https://example.com" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="任务分组">
              <el-select v-model="config.group_name" filterable allow-create style="width: 100%">
                <el-option v-for="g in groups" :key="g" :label="g" :value="g" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="采集引擎">
              <el-select v-model="config.engine" style="width: 100%">
                <el-option label="requests (静态)" value="requests" />
                <el-option label="httpx (HTTP/2)" value="httpx" />
                <el-option label="playwright (动态)" value="playwright" />
                <el-option label="curlcffi (高防)" value="curlcffi" />
                <el-option label="drission (混合)" value="drission" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="解析引擎">
              <el-select v-model="config.parse_engine" style="width: 100%" placeholder="默认与采集引擎相同">
                <el-option label="与采集引擎相同" value="" />
                <el-option label="requests (静态)" value="requests" />
                <el-option label="httpx (HTTP/2)" value="httpx" />
                <el-option label="playwright (动态)" value="playwright" />
                <el-option label="curlcffi (高防)" value="curlcffi" />
                <el-option label="drission (混合)" value="drission" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="最大页数">
              <el-input-number v-model="config.max_pages" :min="1" :max="9999" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="请求间隔">
              <el-input-number v-model="config.interval" :min="0" :max="60" :step="0.5" />
              <span style="margin-left: 5px">秒</span>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 请求设置（仅requests/httpx/curlcffi引擎） -->
        <el-collapse v-if="['requests', 'httpx', 'curlcffi'].includes(config.engine)">
          <el-collapse-item title="请求设置（Headers / Cookies / 代理）" name="requestSettings">
            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item label="User-Agent">
                  <el-input v-model="config.user_agent" placeholder="留空则使用默认UA" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item label="自定义Headers">
                  <el-input v-model="config.custom_headers" type="textarea" :rows="3" placeholder='JSON格式，如: {"Referer": "https://example.com", "Accept-Language": "zh-CN"}' />
                  <div class="form-tip">JSON格式，每行一个或直接粘贴JSON对象</div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item label="Cookies">
                  <el-input v-model="config.cookies" type="textarea" :rows="2" placeholder='JSON格式，如: {"session_id": "abc123", "token": "xyz"}' />
                  <div class="form-tip">JSON格式的Cookie键值对</div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="代理地址">
                  <el-input v-model="config.proxy" placeholder="http://127.0.0.1:7890 或 socks5://127.0.0.1:1080" />
                  <div class="form-tip">支持 http/https/socks5 代理</div>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="请求超时">
                  <el-input-number v-model="config.timeout" :min="5" :max="300" />
                  <span style="margin-left: 5px">秒</span>
                </el-form-item>
              </el-col>
            </el-row>
          </el-collapse-item>
        </el-collapse>

        <!-- 采集规则 -->
        <el-divider content-position="left">采集规则</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="详情页链接" required>
              <el-input v-model="config.detail_link_xpath" placeholder="//div[@class='article']//h2/a/@href" />
              <div class="form-tip">从列表页提取详情页链接的XPath</div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="翻页方式">
              <el-radio-group v-model="config.pagination_type">
                <el-radio value="xpath">XPath翻页</el-radio>
                <el-radio value="page_num">页码递增</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- XPath翻页配置 -->
        <el-row :gutter="20" v-if="config.pagination_type === 'xpath'">
          <el-col :span="12">
            <el-form-item label="下一页XPath">
              <el-input v-model="config.next_xpath" placeholder="//a[contains(text(),'下一页')]/@href 或 //a[@class='next']/@href" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 页码递增配置 -->
        <el-row :gutter="20" v-if="config.pagination_type === 'page_num'">
          <el-col :span="12">
            <el-form-item label="URL模板" required>
              <el-input v-model="config.page_url_template" placeholder="https://example.com/page/{page}" />
              <div class="form-tip">用 {page} 表示页码位置</div>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="起始页码">
              <el-input-number v-model="config.page_start" :min="0" :max="1000" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="页码递增">
              <el-input-number v-model="config.page_step" :min="1" :max="100" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 字段配置 -->
        <el-divider content-position="left">字段配置</el-divider>
        <div class="field-list">
          <el-row v-for="(field, index) in fieldList" :key="index" :gutter="10" style="margin-bottom: 10px" align="middle">
            <el-col :span="5">
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
            <el-col :span="3">
              <el-select v-model="field.type" style="width: 100%">
                <el-option label="XPath提取" value="xpath" />
                <el-option label="常量值" value="constant" />
              </el-select>
            </el-col>
            <el-col :span="14">
              <el-input
                v-if="field.type === 'xpath'"
                v-model="field.xpath"
                placeholder="XPath表达式，如 //h1/text()"
              />
              <el-input
                v-else
                v-model="field.constant"
                placeholder="输入常量值"
              />
            </el-col>
            <el-col :span="2">
              <el-button type="danger" :icon="Delete" circle @click="removeField(index)" />
            </el-col>
          </el-row>
        </div>
        <el-button type="primary" size="small" @click="addField">
          <el-icon><Plus /></el-icon> 添加字段
        </el-button>
      </el-form>
    </el-card>

    <!-- 引擎测试 -->
    <el-card style="margin-top: 20px">
      <template #header><span>引擎测试</span></template>
      <el-form :model="{ testUrl, testEngineName }" label-width="80px">
        <el-row :gutter="10">
          <el-col :span="14">
            <el-form-item label="测试URL">
              <el-input v-model="testUrl" placeholder="https://example.com" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="5">
            <el-form-item label="选择引擎">
              <el-select v-model="testEngineName" style="width: 100%">
                <el-option label="requests" value="requests" />
                <el-option label="httpx" value="httpx" />
                <el-option label="playwright" value="playwright" />
                <el-option label="curlcffi" value="curlcffi" />
                <el-option label="drission" value="drission" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="5">
            <el-form-item>
              <el-button type="primary" :loading="testing" @click="handleTest" style="width: 100%">
                <el-icon><VideoPlay /></el-icon> 测试采集
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 测试结果 -->
      <div v-if="testResult">
        <el-divider content-position="left">测试结果</el-divider>
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="状态码">
            <el-tag :type="testResult.status_code === 200 ? 'success' : 'danger'">
              {{ testResult.status_code }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="内容大小">{{ testResult.content_length }} 字符</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ testResult.elapsed }}s</el-descriptions-item>
          <el-descriptions-item label="编码">{{ testResult.encoding }}</el-descriptions-item>
        </el-descriptions>

        <!-- 页面预览和源码 -->
        <el-tabs v-model="previewTab">
          <el-tab-pane label="页面预览" name="preview">
            <div style="border: 1px solid #dcdfe6; border-radius: 4px; height: 400px; overflow: auto;">
              <iframe :srcdoc="testResult.preview" style="width: 100%; height: 100%; border: none;"></iframe>
            </div>
          </el-tab-pane>
          <el-tab-pane label="网页源代码" name="html">
            <div style="margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center">
              <span style="font-size: 12px; color: #666">
                <span v-if="testHtmlLoading">正在加载完整源码...</span>
                <span v-else>源码长度: {{ testHtml ? testHtml.length : 0 }} 字符</span>
              </span>
              <el-button type="primary" size="small" @click="copyHtml" :disabled="testHtmlLoading">
                <el-icon><CopyDocument /></el-icon> 复制全部
              </el-button>
            </div>
            <textarea
              :value="testHtmlLoading ? '正在加载...' : (testHtml || '点击页面预览加载源码')"
              readonly
              style="width: 100%; height: 400px; background: #1e1e1e; color: #d4d4d4; padding: 15px; border: 1px solid #333; border-radius: 4px; font-family: Consolas, monospace; font-size: 13px; resize: vertical;"
            ></textarea>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, VideoPlay, CopyDocument } from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id
const loading = ref(false)

const task = ref({})
const config = ref({
  url: '',
  engine: 'requests',
  parse_engine: '',
  max_pages: 1,
  interval: 1,
  datasource_id: null,
  db_table: 'crawler_feachdata',
  detail_link_xpath: '',
  pagination_type: 'xpath',
  next_xpath: '',
  page_url_template: '',
  page_start: 1,
  page_step: 1,
  group_name: '默认分组',
  fields: {},
  // 请求设置
  user_agent: '',
  custom_headers: '',
  cookies: '',
  proxy: '',
  timeout: 30,
})

const fieldList = ref([])
const datasourceList = ref([])
const columnsList = ref([]) // 数据源表的字段列表
const groups = ref([])

// 常用字段列表（从数据库表字段中筛选）
const commonFieldNames = ['title', 'content', 'chubanriqi', 'zuozhe', 'keyword', 'abstract', 'kanming', 'wwwimages', 'author', 'zuozhedanwei', 'nianjuanqi']

const commonFields = computed(() => {
  return columnsList.value.filter(f => commonFieldNames.includes(f.name))
})

const otherFields = computed(() => {
  return columnsList.value.filter(f => !commonFieldNames.includes(f.name))
})

const loadTask = async () => {
  loading.value = true
  try {
    const res = await api.get(`/tasks/${taskId}`)
    task.value = res.data
    const cfg = task.value.config_json || {}
    config.value = {
      url: cfg.url || '',
      engine: cfg.engine || 'requests',
      parse_engine: cfg.parse_engine || '',
      max_pages: cfg.max_pages || 1,
      interval: cfg.interval || 1,
      datasource_id: cfg.datasource_id || task.value.datasource_id,
      db_table: cfg.db_table || 'crawler_feachdata',
      detail_link_xpath: cfg.detail_link_xpath || '',
      pagination_type: cfg.pagination_type || 'xpath',
      next_xpath: cfg.next_xpath || '',
      page_url_template: cfg.page_url_template || '',
      page_start: cfg.page_start || 1,
      page_step: cfg.page_step || 1,
      group_name: task.value.group_name || '默认分组',
      fields: cfg.fields || {},
      field_order: cfg.field_order || [],  // 保存字段顺序
      // 请求设置
      user_agent: cfg.user_agent || '',
      custom_headers: cfg.custom_headers || '',
      cookies: cfg.cookies || '',
      proxy: cfg.proxy || '',
      timeout: cfg.timeout || 30,
    }

    // 转换字段为列表（支持新的格式：包含 type 和 value）
    const fieldsObj = config.value.fields
    const fieldOrder = (config.value.field_order && config.value.field_order.length > 0)
      ? config.value.field_order
      : Object.keys(fieldsObj)

    fieldList.value = fieldOrder
      .filter(name => fieldsObj[name])  // 只保留存在的字段
      .map(name => {
        const value = fieldsObj[name]
        // 兼容旧格式（直接是 xpath 字符串）
        if (typeof value === 'string') {
          return { name, xpath: value, type: 'xpath', constant: '' }
        }
        // 新格式：{ xpath: '...', type: 'xpath'|'constant', value: '...' }
        return {
          name,
          xpath: value.xpath || '',
          type: value.type || 'xpath',
          constant: value.value || '',  // 注意：数据库中存储为 value
        }
      })

    // 先完成主要加载，字段列表异步加载
    loading.value = false

    // 异步加载数据源字段（不阻塞页面显示）
    if (config.value.datasource_id) {
      loadColumns(config.value.datasource_id)
    }
  } catch (e) {
    ElMessage.error('加载任务失败')
    loading.value = false
  }
}

const loadDatasources = async () => {
  try {
    const res = await api.get('/datasource/')
    datasourceList.value = res.data || []
  } catch (e) {}
}

const loadGroups = async () => {
  try {
    const res = await api.get('/groups/names')
    groups.value = res.data || []
  } catch (e) {}
}

const loadColumns = async (datasourceId) => {
  if (!datasourceId) {
    columnsList.value = []
    return
  }
  try {
    const res = await api.get(`/datasource/${datasourceId}/columns`)
    columnsList.value = res.data || []
  } catch (e) {
    console.error('加载字段失败:', e)
    columnsList.value = []
  }
}

const onDatasourceChange = async (datasourceId) => {
  await loadColumns(datasourceId)
}

const addField = () => {
  fieldList.value.push({ name: '', xpath: '', type: 'xpath', constant: '' })
}

const removeField = (index) => {
  fieldList.value.splice(index, 1)
}

const saving = ref(false)
const resetting = ref(false)
const testing = ref(false)
const testUrl = ref('')
const testEngineName = ref('requests')
const testResult = ref(null)
const testHtml = ref('')
const testHtmlLoading = ref(false)
const previewTab = ref('preview')

const handleTest = async () => {
  if (!testUrl.value) {
    ElMessage.warning('请输入测试URL')
    return
  }
  testing.value = true
  testResult.value = null
  testHtml.value = ''
  try {
    const res = await api.post('/engines/test', {
      engine: testEngineName.value,
      url: testUrl.value,
      timeout: 30,
    })
    if (res.code === 0) {
      testResult.value = res.data
      // 自动加载HTML源码
      if (res.data.html_temp_id) {
        loadHtmlSource()
      }
      ElMessage.success('测试成功')
    } else {
      ElMessage.error(res.message || '测试失败')
    }
  } catch (e) {
    ElMessage.error('测试失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    testing.value = false
  }
}

const loadHtmlSource = async () => {
  if (!testResult.value?.html_temp_id) return
  testHtmlLoading.value = true
  try {
    const url = `/temp/test_${testResult.value.html_temp_id}.html`
    const res = await fetch(url)
    if (res.ok) {
      testHtml.value = await res.text()
    }
  } catch (e) {
    testHtml.value = '加载失败'
  } finally {
    testHtmlLoading.value = false
  }
}

const copyHtml = async () => {
  try {
    await navigator.clipboard.writeText(testHtml.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const handleResetParse = async () => {
  try {
    await ElMessageBox.confirm(
      '将重置所有已解析记录，允许重新解析。是否继续？',
      '确认重新解析',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户取消
  }

  resetting.value = true
  try {
    const res = await api.post(`/tasks/${taskId}/reset-parse`)
    if (res.code === 0) {
      ElMessage.success(res.message || '重置成功，可运行解析脚本')
    } else {
      ElMessage.error(res.message || '重置失败')
    }
  } catch (e) {
    ElMessage.error('重置失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    resetting.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    // 构建字段配置（支持 xpath 和 constant 类型）
    const fields = {}
    const fieldOrder = []  // 保存字段顺序
    fieldList.value.forEach(f => {
      if (f.name) {
        fieldOrder.push(f.name)  // 记录顺序
        if (f.type === 'constant') {
          // 常量值：直接存储
          fields[f.name] = { type: 'constant', value: f.constant || '', xpath: '' }
        } else {
          // XPath 提取
          fields[f.name] = { type: 'xpath', xpath: f.xpath || '', value: '' }
        }
      }
    })
    config.value.fields = fields
    config.value.field_order = fieldOrder  // 保存字段顺序

    // 从选中的数据源复制数据库配置
    const selectedDs = datasourceList.value.find(ds => ds.id === config.value.datasource_id)
    if (selectedDs) {
      config.value.db_host = selectedDs.host
      config.value.db_port = selectedDs.port
      config.value.db_name = selectedDs.database_name
      config.value.db_user = selectedDs.username
      config.value.db_password = selectedDs.password
    }

    // 保存配置（后端会自动重新生成所有脚本）
    await api.put(`/tasks/${taskId}`, {
      config_json: config.value,
      engine: config.value.engine,
      datasource_id: config.value.datasource_id,
      group_name: config.value.group_name,
    })

    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  // 并行加载基础数据
  await Promise.all([
    loadTask(),
    loadDatasources(),
    loadGroups()
  ])
})
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.field-list {
  margin-bottom: 15px;
}
</style>
