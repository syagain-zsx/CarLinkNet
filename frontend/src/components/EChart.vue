<template>
  <div ref="el" :style="{ width: '100%', height }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
})

const el = ref(null)
let chart = null

function resize() {
  if (chart) chart.resize()
}

onMounted(() => {
  chart = echarts.init(el.value)
  chart.setOption(props.option)
  window.addEventListener('resize', resize)
})

watch(
  () => props.option,
  (o) => {
    if (chart && o) chart.setOption(o, true)
  },
  { deep: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (chart) chart.dispose()
})
</script>
