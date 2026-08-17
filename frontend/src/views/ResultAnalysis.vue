<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 16px">
      <div class="toolbar">
        <el-select v-model="currentCode" placeholder="选择检测任务" style="width: 420px" @change="loadResult">
          <el-option v-for="t in tasks" :key="t.task_code" :label="`${t.task_code} — ${t.name}（${statusText(t.status)}）`" :value="t.task_code" />
        </el-select>
        <el-button @click="loadTasks">刷新</el-button>
      </div>
    </el-card>

    <template v-if="result">
      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="6" v-for="c in cards" :key="c.label">
          <el-card shadow="hover" class="mini-card">
            <div class="mini-value" :style="{ color: c.color }">{{ c.value }}</div>
            <div class="mini-label">{{ c.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><span style="font-weight: 600">攻击类别分布</span></template>
            <EChart :option="pieOption" height="360px" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><span style="font-weight: 600">检测结果明细</span></template>
            <el-table :data="result.items" size="small" max-height="360">
              <el-table-column prop="label" label="类别" min-width="150">
                <template #default="{ row }">
                  <el-tag :type="row.label === 'BENIGN' ? 'success' : 'danger'" size="small">{{ row.label }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="count" label="数量" width="100" />
              <el-table-column prop="confidence_avg" label="平均置信度" width="120">
                <template #default="{ row }">
                  {{ (row.confidence_avg * 100).toFixed(1) }}%
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else description="请选择任务查看检测结果" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api'
import EChart from '../components/EChart.vue'

const route = useRoute()
const tasks = ref([])
const currentCode = ref(route.query.code || '')
const result = ref(null)

const statusText = (s) => ({ pending: '待处理', running: '运行中', finished: '已完成', failed: '失败' }[s] || s)

const cards = computed(() => [
  { label: '总流量', value: result.value?.total ?? 0, color: '#409eff' },
  { label: '攻击流量', value: result.value?.attack_count ?? 0, color: '#f56c6c' },
  { label: '正常流量', value: result.value?.benign_count ?? 0, color: '#67c23a' },
  { label: '检测来源', value: sourceText(result.value?.source), color: '#e6a23c' },
])

const sourceText = (s) => ({ rule: '规则引擎', ensemble: 'PSO-CFW 集成', student: '蒸馏学生模型', collaborative: '规则+模型协同' }[s] || s)

const pieOption = computed(() => {
  const items = result.value?.items || []
  const colors = ['#409eff', '#f56c6c', '#e6a23c', '#67c23a', '#909399', '#9c27b0', '#00bcd4', '#ff9800', '#795548', '#3f51b5', '#f44336']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['38%', '68%'],
        center: ['42%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: items.map((i, idx) => ({ name: i.label, value: i.count, itemStyle: { color: colors[idx % colors.length] } })),
      },
    ],
  }
})

async function loadTasks() {
  tasks.value = await http.get('/detection/tasks')
  const finished = tasks.value.filter((t) => t.status === 'finished')
  if (!currentCode.value && finished.length) {
    currentCode.value = finished[0].task_code
    await loadResult()
  }
}

async function loadResult() {
  if (!currentCode.value) return
  result.value = await http.get(`/result/${currentCode.value}`)
}

onMounted(async () => {
  await loadTasks()
  if (currentCode.value) await loadResult()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}
.mini-card {
  text-align: center;
}
.mini-value {
  font-size: 30px;
  font-weight: 700;
}
.mini-label {
  font-size: 13px;
  color: #6b7280;
  margin-top: 6px;
}
</style>
