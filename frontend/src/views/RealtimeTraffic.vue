<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><span style="font-weight: 600">流量速率</span></template>
          <EChart :option="rateOption" height="260px" />
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 600">实时流量日志</span>
              <el-switch v-model="running" active-text="运行" inactive-text="暂停" />
            </div>
          </template>
          <el-table :data="flows" height="320" size="small">
            <el-table-column prop="time" label="时间" width="90" />
            <el-table-column prop="src" label="源地址" width="150" />
            <el-table-column prop="dst" label="目标地址" width="150" />
            <el-table-column prop="proto" label="协议" width="70" />
            <el-table-column prop="packets" label="包数" width="80" />
            <el-table-column prop="bytes" label="字节" width="90" />
            <el-table-column label="判定">
              <template #default="{ row }">
                <el-tag :type="row.label === 'BENIGN' ? 'success' : 'danger'" size="small">{{ row.label }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import EChart from '../components/EChart.vue'

const labels = ['BENIGN', 'DDoS', 'DoS Hulk', 'PortScan', 'Bot', 'Web Attack', 'Heartbleed', 'Patator', 'DoS Slowloris', 'DoS GoldenEye', 'DoS Slowhttptest']
const running = ref(true)
const flows = ref([])
const times = ref([])
const rates = ref([])
let timer = null

const rateOption = ref({
  grid: { left: 40, right: 16, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value', name: '包/秒' },
  series: [
    { name: '速率', type: 'line', smooth: true, data: [], areaStyle: { opacity: 0.15 }, itemStyle: { color: '#409eff' } },
  ],
})

function rnd(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}
function randInt(a, b) {
  return Math.floor(Math.random() * (b - a + 1)) + a
}

function tick() {
  const isAttack = Math.random() < 0.3
  const label = isAttack ? rnd(labels.slice(1)) : 'BENIGN'
  const packets = isAttack ? randInt(100, 3000) : randInt(5, 100)
  const flow = {
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    src: `192.168.${randInt(1, 254)}.${randInt(1, 254)}`,
    dst: `10.0.${randInt(1, 254)}.${randInt(1, 254)}`,
    proto: Math.random() < 0.85 ? 'TCP' : 'UDP',
    packets,
    bytes: packets * randInt(40, 1400),
    label,
  }
  flows.value.unshift(flow)
  if (flows.value.length > 100) flows.value.pop()

  const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  times.value.push(now)
  rates.value.push(packets)
  if (times.value.length > 30) {
    times.value.shift()
    rates.value.shift()
  }
  rateOption.value.xAxis.data = times.value
  rateOption.value.series[0].data = rates.value
}

onMounted(() => {
  timer = setInterval(() => {
    if (running.value) tick()
  }, 1000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>
