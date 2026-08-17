<template>
  <el-card shadow="never">
    <template #header>
      <div class="header-row">
        <span style="font-weight: 600">流量数据集</span>
        <el-upload :show-file-list="false" :before-upload="beforeUpload" accept=".csv">
          <el-button type="primary" :loading="uploading">
            <el-icon style="margin-right: 4px"><Upload /></el-icon>上传 CSV
          </el-button>
        </el-upload>
      </div>
    </template>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="数据格式需为 CICFlowMeter 风格流级 CSV（含 Flow Duration、Total Fwd Packets、Label 等字段）。可使用后端脚本 scripts/generate_sample_data.py 生成示例数据。"
      style="margin-bottom: 16px"
    />

    <el-table :data="datasets" v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="filename" label="文件名" min-width="200" />
      <el-table-column prop="rows" label="样本数" width="120" />
      <el-table-column prop="uploaded_at" label="上传时间" width="180" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" link @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api'

const datasets = ref([])
const loading = ref(false)
const uploading = ref(false)

async function load() {
  loading.value = true
  try {
    datasets.value = await http.get('/data/list')
  } finally {
    loading.value = false
  }
}

async function beforeUpload(file) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await http.post('/data/upload', fd)
    ElMessage.success('上传成功')
    await load()
    return false
  } finally {
    uploading.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除数据集「${row.name}」吗？`, '提示', { type: 'warning' })
  await http.delete(`/data/${row.id}`)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
