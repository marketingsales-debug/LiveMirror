<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';

const props = defineProps({
  simulationId: String,
  round: Number
});

// For an animated line chart capturing belief evolution,
// we will stub out the CSS framework for it before integrating Chart.js/D3.
const chartContainer = ref<HTMLElement | null>(null);

const histories = ref([
  { id: 1, name: 'Agent 1', shifts: [-0.1, 0.2, 0.3, 0.5] },
  { id: 2, name: 'Agent 2', shifts: [0.8, 0.7, 0.6, 0.6] },
  { id: 3, name: 'Agent 3', shifts: [-0.6, -0.6, -0.7, -0.8] },
]); // Mocked `belief_history` for CSS alignment.

</script>

<template>
  <div class="belief-evolution-chart" ref="chartContainer">
    <div class="tracks" v-for="agent in histories" :key="agent.id">
      <div class="track-label">{{ agent.name }}</div>
      <div class="sparkline">
        <!-- We use simple CSS bars to represent alignment shift for the stub -->
        <span 
          v-for="(shift, i) in agent.shifts" 
          :key="i"
          class="bar"
          :style="{ 
            height: Math.abs(shift) * 100 + '%',
            backgroundColor: shift >= 0 ? 'var(--accent-color)' : '#ff4d4d',
            left: (i * 20) + 'px'
          }"
        ></span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.belief-evolution-chart {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.tracks {
  display: flex;
  align-items: center;
  gap: 16px;
}

.track-label {
  width: 80px;
  font-size: 0.8rem;
  color: var(--text-primary);
  opacity: 0.8;
}

.sparkline {
  flex: 1;
  height: 40px;
  position: relative;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.bar {
  position: absolute;
  bottom: 0;
  width: 12px;
  min-height: 2px;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  transition: height 0.3s ease;
}
</style>
