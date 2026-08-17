<template>
  <el-row :gutter="16">
    <el-col :span="8">
      <el-card shadow="never">
        <template #header><span style="font-weight: 600">发起检测任务</span></template>
        <el-form label-width="90px">
          <el-form-item label="数据集">
            <el-select v-model="form.dataset_id" placeholder="选择数据集" style="width: 100%">
              <el-option v-for="d in datasets" :key="d.id" :label="`${d.name}（${d.rows} 条）`" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="检测模式">
            <el-radio-group v-model="form.mode">
              <el-radio value="model">模型检测</el-radio>
              <el-radio value="rule">规则检测</el-radio>
              <el-radio value="collaborative">协同检测</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.mode !== 'model'" label="规则集">
            <el-select v-model="form.ruleset_id" placeholder="不选则使用内置规则" clearable style="width: 100%">
              <el-option v-for="r in rulesets" :key="r.id" :label="`${r.name}（${r.rule_count} 条）`" :value="r.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.mode !== 'rule'" label="轻量模型">
            <el-switch v-model="form.use_student" active-text="学生模型" inactive-text="集成模型" />
          </el-form-item>
          <el-form-item label="任务名称">
            <el-input v-model="form.name" placeholder="可选" />
          </el-form-item>
          <el-button type="primary" :loading="creating" style="width: 100%" @click="create">
            🔍 发起检测
          </el-button>
        </el-form>
        <el-alert
          type="info"
          :closable="false"
          style="margin-top: 14px"
          title="模式说明"
          description="模型检测走多视图集成/蒸馏模型；规则检测走签名匹配；协同检测 = 规则快判优先，未命中交模型（分阶段判决）。"
        />
      </el-card>
    </el-col>

    <el-col :span="16">
      <el-card shadow="never">
        <template #header>
          <div class="header-row">
            <span style="font-weight: 600">任务列表</span>
            <el-button size="small" @click="load">刷新</el-button>
          </div>
        </template>
        <el-table :data="tasks" v-loading="loading">
          <el-table-column prop="task_code" label="任务编码" width="220" />
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="mode" label="模式" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="{ rule: 'warning', model: 'primary', collaborative: 'success' }[row.mode]">
                {{ modeText(row.mode) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'finished'" type="primary" link @click="$router.push('/result?code=' + row.task_code)">
                查看结果
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api'

const datasets = ref([])
const rulesets = ref([])
const tasks = ref([])
const loading = ref(false)
const creating = ref(false)
const form = reactive({ dataset_id: null, mode: 'model', ruleset_id: null, use_student: false, name: '' })
let timer = null

const modeText = (m) => ({ rule: '规则检测', model: '模型检测', collaborative: '协同检测' }[m] || m)
const statusText = (s) => ({ pending: '待处理', running: '运行中', finished: '已完成', failed: '失败' }[s] || s)
const statusType = (s) => ({ pending: 'info', running: 'warning', finished: 'success', failed: 'danger' }[s] || 'info')

async function load() {
  loading.value = true
  try {
    const [ds, rs, ts] = await Promise.all([
      http.get('/data/list'),
      http.get('/rule/list'),
      http.get('/detection/tasks'),
    ])
    datasets.value = ds
    rulesets.value = rs
    tasks.value = ts
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.dataset_id) {
    ElMessage.warning('请选择数据集')
    return
  }
  creating.value = true
  try {
    const payload = { ...form, ruleset_id: form.mode === 'model' ? null : form.ruleset_id }
    await http.post('/detection/task', payload)
    ElMessage.success('任务已创建，后台执行中')
    await load()
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(() => {
    if (tasks.value.some((t) => t.status === 'pending' || t.status === 'running')) load()
  }, 2000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
