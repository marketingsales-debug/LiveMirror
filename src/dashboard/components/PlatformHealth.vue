<script setup lang="ts">
import { ref, onMounted } from 'vue';

const healthData = ref<Record<string, { status: string; latency_ms: number; last_check: string }> | null>(null);

const fetchHealth = async () => {
  try {
    const res = await fetch('http://localhost:5001/api/ingest/health');
    if (res.ok) {
      const data = await res.json();
      healthData.value = data.platforms;
    }
  } catch(e) { console.error('Failed to fetch platform health', e); }
};

onMounted(() => {
  fetchHealth();
  setInterval(fetchHealth, 30000); // 30s polling
});
</script>

<template>
  <div class="platform-health">
    <header>
      <h4>Platform Health</h4>
    </header>
    <div class="grid" v-if="healthData">
      <div v-for="(info, platform) in healthData" :key="platform" class="platform-item">
        <span class="dot" :class="info.status"></span>
        <span class="name">{{ platform }}</span>
      </div>
    </div>
    <div v-else class="loading">Checking platforms...</div>
  </div>
</template>

<style scoped>
.platform-health {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
header h4 {
  margin: 0 0 12px 0;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.6;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.platform-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
}
.name {
  text-transform: capitalize;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #aaa;
}
.dot.ok { background: #66fcf1; box-shadow: 0 0 4px #66fcf1; }
.dot.error { background: #ff4d4d; box-shadow: 0 0 4px #ff4d4d; }
.loading {
  font-size: 0.8rem;
  opacity: 0.5;
}
</style>
