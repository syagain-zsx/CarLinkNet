<template>
  <el-card shadow="never">
    <template #header><span style="font-weight: 600">用户管理</span></template>
    <el-table :data="users" v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column prop="display_name" label="显示名称" min-width="140" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
            {{ row.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="row.enabled"
            :disabled="row.username === 'admin'"
            @change="(v) => toggle(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="设置角色" width="160">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            size="small"
            :disabled="row.username === 'admin'"
            @change="(v) => setRole(row, v)"
          >
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api'

const users = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    users.value = await http.get('/user/list')
  } finally {
    loading.value = false
  }
}

async function toggle(row, v) {
  await http.post(`/user/${row.id}/update`, { enabled: v })
  ElMessage.success('已更新')
  await load()
}

async function setRole(row, v) {
  await http.post(`/user/${row.id}/update`, { role: v })
  ElMessage.success('已更新')
  await load()
}

onMounted(load)
</script>
