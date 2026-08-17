<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="brand">
        <el-icon :size="36" color="#409eff"><Monitor /></el-icon>
        <h2>注册账号</h2>
      </div>
      <el-form :model="form" @keyup.enter="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名（2-32 字符）" size="large">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.display_name" placeholder="显示名称（可选）" size="large">
            <template #prefix><el-icon><Postcard /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码（至少 6 位）" size="large" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          注 册
        </el-button>
      </el-form>
      <div class="tip">已有账号？<router-link to="/login">返回登录</router-link></div>
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
const form = reactive({ username: '', display_name: '', password: '' })
const loading = ref(false)

async function submit() {
  if (form.username.length < 2 || form.password.length < 6) {
    ElMessage.warning('用户名至少 2 位，密码至少 6 位')
    return
  }
  loading.value = true
  try {
    const data = await http.post('/auth/register', form)
    auth.setAuth(data.token, data.user)
    ElMessage.success('注册成功')
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
  margin: 10px 0;
  color: #1f2937;
}
.tip {
  text-align: center;
  font-size: 13px;
  color: #6b7280;
  margin-top: 16px;
}
</style>
