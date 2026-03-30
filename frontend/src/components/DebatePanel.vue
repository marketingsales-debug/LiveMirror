<script setup lang="ts">
import { computed } from 'vue';

type Direction = 'BULL' | 'BEAR' | 'NEUTRAL';

interface PredictionDetails {
  text: string;
  confidence_level: string;
  confidence: number;
  consensus: number;
  bull_score: number;
  bear_score: number;
}

interface DebateDetails {
  direction: Direction;
  bull_count: number;
  bear_count: number;
}

interface PredictionReport {
  status: string;
  topic: string;
  prediction: PredictionDetails;
  debate: DebateDetails;
}

const emptyPrediction: PredictionDetails = {
  text: '',
  confidence_level: '',
  confidence: 0,
  consensus: 0,
  bull_score: 0,
  bear_score: 0
};

const emptyDebate: DebateDetails = {
  direction: 'NEUTRAL',
  bull_count: 0,
  bear_count: 0
};

const props = defineProps<{
  report: PredictionReport | null;
}>();

const hasData = computed(() => props.report?.status === 'completed');
const p = computed<PredictionDetails>(() => props.report?.prediction ?? emptyPrediction);
const d = computed<DebateDetails>(() => props.report?.debate ?? emptyDebate);

const bullPct = computed(() => {
  if (!hasData.value) return 50;
  const total = p.value.bull_score + p.value.bear_score;
  if (total === 0) return 50;
  return (p.value.bull_score / total) * 100;
});
</script>

<template>
  <div class="debate-panel">
    <header>
      <h3>Agent Debate Consensus</h3>
      <p v-if="hasData">Topic: {{ report.topic }}</p>
      <p v-else>Waiting for prediction pipeline...</p>
    </header>

    <div v-if="hasData" class="results">
      <div class="prediction-text">
        "{{ p.text }}"
      </div>

      <div class="metrics">
        <div class="metric">
          <span class="label">Direction</span>
          <span class="value direction" :class="d.direction.toLowerCase()">
            {{ d.direction }}
          </span>
        </div>
        <div class="metric">
          <span class="label">Confidence</span>
          <span class="value">{{ p.confidence_level }} ({{ (p.confidence * 100).toFixed(1) }}%)</span>
        </div>
        <div class="metric">
          <span class="label">Consensus Score</span>
          <span class="value">{{ p.consensus.toFixed(2) }}</span>
        </div>
      </div>

      <div class="tug-of-war">
        <div class="labels">
          <span class="bull">BULL ({{ d.bull_count }} agents)</span>
          <span class="bear">BEAR ({{ d.bear_count }} agents)</span>
        </div>
        <div class="bar">
          <div class="fill bull-fill" :style="{ width: bullPct + '%' }"></div>
        </div>
        <div class="scores">
          <span>Score: {{ p.bull_score.toFixed(1) }}</span>
          <span>Score: {{ p.bear_score.toFixed(1) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.debate-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

header h3 {
  margin: 0;
  color: var(--text-highlight);
}

header p {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  opacity: 0.7;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.prediction-text {
  font-size: 1.1rem;
  font-style: italic;
  padding: 16px;
  background: rgba(102, 252, 241, 0.05);
  border-left: 4px solid var(--accent-color);
  border-radius: 4px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric {
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.2);
  padding: 12px;
  border-radius: 8px;
}

.label {
  font-size: 0.75rem;
  text-transform: uppercase;
  opacity: 0.7;
  margin-bottom: 4px;
}

.value {
  font-weight: 600;
  font-size: 1.1rem;
}

.direction.bull { color: var(--accent-color); }
.direction.bear { color: #ff4d4d; }
.direction.neutral { color: #aaa; }

.tug-of-war {
  margin-top: 8px;
}

.labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 8px;
}

.bull { color: var(--accent-color); }
.bear { color: #ff4d4d; }

.bar {
  height: 12px;
  background: #ff4d4d; /* base is bear */
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.fill.bull-fill {
  height: 100%;
  background: var(--accent-color);
  transition: width 0.5s ease;
}

.scores {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  opacity: 0.7;
  margin-top: 4px;
}
</style>
