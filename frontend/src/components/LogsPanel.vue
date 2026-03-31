<template>
  <div class="logs-panel">
    <header class="logs-header">
      <h3>System Logs</h3>
      <div class="logs-controls">
        <select v-model="levelFilter" class="level-select">
          <option value="">ALL</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="INFO">INFO</option>
          <option value="DEBUG">DEBUG</option>
        </select>
        <label class="auto-scroll-label">
          <input type="checkbox" v-model="autoScroll" /> Auto-scroll
        </label>
        <button class="clear-btn" @click="clearLogs">Clear</button>
      </div>
    </header>
    <div class="logs-body" ref="logsContainer">
      <div v-if="filteredLogs.length === 0" class="empty">No logs yet. Interact with the dashboard to generate logs.</div>
      <div
        v-for="(log, i) in filteredLogs"
        :key="i"
        class="log-entry"
        :class="log.level.toLowerCase()"
      >
        <span class="log-ts">{{ formatTs(log.ts) }}</span>
        <span class="log-level" :class="log.level.toLowerCase()">{{ log.level }}</span>
        <span class="log-source">{{ log.logger }}</span>
        <span class="log-msg">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

interface LogEntry {
  ts: string;
  level: string;
  logger: string;
  message: string;
}

const logs = ref<LogEntry[]>([]);
const levelFilter = ref('');
const autoScroll = ref(true);
const logsContainer = ref<HTMLElement | null>(null);
let es: EventSource | null = null;

const filteredLogs = computed(() => {
  if (!levelFilter.value) return logs.value;
  return logs.value.filter(l => l.level === levelFilter.value);
});

const formatTs = (iso: string) => {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso;
  }
};

const scrollToBottom = () => {
  if (autoScroll.value && logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
  }
};

const clearLogs = () => {
  logs.value = [];
};

watch(filteredLogs, () => {
  nextTick(scrollToBottom);
});

const fetchInitialLogs = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/logs?limit=200`);
    if (res.ok) {
      const data = await res.json();
      logs.value = data.logs ?? [];
    }
  } catch (err) {
    console.warn('Failed to fetch initial logs', err);
  }
};

const connectStream = () => {
  if (es) es.close();
  es = new EventSource(`${API_BASE_URL}/api/logs/stream`);
  es.onmessage = (event) => {
    try {
      const entry: LogEntry = JSON.parse(event.data);
      logs.value.push(entry);
      if (logs.value.length > 500) {
        logs.value = logs.value.slice(-400);
      }
    } catch {
      // ignore parse errors
    }
  };
  es.onerror = () => {
    es?.close();
    es = null;
    setTimeout(connectStream, 3000);
  };
};

onMounted(async () => {
  await fetchInitialLogs();
  connectStream();
});

onUnmounted(() => {
  if (es) es.close();
});
</script>

<style scoped>
.logs-panel {
  display: flex;
  flex-direction: column;
  max-height: 400px;
  min-height: 250px;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.logs-header h3 {
  margin: 0;
  color: var(--text-highlight, #e6f1ff);
  font-size: 1rem;
}

.logs-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.level-select {
  background: rgba(0,0,0,0.4);
  border: 1px solid rgba(255,255,255,0.15);
  color: #ccc;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  outline: none;
}

.auto-scroll-label {
  font-size: 0.75rem;
  color: #888;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.clear-btn {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
  border: 1px solid rgba(255, 77, 77, 0.3);
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}
.clear-btn:hover {
  background: rgba(255, 77, 77, 0.3);
}

.logs-body {
  flex: 1;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 8px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.72rem;
  line-height: 1.6;
}

.logs-body::-webkit-scrollbar {
  width: 6px;
}
.logs-body::-webkit-scrollbar-track {
  background: transparent;
}
.logs-body::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 3px;
}

.empty {
  color: #555;
  text-align: center;
  padding: 40px 0;
  font-style: italic;
}

.log-entry {
  display: flex;
  gap: 8px;
  padding: 2px 4px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
}

.log-entry:hover {
  background: rgba(255,255,255,0.03);
}

.log-entry.error {
  background: rgba(255, 77, 77, 0.08);
}

.log-entry.warning {
  background: rgba(255, 193, 7, 0.06);
}

.log-ts {
  color: #555;
  flex-shrink: 0;
  min-width: 64px;
}

.log-level {
  flex-shrink: 0;
  min-width: 56px;
  font-weight: 700;
  text-transform: uppercase;
}
.log-level.error { color: #ff4d4d; }
.log-level.warning { color: #ffc107; }
.log-level.info { color: var(--accent-color, #66fcf1); }
.log-level.debug { color: #666; }

.log-source {
  color: #7c8db0;
  flex-shrink: 0;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-msg {
  color: #ccc;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
