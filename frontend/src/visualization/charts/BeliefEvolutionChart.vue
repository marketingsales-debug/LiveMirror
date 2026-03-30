<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

const props = defineProps<{
  simulationId?: string | null;
  round?: number;
}>();

type AgentHistory = {
  id: string;
  name: string;
  shifts: number[];
};

const histories = ref<AgentHistory[]>([]);
let eventSource: EventSource | null = null;

const setupSSE = () => {
  eventSource = new EventSource('/api/events');
  
  eventSource.addEventListener('simulation_round', (event: MessageEvent) => {
    const message = JSON.parse(event.data);
    const data = message.data;
    
    if (data.simulation_id === props.simulationId && data.belief_profile && data.trust_network) {
      const nodes = data.trust_network.nodes as Array<{ id: string; name: string }>;
      const profile = data.belief_profile as Record<string, number>;
      
      nodes.forEach((node) => {
        let agent = histories.value.find((h) => h.id === node.id);
        if (!agent) {
          agent = { id: node.id, name: node.name, shifts: [] };
          histories.value.push(agent);
        }
        const shiftValue = Number(profile[node.id] ?? 0);
        agent.shifts.push(shiftValue);
        if (agent.shifts.length > 15) agent.shifts.shift();
      });
    }
  });

  eventSource.onerror = (err) => {
    console.error("Belief SSE Connection Failed:", err);
    eventSource?.close();
  };
};

onMounted(() => {
  setupSSE();
});

onUnmounted(() => {
  eventSource?.close();
});
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
            height: ((shift + 1) / 2) * 100 + '%',
            backgroundColor: shift >= 0 ? '#66fcf1' : '#ff4d4d',
            left: `${Number(i) * 15}px`
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
