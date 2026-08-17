<template>
  <div>
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" :style="{ background: card.color }">
            <el-icon :size="26" color="#fff"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <span style="font-weight: 600">系统概览</span>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="检测任务总数">{{ summary.total_tasks ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="已完成任务">{{ summary.finished_tasks ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="运行中/待处理">{{ summary.running_tasks ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="检测出的攻击流量">{{ summary.total_attacks ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="正常流量">{{ summary.total_benign ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="数据集 / 规则集">{{ summary.total_datasets ?? '-' }} / {{ summary.total_rulesets ?? '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <span style="font-weight: 600">核心技术</span>
      </template>
      <el-row :gutter="16">
        <el-col v-for="t in techs" :key="t.title" :span="6">
          <el-card shadow="hover" class="tech-card">
            <div class="tech-title">{{ t.icon }} {{ t.title }}</div>
            <div class="tech-desc">{{ t.desc }}</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import http from '../api'

const summary = ref({})

const cards = computed(() => [
  { label: '检测任务总数', value: summary.value.total_tasks ?? '-', icon: 'List', color: '#409eff' },
  { label: '已完成任务', value: summary.value.finished_tasks ?? '-', icon: 'CircleCheck', color: '#67c23a' },
  { label: '检测攻击流量', value: summary.value.total_attacks ?? '-', icon: 'Warning', color: '#f56c6c' },
  { label: '正常流量', value: summary.value.total_benign ?? '-', icon: 'CircleCheck', color: '#909399' },
])

const techs = [
  { icon: '🧠', title: '多视图特征', desc: '统计 / 行为时间结构 / 多尺度频域三类特征联合刻画网络行为' },
  { icon: '🤝', title: 'PSO-CFW 集成', desc: '粒子群优化的类别级加权融合，聚合 CNN / XGBoost / FT-Transformer' },
  { icon: '📉', title: '双教师蒸馏', desc: '知识蒸馏压缩出轻量学生模型，适配边缘低算力部署' },
  { icon: '🔐', title: '多中心联邦学习', desc: '非 IID 客户端聚类协同，数据不出域，兼顾隐私与精度' },
]

onMounted(async () => {
  summary.value = await http.get('/result/summary')
})
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
}
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}
.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2937;
}
.stat-label {
  font-size: 13px;
  color: #6b7280;
}
.tech-card {
  text-align: center;
}
.tech-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f2937;
}
.tech-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}
</style>
