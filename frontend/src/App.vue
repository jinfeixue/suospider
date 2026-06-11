<template>
  <el-config-provider :locale="zhCn">
    <!-- 登录页：不显示侧边栏和顶栏 -->
    <div v-if="isLoginPage" style="height: 100vh">
      <router-view />
    </div>

    <!-- 其他页面：显示完整布局 -->
    <el-container v-else style="height: 100vh">
      <!-- Sidebar -->
      <el-aside width="220px" class="app-sidebar">
        <div class="sidebar-header">
          <div class="logo-icon">🕷️</div>
          <div class="logo-text">
            <h2>Spider</h2>
            <span>Manager V1.0</span>
          </div>
        </div>
        <el-menu
          :default-active="$route.path"
          class="sidebar-menu"
          router
        >
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>

          <!-- 系统配置（先配置，再采集） -->
          <el-sub-menu index="system-config">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统配置</span>
            </template>
            <el-menu-item index="/datasource">
              <el-icon><Connection /></el-icon>
              <span>数据源配置</span>
            </el-menu-item>
            <el-menu-item index="/llm-config">
              <el-icon><Cpu /></el-icon>
              <span>大模型配置</span>
            </el-menu-item>
            <el-menu-item index="/engine-manager">
              <el-icon><Van /></el-icon>
              <span>引擎管理</span>
            </el-menu-item>
          </el-sub-menu>

          <!-- 数据采集 -->
          <el-sub-menu index="data-collection">
            <template #title>
              <el-icon><DataLine /></el-icon>
              <span>数据采集</span>
            </template>
            <el-menu-item index="/smart-tasks">
              <el-icon><MagicStick /></el-icon>
              <span>智能采集</span>
            </el-menu-item>
            <el-menu-item index="/professional-tasks">
              <el-icon><List /></el-icon>
              <span>专业采集</span>
            </el-menu-item>
            <el-menu-item index="/tasks">
              <el-icon><FolderOpened /></el-icon>
              <span>全部任务</span>
            </el-menu-item>
          </el-sub-menu>

          <!-- 其他 -->
          <el-menu-item index="/editor">
            <el-icon><Edit /></el-icon>
            <span>代码编辑</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>日志中心</span>
          </el-menu-item>
          <el-menu-item index="/data">
            <el-icon><FolderOpened /></el-icon>
            <span>数据管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- Main content -->
      <el-container>
        <el-header class="app-header">
          <span class="header-title">{{ $route.meta.title || 'Spider Manager' }}</span>
          <el-button type="danger" size="small" @click="logout">退出</el-button>
        </el-header>
        <el-main style="background: #f5f7fa; padding: 20px">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// 判断是否是登录页
const isLoginPage = computed(() => route.path === '/login')

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', Arial, sans-serif; }

/* Sidebar styles */
.app-sidebar {
  background: linear-gradient(180deg, #f8f9ff 0%, #eef1f8 100%);
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 24px 20px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.logo-icon {
  font-size: 32px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.logo-text {
  margin-left: 12px;
}

.logo-text h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.logo-text span {
  font-size: 11px;
  color: #909399;
  letter-spacing: 1px;
}

.sidebar-menu {
  background: transparent !important;
  border-right: none !important;
  padding: 8px 0;
}

.sidebar-menu .el-menu-item,
.sidebar-menu .el-sub-menu__title {
  color: #606266 !important;
  height: 46px;
  line-height: 46px;
  margin: 2px 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.sidebar-menu .el-menu-item:hover,
.sidebar-menu .el-sub-menu__title:hover {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.05) 100%) !important;
  color: #667eea !important;
}

.sidebar-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
  color: #fff !important;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
}

.sidebar-menu .el-menu-item.is-active .el-icon,
.sidebar-menu .el-menu-item.is-active span {
  color: #fff !important;
}

.sidebar-menu .el-sub-menu .el-menu-item {
  padding-left: 52px !important;
  height: 42px;
  line-height: 42px;
}

.sidebar-menu .el-sub-menu .el-menu-item:hover {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.08) 0%, transparent 100%) !important;
}

.sidebar-menu .el-sub-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
}

.sidebar-menu .el-sub-menu__icon-arrow {
  color: #909399;
}

.sidebar-menu .el-menu-item .el-icon,
.sidebar-menu .el-sub-menu__title .el-icon {
  font-size: 18px;
  color: inherit;
}

.sidebar-menu .el-menu-item span,
.sidebar-menu .el-sub-menu__title span {
  font-size: 14px;
  color: inherit;
}

/* Scrollbar */
.app-sidebar::-webkit-scrollbar {
  width: 4px;
}

.app-sidebar::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 2px;
}

.app-sidebar::-webkit-scrollbar-track {
  background: transparent;
}

/* Header */
.app-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
</style>
