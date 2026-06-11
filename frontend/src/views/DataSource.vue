<template>
  <div class="datasource-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据源管理</span>
          <el-button type="primary" @click="showAddDialog">添加数据源</el-button>
        </div>
      </template>

      <el-table :data="datasourceList" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="host" label="主机" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="database_name" label="数据库名" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row)">测试</el-button>
            <el-button size="small" type="success" @click="initDatabase(row)">初始化</el-button>
            <el-button size="small" type="warning" @click="editDatasource(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteDatasource(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑数据源' : '添加数据源'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="请输入数据源名称" />
        </el-form-item>
        <el-form-item label="主机" required>
          <el-input v-model="form.host" placeholder="请输入数据库主机" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="数据库名">
          <el-input v-model="form.database_name" placeholder="留空自动生成" />
        </el-form-item>
        <el-form-item label="字符集">
          <el-select v-model="form.charset">
            <el-option label="utf8mb4" value="utf8mb4" />
            <el-option label="utf8" value="utf8" />
            <el-option label="gbk" value="gbk" />
          </el-select>
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

const datasourceList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const testing = ref(false)

const form = ref({
  name: '', host: '', port: 3306, username: '', password: '',
  database_name: '', charset: 'utf8mb4'
})

const loadDatasources = async () => {
  try {
    const res = await api.get('/datasource/')
    datasourceList.value = res.data?.data || res.data || []
  } catch (error) {
    ElMessage.error('加载数据源列表失败')
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.value = {
    name: '', host: '', port: 3306, username: '', password: '',
    database_name: '', charset: 'utf8mb4'
  }
  dialogVisible.value = true
}

const editDatasource = (row) => {
  isEdit.value = true
  editId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    if (isEdit.value) {
      await api.put(`/datasource/${editId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      const res = await api.post('/datasource/', form.value)
      const msg = res.data?.data?.init_message || ''
      ElMessage.success('添加成功' + msg)
    }
    dialogVisible.value = false
    await loadDatasources()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const testInDialog = async () => {
  if (!form.value.host || !form.value.username || !form.value.password) {
    ElMessage.warning('请先填写主机、用户名和密码')
    return
  }
  testing.value = true
  try {
    // 先保存再测试
    let dsId = editId.value
    if (!isEdit.value || !dsId) {
      const res = await api.post('/datasource/', form.value)
      dsId = res.data?.data?.id || res.data?.id
      await loadDatasources()
    }
    if (dsId) {
      const res = await api.post(`/datasource/${dsId}/test`)
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
    const res = await api.post(`/datasource/${row.id}/test`)
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

const initDatabase = async (row) => {
  try {
    await ElMessageBox.confirm('确定要初始化数据库和表吗？', '提示', { type: 'warning' })
    const res = await api.post(`/datasource/${row.id}/init-db`)
    ElMessage.success(res.data?.message || '初始化成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '初始化失败')
    }
  }
}

const deleteDatasource = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该数据源吗？', '提示', { type: 'warning' })
    await api.delete(`/datasource/${row.id}`)
    ElMessage.success('删除成功')
    await loadDatasources()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadDatasources()
})
</script>

<style scoped>
.datasource-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
