<script setup lang="ts">
import { ref, onMounted } from 'vue';

const stats = ref<{
  total_validations: number;
  avg_accuracy: number;
  calibration_offset: number;
} | null>(null);

const fetchStats = async () => {
  try {
    const res = await fetch('http://localhost:5001/api/predict/learning');
    if (res.ok) {
      stats.value = await res.json();
    }
  } catch(e) { console.error('Failed to fetch learning stats', e); }
};

onMounted(() => {
  fetchStats();
  setInterval(fetchStats, 15000);
});
</script>

<template>
  <div class="learning-stats">
    <header>
      <h3>Engine Learning Loop</h3>
    </header>
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <span class="label">Validations</span>
        <span class="value">{{ stats.total_validations }}</span>
      </div>
      <div class="stat-card">
        <span class="label">Accuracy</span>
        <span class="value" :class="{
          good: stats.avg_accuracy >= 0.7,
          warn: stats.avg_accuracy >= 0.5 && stats.avg_accuracy < 0.7,
          bad: stats.avg_accuracy < 0.5
        }">
          {{ (stats.avg_accuracy * 100).toFixed(1) }}%
        </span>
      </div>
      <div class="stat-card">
        <span class="label">Calibration Offset</span>
        <span class="value">{{ stats.calibration_offset > 0 ? '+' : '' }}{{ stats.calibration_offset.toFixed(3) }}</span>
      </div>
    </div>
    <div v-else class="empty">
      No learning data yet. Validate a prediction.
    </div>
  </div>
</template>

<style scoped>
.learning-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}
header h3 {
  margin: 0;
  color: var(--text-highlight);
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.stat-card {
  background: rgba(0,0,0,0.2);
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.label {
  font-size: 0.75rem;
  text-transform: uppercase;
  opacity: 0.7;
  margin-bottom: 8px;
}
.value {
  font-size: 1.5rem;
  font-weight: 600;
}
.value.good { color: var(--accent-color); }
.value.warn { color: #ffb74d; }
.value.bad { color: #ff4d4d; }
.empty {
  opacity: 0.5;
  font-size: 0.85rem;
  padding: 16px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  text-align: center;
}
</style>
