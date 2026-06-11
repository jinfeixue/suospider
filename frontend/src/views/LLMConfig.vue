<template>
  <div class="llm-config-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>大模型配置</span>
          <el-button type="primary" @click="showAddDialog">添加配置</el-button>
        </div>
      </template>

      <el-table :data="configList" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="provider" label="提供商" width="100" />
        <el-table-column prop="model" label="模型" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="默认" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="warning">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row)">测试</el-button>
            <el-button size="small" type="success" @click="setDefault(row)">设为默认</el-button>
            <el-button size="small" type="warning" @click="editConfig(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑配置' : '添加配置'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="请输入配置名称" />
        </el-form-item>
        <el-form-item label="提供商" required>
          <el-select v-model="form.provider" placeholder="请选择提供商">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="阿里云" value="aliyun" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型" required>
          <el-input v-model="form.model" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item label="API密钥" required>
          <el-input v-model="form.api_key" type="password" placeholder="请输入API密钥" />
        </el-form-item>
        <el-form-item label="API地址">
          <el-input v-model="form.api_url" placeholder="留空使用默认地址" />
        </el-form-item>
        <el-form-item label="温度参数">
          <el-input v-model="form.temperature" placeholder="0.1" />
        </el-form-item>
        <el-form-item label="最大Token">
          <el-input-number v-model="form.max_tokens" :min="100" :max="32000" />
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number v-model="form.timeout" :min="5" :max="120" />
          <span style="margin-left: 10px">秒</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="success" @click="testInDialog" :loading="testing">
          <el-icon><VideoPlay /></el-icon> 测试连通性
        </el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'
import api from '../api'

const configList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const testing = ref(false)

const form = ref({
  name: '',
  provider: 'openai',
  model: '',
  api_key: '',
  api_url: '',
  temperature: '0.1',
  max_tokens: 4000,
  timeout: 30
})

const loadConfigs = async () => {
  try {
    const res = await api.get('/llm-config/')
    configList.value = res.data?.data || res.data || []
  } catch (error) {
    ElMessage.error('加载配置列表失败')
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.value = {
    name: '', provider: 'openai', model: '', api_key: '',
    api_url: '', temperature: '0.1', max_tokens: 4000, timeout: 30
  }
  dialogVisible.value = true
}

const editConfig = (row) => {
  isEdit.value = true
  editId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    if (isEdit.value) {
      await api.put(`/llm-config/${editId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/llm-config/', form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadConfigs()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const testInDialog = async () => {
  if (!form.value.provider || !form.value.model || !form.value.api_key) {
    ElMessage.warning('请先填写提供商、模型和API密钥')
    return
  }
  testing.value = true
  try {
    // 先保存再测试
    let configId = editId.value
    if (!isEdit.value || !configId) {
      const res = await api.post('/llm-config/', form.value)
      configId = res.data?.data?.id || res.data?.id
      await loadConfigs()
    }
    if (configId) {
      const res = await api.post(`/llm-config/${configId}/test`)
      const data = res.data?.data || res.data
      if (data?.success) {
        ElMessage.success(`连接成功，响应时间: ${data.response_time || 0}秒`)
      } else {
        ElMessage.error(data?.message || '测试失败')
      }
    }
  } catch (error) {
    ElMessage.error('测试失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    testing.value = false
  }
}

const testConnection = async (row) => {
  try {
    const res = await api.post(`/llm-config/${row.id}/test`)
    const data = res.data?.data || res.data
    if (data?.success) {
      ElMessage.success(`连接成功，响应时间: ${data.response_time || 0}秒`)
    } else {
      ElMessage.error(data?.message || '测试失败')
    }
  } catch (error) {
    ElMessage.error('测试失败')
  }
}

const setDefault = async (row) => {
  try {
    await api.post(`/llm-config/${row.id}/set-default`)
    ElMessage.success('已设为默认配置')
    await loadConfigs()
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

const deleteConfig = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该配置吗？', '提示', { type: 'warning' })
    await api.delete(`/llm-config/${row.id}`)
    ElMessage.success('删除成功')
    await loadConfigs()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.llm-config-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
