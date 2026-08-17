<template>
  <el-row :gutter="16">
    <el-col :span="16">
      <el-card shadow="never">
        <template #header><span style="font-weight: 600">内置默认规则（签名匹配）</span></template>
        <el-table :data="defaultRules" size="small">
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="label" label="攻击类型" width="140">
            <template #default="{ row }">
              <el-tag type="danger" size="small">{{ row.label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="severity" label="级别" width="90">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'high' ? 'danger' : 'warning'" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="条件" min-width="300">
            <template #default="{ row }">
              <span class="cond">{{ describe(row.conditions) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>

    <el-col :span="8">
      <el-card shadow="never">
        <template #header>
          <div class="header-row">
            <span style="font-weight: 600">自定义规则集</span>
            <el-upload :show-file-list="false" :before-upload="beforeUpload" accept=".json">
              <el-button type="primary" size="small" :loading="uploading">上传 JSON</el-button>
            </el-upload>
          </div>
        </template>
        <el-table :data="rulesets" v-loading="loading" size="small">
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="rule_count" label="规则数" width="80" />
          <el-table-column label="启用" width="70">
            <template #default="{ row }">
              <el-switch :model-value="row.enabled" @change="(v) => toggle(row, v)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70">
            <template #default="{ row }">
              <el-button type="danger" link @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api'

const defaultRules = ref([])
const rulesets = ref([])
const loading = ref(false)
const uploading = ref(false)

const OP_TEXT = { '>': '大于', '<': '小于', '>=': '≥', '<=': '≤', '==': '等于', '!=': '≠', in: '∈', not_in: '∉' }

function describe(conditions) {
  return conditions
    .map((c) => {
      const val = Array.isArray(c.value) ? c.value.join(',') : c.value
      return `${c.field} ${OP_TEXT[c.op] || c.op} ${val}`
    })
    .join(' 且 ')
}

async function load() {
  loading.value = true
  try {
    const [d, list] = await Promise.all([http.get('/rule/default'), http.get('/rule/list')])
    defaultRules.value = d.rules
    rulesets.value = list
  } finally {
    loading.value = false
  }
}

async function beforeUpload(file) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await http.post('/rule/upload', fd)
    ElMessage.success('规则集上传成功')
    await load()
    return false
  } finally {
    uploading.value = false
  }
}

async function toggle(row, v) {
  await http.post(`/rule/${row.id}/toggle`)
  await load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除规则集「${row.name}」吗？`, '提示', { type: 'warning' })
  await http.delete(`/rule/${row.id}`)
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
.cond {
  font-size: 12px;
  color: #6b7280;
}
</style>
