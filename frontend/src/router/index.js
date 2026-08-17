import { createRouter, createWebHashHistory } from 'vue-router'
import Layout from '../layout/Layout.vue'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  { path: '/register', component: () => import('../views/Register.vue') },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '仪表盘', icon: 'Odometer' } },
      { path: 'realtime', component: () => import('../views/RealtimeTraffic.vue'), meta: { title: '实时流量', icon: 'DataLine' } },
      { path: 'data', component: () => import('../views/DataManagement.vue'), meta: { title: '数据管理', icon: 'FolderOpened' } },
      { path: 'feature', component: () => import('../views/FeatureGeneration.vue'), meta: { title: '特征生成', icon: 'MagicStick' } },
      { path: 'rule', component: () => import('../views/RuleManagement.vue'), meta: { title: '规则管理', icon: 'SetUp' } },
      { path: 'detection', component: () => import('../views/DetectionCenter.vue'), meta: { title: '检测中心', icon: 'Aim' } },
      { path: 'result', component: () => import('../views/ResultAnalysis.vue'), meta: { title: '结果分析', icon: 'PieChart' } },
      { path: 'user', component: () => import('../views/UserManagement.vue'), meta: { title: '用户管理', icon: 'User', admin: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && to.path !== '/register' && !token) {
    return '/login'
  }
  return true
})

export default router
