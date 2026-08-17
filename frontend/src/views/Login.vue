<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="brand">
        <el-icon :size="36" color="#409eff"><Monitor /></el-icon>
        <h2>工业互联网智能入侵检测系统</h2>
        <p>Industrial IoT Intelligent Intrusion Detection System</p>
      </div>
      <el-form :model="form" @keyup.enter="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>
      <div class="tip">
        还没有账号？<router-link to="/register">立即注册</router-link>
        <span class="divider">|</span> 默认管理员：admin / admin123
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const auth = useAuthStore()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await http.post('/auth/login', form)
    auth.setAuth(data.token, data.user)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2937 0%, #374151 50%, #1e3a5f 100%);
}
.auth-card {
  width: 400px;
  padding: 10px 10px 0;
}
.brand {
  text-align: center;
  margin-bottom: 22px;
}
.brand h2 {
  font-size: 20px;
  margin: 10px 0 4px;
  color: #1f2937;
}
.brand p {
  font-size: 12px;
  color: #9ca3af;
}
.tip {
  text-align: center;
  font-size: 13px;
  color: #6b7280;
  margin-top: 16px;
}
.divider {
  margin: 0 8px;
}
</style>
