<template>
  <el-row :gutter="16">
    <el-col :span="10">
      <el-card shadow="never">
        <template #header><span style="font-weight: 600">生成特征集</span></template>
        <el-form label-width="100px">
          <el-form-item label="数据集">
            <el-select v-model="form.dataset_id" placeholder="选择数据集" style="width: 100%">
              <el-option v-for="d in datasets" :key="d.id" :label="`${d.name}（${d.rows} 条）`" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="特征类型">
            <el-select v-model="form.feature_type" style="width: 100%">
              <el-option v-for="t in types" :key="t.value" :label="`${t.label}（${t.dim} 维）`" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="特征集名称">
            <el-input v-model="form.name" placeholder="可选，默认自动命名" />
          </el-form-item>
          <el-button type="primary" :loading="generating" style="width: 100%" @click="generate">
            🚀 生成特征
          </el-button>
        </el-form>

        <template v-if="result">
          <el-divider />
          <el-descriptions :column="1" border>
            <el-descriptions-item label="特征集 ID">{{ result.id }}</el-descriptions-item>
            <el-descriptions-item label="总维度">{{ result.total }}</el-descriptions-item>
            <el-descriptions-item v-for="(dim, k) in result.dimensions" :key="k" :label="result.view_labels[k] || k">
              {{ dim }} 维
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </el-card>
    </el-col>

    <el-col :span="14">
      <el-card shadow="never">
        <template #header><span style="font-weight: 600">特征集列表</span></template>
        <el-table :data="features" v-loading="loading">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column prop="feature_type" label="类型" width="130" />
          <el-table-column prop="dimensions" label="维度分布" min-width="220" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api'

const datasets = ref([])
const features = ref([])
const types = ref([])
const loading = ref(false)
const generating = ref(false)
const result = ref(null)
const form = reactive({ dataset_id: null, feature_type: 'all', name: '' })

async function load() {
  loading.value = true
  try {
    const [ds, fs, ts] = await Promise.all([
      http.get('/data/list'),
      http.get('/feature/list'),
      http.get('/feature/types'),
    ])
    datasets.value = ds
    features.value = fs
    types.value = ts
  } finally {
    loading.value = false
  }
}

async function generate() {
  if (!form.dataset_id) {
    ElMessage.warning('请选择数据集')
    return
  }
  generating.value = true
  try {
    result.value = await http.post('/feature/generate', form)
    ElMessage.success('特征生成成功')
    await load()
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>
