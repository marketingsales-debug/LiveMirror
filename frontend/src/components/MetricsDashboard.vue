<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

type Overview = {
  predictions: {
    total: number;
    last_24h: number;
    by_variant?: Record<string, number>;
    variants?: Record<string, { count: number; avg_confidence: number; avg_latency_ms: number }>;
    variant_alerts?: { level: string; message: string }[];
  };
  accuracy: { current: number; trend: string; history: number[] };
  latency: { avg_ms: number; p95_ms: number; target_ms: number };
  cache: { hit_rate: number; hits: number; misses: number };
};

type FineTune = {
  status: string;
  pending_samples: number;
  runs: { total: number; last_7_days: number };
  latest_run: {
    timestamp: string | null;
    samples_used: number;
    pre_accuracy: number;
    post_accuracy: number;
    improvement: number;
  };
  regression: { detected: boolean; rollback_triggered: boolean };
};

type Drift = {
  status: string;
  drift_magnitude: number;
  current_accuracy: number;
  target_accuracy: number;
  alerts: { level: string; message: string }[];
};

const overview = ref<Overview | null>(null);
const fineTune = ref<FineTune | null>(null);
const drift = ref<Drift | null>(null);
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const apiUrl = (path: string) => `${API_BASE_URL}${path}`;
let timer: number | undefined;

const fetchMetrics = async () => {
  try {
    const [o, f, d] = await Promise.all([
      fetch(apiUrl('/api/metrics/overview')),
      fetch(apiUrl('/api/metrics/fine-tune')),
      fetch(apiUrl('/api/metrics/accuracy-drift'))
    ]);
    if (o.ok) overview.value = await o.json();
    if (f.ok) fineTune.value = await f.json();
    if (d.ok) drift.value = await d.json();
  } catch (e) {
    console.error('Failed to fetch metrics', e);
  }
};

onMounted(() => {
  fetchMetrics();
  timer = window.setInterval(fetchMetrics, 15000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <div class="metrics-panel">
    <header>
      <h3>System Metrics</h3>
    </header>

    <div v-if="overview" class="metrics-grid">
      <div class="metric-card">
        <span class="label">Predictions (24h)</span>
        <span class="value">{{ overview.predictions.last_24h }}</span>
        <span class="sub">{{ overview.predictions.total }} total</span>
      </div>
      <div class="metric-card">
        <span class="label">Accuracy</span>
        <span class="value" :class="overview.accuracy.trend">{{ (overview.accuracy.current * 100).toFixed(1) }}%</span>
        <span class="sub">{{ overview.accuracy.trend }}</span>
      </div>
      <div class="metric-card">
        <span class="label">Latency (p95)</span>
        <span class="value">{{ overview.latency.p95_ms.toFixed(1) }}ms</span>
        <span class="sub">Target {{ overview.latency.target_ms }}ms</span>
      </div>
      <div class="metric-card">
        <span class="label">Cache Hit Rate</span>
        <span class="value">{{ (overview.cache.hit_rate * 100).toFixed(1) }}%</span>
        <span class="sub">{{ overview.cache.hits }} hits / {{ overview.cache.misses }} misses</span>
      </div>
    </div>
    <div v-if="overview?.predictions.variants" class="variant-grid">
      <div
        v-for="(stats, variant) in overview.predictions.variants"
        :key="variant"
        class="variant-card"
      >
        <span class="label">Variant</span>
        <span class="value">{{ variant }}</span>
        <span class="sub">{{ stats.count }} predictions</span>
        <span class="sub">Avg conf: {{ (stats.avg_confidence * 100).toFixed(1) }}%</span>
        <span class="sub">Avg latency: {{ stats.avg_latency_ms.toFixed(1) }}ms</span>
      </div>
    </div>
    <div v-if="overview?.predictions.variant_alerts?.length" class="alerts">
      <div
        v-for="(a, idx) in overview.predictions.variant_alerts"
        :key="idx"
        class="alert"
        :class="a.level"
      >
        {{ a.message }}
      </div>
    </div>

    <div v-if="fineTune" class="fine-tune">
      <h4>Fine-Tune Loop</h4>
      <div class="fine-grid">
        <div class="fine-card">
          <span class="label">Runs (7d)</span>
          <span class="value">{{ fineTune.runs.last_7_days }}</span>
          <span class="sub">{{ fineTune.runs.total }} total</span>
        </div>
        <div class="fine-card">
          <span class="label">Latest Improvement</span>
          <span class="value">{{ (fineTune.latest_run.improvement * 100).toFixed(2) }}%</span>
          <span class="sub">{{ fineTune.latest_run.samples_used }} samples</span>
        </div>
        <div class="fine-card">
          <span class="label">Regression</span>
          <span class="value" :class="{ bad: fineTune.regression.detected }">
            {{ fineTune.regression.detected ? 'Detected' : 'None' }}
          </span>
          <span class="sub">{{ fineTune.regression.rollback_triggered ? 'Rollback' : 'Healthy' }}</span>
        </div>
      </div>
    </div>

    <div v-if="drift" class="drift">
      <h4>Accuracy Drift</h4>
      <div class="drift-row">
        <span class="value" :class="drift.status">{{ drift.status.replace('_', ' ') }}</span>
        <span class="sub">{{ (drift.drift_magnitude * 100).toFixed(2) }}% vs baseline</span>
      </div>
      <div v-if="drift.alerts.length" class="alerts">
        <div v-for="(a, idx) in drift.alerts" :key="idx" class="alert" :class="a.level">
          {{ a.message }}
        </div>
      </div>
    </div>

    <div v-if="!overview && !fineTune && !drift" class="empty">
      Metrics unavailable. Run a prediction to populate data.
    </div>
  </div>
</template>

<style scoped>
.metrics-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}
header h3 {
  margin: 0;
  color: var(--text-highlight);
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.variant-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.variant-card {
  background: rgba(0,0,0,0.2);
  padding: 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.metric-card, .fine-card {
  background: rgba(0,0,0,0.2);
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label {
  font-size: 0.7rem;
  text-transform: uppercase;
  opacity: 0.7;
}
.value {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--accent-color);
}
.value.improving { color: var(--accent-color); }
.value.degrading, .value.critical_drift { color: #ff4d4d; }
.value.mild_drift { color: #ffb74d; }
.value.stable { color: var(--text-highlight); }
.value.bad { color: #ff4d4d; }
.sub {
  font-size: 0.75rem;
  opacity: 0.6;
}
.fine-tune h4, .drift h4 {
  margin: 4px 0 0;
  font-size: 0.85rem;
  color: var(--text-highlight);
}
.fine-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 8px;
}
.drift-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0,0,0,0.2);
  padding: 12px 16px;
  border-radius: 8px;
}
.alerts {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
}
.alert.warning {
  background: rgba(255, 183, 77, 0.15);
  color: #ffb74d;
}
.alert.critical {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
}
.empty {
  opacity: 0.6;
  font-size: 0.85rem;
  padding: 16px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  text-align: center;
}
</style>
