<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

interface Thought {
  id: string;
  message: string;
  step: string;
  timestamp: string;
}

const thoughts = ref<Thought[]>([]);
const streamActive = ref(false);
const streamStatusText = ref('Connecting...');
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
let reconnectTimer: number | null = null;
let retryDelay = 1000;
const maxRetryDelay = 30000;
let isUnmounted = false;

// Connect to the global SSE stream
let eventSource: EventSource | null = null;

onMounted(() => {
  isUnmounted = false;
  connectStream();
});

onUnmounted(() => {
  isUnmounted = true;
  if (eventSource) eventSource.close();
  if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
});

function connectStream() {
  if (eventSource) eventSource.close();
  const url = `${API_BASE_URL}/api/stream/events`;
  eventSource = new EventSource(url);

  eventSource.addEventListener('agent_thought', (event: MessageEvent) => {
    const payload = safeParse<{ data: Thought; timestamp: string }>(event.data, 'agent_thought');
    if (!payload?.data) return;
    thoughts.value.unshift({
      id: Math.random().toString(36).substr(2, 9),
      message: payload.data.message,
      step: payload.data.step,
      timestamp: payload.timestamp
    });
    streamActive.value = true;
    streamStatusText.value = 'Live';
  });

  eventSource.onopen = () => {
    retryDelay = 1000;
    streamActive.value = true;
    streamStatusText.value = 'Live';
  };

  eventSource.onerror = (err) => {
    console.warn('Thought stream SSE error', err);
    streamActive.value = false;
    streamStatusText.value = 'Reconnecting...';
    eventSource?.close();
    eventSource = null;
    scheduleReconnect();
  };
}

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
    connectStream();
  }, retryDelay);
  retryDelay = Math.min(retryDelay * 2, maxRetryDelay);
};

const getStepColor = (step: string) => {
  switch (step) {
    case 'received': return 'text-blue-400 border-blue-400';
    case 'context': return 'text-purple-400 border-purple-400';
    case 'thinking': return 'text-yellow-400 border-yellow-400';
    case 'action': return 'text-green-400 border-green-400';
    default: return 'text-gray-400 border-gray-400';
  }
};
</script>

<template>
  <div class="thought-stream h-full flex flex-col bg-slate-900 text-slate-100 p-4 font-mono text-sm border-l border-slate-700">
    <div class="flex items-center justify-between mb-4 border-b border-slate-700 pb-2">
      <h3 class="text-lg font-bold flex items-center gap-2">
        <span class="relative flex h-3 w-3">
          <span :class="['animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', streamActive ? 'bg-green-400' : 'bg-red-400']"></span>
          <span :class="['relative inline-flex rounded-full h-3 w-3', streamActive ? 'bg-green-500' : 'bg-red-500']"></span>
        </span>
        Autonomous Thought Stream
      </h3>
      <div class="text-xs text-slate-500 flex items-center gap-2">
        <span>{{ streamStatusText }}</span>
        <span>{{ thoughts.length }} events</span>
      </div>
    </div>

    <div class="overflow-y-auto flex-grow space-y-4 pr-2 custom-scrollbar">
      <div v-if="thoughts.length === 0" class="text-slate-600 italic text-center py-10">
        Waiting for agent activity...
      </div>
      
      <div v-for="thought in thoughts" :key="thought.id" 
           class="thought-card p-3 rounded bg-slate-800 border-l-4 shadow-lg transition-all hover:bg-slate-750"
           :class="getStepColor(thought.step)">
        <div class="flex justify-between items-start mb-1">
          <span class="text-xs uppercase font-bold tracking-wider opacity-60">{{ thought.step }}</span>
          <span class="text-[10px] opacity-40">{{ new Date(thought.timestamp).toLocaleTimeString() }}</span>
        </div>
        <p class="whitespace-pre-wrap leading-relaxed">{{ thought.message }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.thought-card {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 10px;
}
</style>
