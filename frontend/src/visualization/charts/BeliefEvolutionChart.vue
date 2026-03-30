<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

const props = defineProps<{
  simulationId?: string | null;
  round?: number;
}>();

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

type AgentHistory = {
  id: string;
  name: string;
  shifts: number[];
};

const histories = ref<AgentHistory[]>([]);
let eventSource: EventSource | null = null;
let reconnectTimer: number | null = null;
let retryDelay = 1000;
const maxRetryDelay = 30000;
let isUnmounted = false;

const safeParse = <T>(raw: string, label: string): T | null => {
  if (typeof raw !== 'string') {
    console.warn(`Expected ${label} SSE payload to be string.`);
    return null;
  }
  try {
    return JSON.parse(raw) as T;
  } catch (error) {
    console.warn(`Failed to parse ${label} SSE payload`, error);
    return null;
  }
};

const scheduleReconnect = () => {
  if (reconnectTimer !== null || isUnmounted) return;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    setupSSE();
  }, retryDelay);
  retryDelay = Math.min(retryDelay * 2, maxRetryDelay);
};

const handleSimulationRound = (event: Event) => {
  const msgEvent = event as MessageEvent;
  const message = safeParse<{
    data?: {
      simulation_id?: string;
      belief_profile?: Record<string, number>;
      trust_network?: { nodes: Array<{ id: string; name: string }> };
    };
  }>(msgEvent.data, 'simulation_round');
  if (!message?.data) return;
  const { simulation_id, belief_profile, trust_network } = message.data;
  if (simulation_id === props.simulationId && belief_profile && trust_network?.nodes) {
    const nodes = trust_network.nodes;
    const profile = belief_profile;
    
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
};

const setupSSE = () => {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`${API_BASE_URL}/api/stream/events`);
  eventSource.addEventListener('simulation_round', handleSimulationRound as EventListener);

  eventSource.onopen = () => {
    retryDelay = 1000;
  };

  eventSource.onerror = (err) => {
    console.error("Belief SSE Connection Failed:", err);
    eventSource?.close();
    eventSource = null;
    scheduleReconnect();
  };
};

onMounted(() => {
  isUnmounted = false;
  setupSSE();
});

onUnmounted(() => {
  isUnmounted = true;
  eventSource?.close();
  if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
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
