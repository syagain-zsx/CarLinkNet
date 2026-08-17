<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="24" color="#409eff"><Monitor /></el-icon>
        <span>智能入侵检测系统</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1f2937"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
        class="menu"
      >
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
          <el-icon><component :is="item.meta.icon" /></el-icon>
          <span>{{ item.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="page-title">{{ $route.meta.title || '' }}</div>
        <div class="header-right">
          <el-tag :type="auth.isAdmin ? 'danger' : 'info'" size="small">
            {{ auth.user?.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
          <el-dropdown @command="onCommand">
            <span class="user-name">
              {{ auth.user?.display_name || auth.user?.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const router = useRouter()

const menus = computed(() => {
  const layout = router.options.routes.find((r) => r.path === '/')
  return (layout?.children || []).filter((c) => {
    if (c.meta?.admin && !auth.isAdmin) return false
    return true
  })
})

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background-color: #1f2937;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  border-bottom: 1px solid #374151;
}
.menu {
  border-right: none;
  flex: 1;
}
.header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.user-name {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #374151;
}
.main {
  background: #f3f4f6;
  padding: 20px;
}
</style>
