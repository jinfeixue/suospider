import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '仪表盘', requiresAuth: true },
  },
  {
    path: '/tasks',
    name: 'TaskList',
    component: () => import('../views/TaskList.vue'),
    meta: { title: '全部任务', requiresAuth: true },
  },
  {
    path: '/smart-tasks',
    name: 'SmartTaskList',
    component: () => import('../views/TaskList.vue'),
    meta: { title: '智能采集', requiresAuth: true },
  },
  {
    path: '/professional-tasks',
    name: 'ProfessionalTaskList',
    component: () => import('../views/TaskList.vue'),
    meta: { title: '专业采集', requiresAuth: true },
  },
  {
    path: '/tasks/:id',
    name: 'TaskDetail',
    component: () => import('../views/TaskDetail.vue'),
    meta: { title: '任务详情', requiresAuth: true },
  },
  {
    path: '/tasks/:id/config',
    name: 'TaskConfig',
    component: () => import('../views/TaskConfig.vue'),
    meta: { title: '专业采集配置', requiresAuth: true },
  },
  {
    path: '/tasks/:id/smart-config',
    name: 'SmartTaskConfig',
    component: () => import('../views/SmartTaskConfig.vue'),
    meta: { title: '智能采集配置', requiresAuth: true },
  },
  {
    path: '/editor',
    name: 'ScriptEditor',
    component: () => import('../views/ScriptEditor.vue'),
    meta: { title: '代码编辑', requiresAuth: true },
  },
  {
    path: '/editor/:taskId/:type',
    name: 'ScriptEditorWithTask',
    component: () => import('../views/ScriptEditor.vue'),
    meta: { title: '代码编辑', requiresAuth: true },
  },
  {
    path: '/logs',
    name: 'LogCenter',
    component: () => import('../views/LogCenter.vue'),
    meta: { title: '日志中心', requiresAuth: true },
  },
  {
    path: '/logs/:runId',
    name: 'LogDetail',
    component: () => import('../views/LogCenter.vue'),
    meta: { title: '运行日志', requiresAuth: true },
  },
  {
    path: '/data',
    name: 'DataViewer',
    component: () => import('../views/DataViewer.vue'),
    meta: { title: '数据管理', requiresAuth: true },
  },
  {
    path: '/engine-test',
    name: 'EngineTest',
    component: () => import('../views/EngineTest.vue'),
    meta: { title: '引擎调试', requiresAuth: true },
  },
  {
    path: '/engine-manager',
    name: 'EngineManager',
    component: () => import('../views/EngineManager.vue'),
    meta: { title: '引擎管理', requiresAuth: true },
  },
  {
    path: '/datasource',
    name: 'DataSource',
    component: () => import('../views/DataSource.vue'),
    meta: { title: '数据源管理', requiresAuth: true },
  },
  {
    path: '/llm-config',
    name: 'LLMConfig',
    component: () => import('../views/LLMConfig.vue'),
    meta: { title: '大模型配置', requiresAuth: true },
  },
  {
    path: '/smart-wizard',
    name: 'SmartWizard',
    component: () => import('../views/SmartWizard.vue'),
    meta: { title: '智能采集向导', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 - 检查登录状态
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false // 默认需要认证

  if (requiresAuth && !token) {
    // 需要认证但没有token，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录用户访问登录页，跳转到首页
    next('/')
  } else {
    next()
  }
})

export default router
