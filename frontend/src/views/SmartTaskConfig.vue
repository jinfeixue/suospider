<template>
  <div v-loading="loading">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>智能采集配置: {{ task?.name || '加载中...' }}</span>
          <el-space>
            <el-button @click="$router.back()">返回</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
          </el-space>
        </div>
      </template>

      <el-form :model="config" label-width="120px">
        <!-- 基础配置 -->
        <el-divider content-position="left">基础配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="目标URL" required>
              <el-input v-model="config.url" placeholder="https://example.com" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="采集页数">
              <el-input-number v-model="config.max_pages" :min="1" :max="1000" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="请求间隔">
              <el-input-number v-model="config.interval" :min="1" :max="60" />
              <span style="margin-left: 5px">秒</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
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
          <el-col :span="8">
            <el-form-item label="数据源" required>
              <el-select v-model="config.datasource_id" placeholder="请选择数据源" style="width: 100%">
                <el-option
                  v-for="ds in datasourceList"
                  :key="ds.id"
                  :label="`${ds.name} (${ds.host}:${ds.port})`"
                  :value="ds.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="大模型">
              <el-select v-model="config.llm_config_id" placeholder="请选择大模型" style="width: 100%">
                <el-option
                  v-for="llm in llmConfigs"
                  :key="llm.id"
                  :label="`${llm.name} (${llm.provider})`"
                  :value="llm.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 采集规则 -->
        <el-divider content-position="left">采集规则（AI自动生成，可手动调整）</el-divider>

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="详情页链接" required>
              <el-input v-model="config.detail_link_xpath" placeholder="//div[@class='article']//h2/a/@href">
                <template #append>
                  <el-button @click="testXPath('detail_link')">测试</el-button>
                </template>
              </el-input>
              <div class="form-tip">从列表页提取详情页链接的XPath</div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 翻页配置 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="翻页类型">
              <el-select v-model="config.pagination_type" style="width: 100%">
                <el-option label="下一页按钮" value="next_button" />
                <el-option label="URL页码递增" value="url_pattern" />
                <el-option label="无翻页" value="none" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8" v-if="config.pagination_type === 'next_button'">
            <el-form-item label="下一页XPath">
              <el-input v-model="config.next_xpath" placeholder="//a[@rel='next']/@href" />
            </el-form-item>
          </el-col>
          <el-col :span="8" v-if="config.pagination_type === 'url_pattern'">
            <el-form-item label="URL规律">
              <el-input v-model="config.page_url_template" placeholder="?page={page}" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 字段配置 -->
        <el-divider content-position="left">字段XPath配置</el-divider>
        <div class="field-list">
          <el-row v-for="(field, index) in fieldList" :key="index" :gutter="10" style="margin-bottom: 10px">
            <el-col :span="4">
              <el-select v-model="field.name" placeholder="字段名" filterable>
                <el-option label="标题" value="title" />
                <el-option label="正文" value="content" />
                <el-option label="发布日期" value="chubanriqi" />
                <el-option label="作者" value="zuozhe" />
                <el-option label="关键词" value="keyword" />
                <el-option label="摘要" value="abstract" />
                <el-option label="来源" value="kanming" />
                <el-option label="图片" value="wwwimages" />
              </el-select>
            </el-col>
            <el-col :span="16">
              <el-input v-model="field.xpath" placeholder="XPath表达式">
                <template #prepend>
                  <el-tag v-if="field.confidence" :type="field.confidence >= 80 ? 'success' : 'warning'" size="small">
                    {{ field.confidence }}%
                  </el-tag>
                </template>
              </el-input>
            </el-col>
            <el-col :span="4">
              <el-button type="danger" :icon="Delete" circle @click="removeField(index)" />
            </el-col>
          </el-row>
        </div>
        <el-button type="primary" size="small" @click="addField">
          <el-icon><Plus /></el-icon> 添加字段
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id
const loading = ref(false)

const task = ref({})
const config = ref({
  url: '',
  engine: 'requests',
  max_pages: 5,
  interval: 2,
  datasource_id: null,
  llm_config_id: null,
  detail_link_xpath: '',
  pagination_type: 'next_button',
  next_xpath: '',
  page_url_template: '',
  fields: {},
})

const fieldList = ref([])
const datasourceList = ref([])
const llmConfigs = ref([])

const loadTask = async () => {
  loading.value = true
  try {
    const res = await api.get(`/tasks/${taskId}`)
    task.value = res.data
    const cfg = task.value.config_json || {}
    config.value = {
      url: cfg.url || '',
      engine: cfg.engine || 'requests',
      max_pages: cfg.max_pages || 5,
      interval: cfg.interval || 2,
      datasource_id: cfg.datasource_id || task.value.datasource_id,
      llm_config_id: cfg.llm_config_id || null,
      detail_link_xpath: cfg.detail_link_xpath || '',
      pagination_type: cfg.pagination_type || 'next_button',
      next_xpath: cfg.next_xpath || '',
      page_url_template: cfg.page_url_template || '',
      fields: cfg.fields || {},
    }

    // 转换字段为列表
    fieldList.value = Object.entries(config.value.fields).map(([name, xpath]) => ({
      name,
      xpath,
      confidence: 85,
    }))
  } catch (e) {
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

const loadDatasources = async () => {
  try {
    const res = await api.get('/datasource/')
    datasourceList.value = res.data || []
  } catch (e) {}
}

const loadLLMConfigs = async () => {
  try {
    const res = await api.get('/llm-config/')
    llmConfigs.value = res.data || []
  } catch (e) {}
}

const addField = () => {
  fieldList.value.push({ name: '', xpath: '', confidence: 0 })
}

const removeField = (index) => {
  fieldList.value.splice(index, 1)
}

const saving = ref(false)

const handleSave = async () => {
  saving.value = true
  try {
    // 转换字段列表为对象
    const fields = {}
    fieldList.value.forEach(f => {
      if (f.name && f.xpath) {
        fields[f.name] = f.xpath
      }
    })
    config.value.fields = fields

    // 保存配置
    await api.put(`/tasks/${taskId}`, {
      config_json: config.value,
      engine: config.value.engine,
      datasource_id: config.value.datasource_id,
    })

    // 自动同步到脚本
    await api.post(`/tasks/${taskId}/scripts/full/regenerate`)

    ElMessage.success('保存并同步成功')
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
    loadLLMConfigs()
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
