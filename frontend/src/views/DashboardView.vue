<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import ContagionGraph from '@livemirror/visualization/charts/ContagionGraph.vue';
import TrustNetworkGraph from '@livemirror/visualization/charts/TrustNetworkGraph.vue';
import BeliefEvolutionChart from '@livemirror/visualization/charts/BeliefEvolutionChart.vue';
import DebatePanel from '../components/DebatePanel.vue';
import PlatformHealth from '../components/PlatformHealth.vue';
import PredictionHistory from '../components/PredictionHistory.vue';
import LearningStatsPanel from '../components/LearningStatsPanel.vue';

// Reactive State
const topicInput = ref('AI Regulation');
const totalSignals = ref(0);
const totalEntities = ref(0);
const latestQuery = ref('...');

// Simulation State
const isSimulating = ref(false);
const activeSimulationId = ref<string | null>(null);
const currentRound = ref(0);
const totalRounds = ref(0);
const roundActions = ref(0);

// Fusion State
const fusionSignals = ref<any[]>([]);
const audienceConsensus = ref<Record<string, any>>({
  crypto_twitter: { direction: 0, confidence: 0 },
  mainstream_media: { direction: 0, confidence: 0 },
  retail_investors: { direction: 0, confidence: 0 },
  tech_community: { direction: 0, confidence: 0 }
});
const temporalDynamics = ref({
  momentum: 0,
  velocity: 0,
  acceleration: 0
});

interface Fingerprint {
  id: string;
  name: string;
  stage: string;
  score: number;
  platform: string;
  isTipping: boolean;
}

const activeFingerprints = ref<Fingerprint[]>([]);
const activePrediction = ref<Record<string, unknown> | null>(null);
let es: EventSource | null = null;


const runIngestion = async () => {
  try {
    await fetch('http://localhost:5001/api/ingest/start', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topicInput.value, platforms: ['reddit', 'hackernews', 'polymarket', 'web_search'] })
    });
  } catch(err) { console.error('Failed to start ingestion', err); }
};

const runSimulation = async () => {
  if (isSimulating.value) return;
  isSimulating.value = true;
  currentRound.value = 0;
  activePrediction.value = null;
  
  try {
    const res = await fetch('http://localhost:5001/api/simulate/start', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topicInput.value, agent_count: 50, total_rounds: 72 })
    });
    const data = await res.json();
    activeSimulationId.value = data.simulation_id;
  } catch(err) {
    console.error('Failed to start sim', err);
    isSimulating.value = false;
  }
};

const runPrediction = async () => {
  if (isSimulating.value) return;
  isSimulating.value = true;
  currentRound.value = 0;
  activePrediction.value = null;

  try {
    const res = await fetch('http://localhost:5001/api/predict/start', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topicInput.value, agent_count: 50, simulation_rounds: 72 })
    });
    if (!res.ok) throw new Error('Prediction start failed');
  } catch(err) {
    console.error('Failed to start prediction', err);
    isSimulating.value = false;
  }

};

onMounted(() => {
  es = new EventSource('http://localhost:5001/api/stream/events');

  es.addEventListener('ingestion_complete', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      totalSignals.value += data.total_signals || 0;
      latestQuery.value = data.query || '...';
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('graph_update', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      totalEntities.value = data.total_entities || 0;
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('analysis_result', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      activeFingerprints.value.unshift({
        id: data.signal_id,
        name: data.fingerprint,
        stage: data.narrative_stage,
        score: data.emotional_velocity,
        platform: data.platform,
        isTipping: data.is_tipping_point
      });
      if (activeFingerprints.value.length > 8) {
        activeFingerprints.value.pop();
      }
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('prediction_new', (async (e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      // Fetch full debate report
      const res = await fetch(`http://localhost:5001/api/predict/report/${data.prediction_id}`);
      if (res.ok) {
        activePrediction.value = await res.json();
      }
    } catch(err) { console.error('Failed to load prediction report', err); }
  }) as EventListener);

  // Phase 3 Simulation Listeners
  es.addEventListener('simulation_round', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      activeSimulationId.value = data.simulation_id;
      currentRound.value = data.round_num || data.round;
      totalRounds.value = data.total_rounds;
      roundActions.value = data.actions_this_round || data.actions;
      isSimulating.value = true;
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('simulation_complete', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      isSimulating.value = false;
      currentRound.value = data.total_rounds;
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('fusion_result', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      fusionSignals.value.unshift({
        id: data.signal_id,
        direction: data.direction,
        confidence: data.confidence,
        modalities: data.modalities
      });
      if (fusionSignals.value.length > 5) fusionSignals.value.pop();
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('audience_prediction', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      audienceConsensus.value[data.segment] = {
        direction: data.direction,
        confidence: data.confidence
      };
    } catch { /* ignore */ }
  }) as EventListener);

  es.addEventListener('temporal_update', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      temporalDynamics.value = {
        momentum: data.momentum,
        velocity: data.velocity,
        acceleration: data.acceleration
      };
    } catch { /* ignore */ }
  }) as EventListener);
});

onUnmounted(() => {
  if (es) es.close();
});
</script>

<template>
  <div class="dashboard">
    <aside class="sidebar glass-panel">
      <div class="logo">
        <h2>LiveMirror</h2>
        <div class="badge flashing" v-if="activeFingerprints.some(f => f.isTipping)">⚠️ TIPPING POINT</div>
        <div class="badge" v-else-if="isSimulating">🧬 SIMULATING ({{ currentRound }}/{{ totalRounds }})</div>
        <div class="badge" v-else>LIVE STATUS</div>
      </div>
      <nav>
        <a href="#" class="active">Overview</a>
        <a href="#">Simulations</a>
        <a href="#">Entities</a>
        <a href="#">Alerts</a>
      </nav>
      <div class="actions">
        <input v-model="topicInput" placeholder="Enter topic..." class="topic-input" />
        <button class="secondary-btn" @click="runIngestion">Ingest Data</button>
        <button class="secondary-btn" @click="runSimulation" :disabled="isSimulating">Run Simulation</button>
        <button class="primary-btn" @click="runPrediction" :disabled="isSimulating">
          {{ isSimulating ? 'Running...' : 'Full Prediction' }}
        </button>
      </div>
      <PlatformHealth />
    </aside>
    <main class="main-content">
      <header class="top-nav glass-panel">
        <div class="stats">
          <div class="stat">Signals processed: <span>{{ totalSignals }}</span></div>
          <div class="stat">Graph entities: <span>{{ totalEntities }}</span></div>
          <div class="stat">Actions this round: <span class="accent">{{ roundActions }}</span></div>
        </div>
      </header>
      
      <!-- Simulation Row -->
      <div class="simulation-grid">
        <section class="sim-panel glass-panel">
          <header>
            <h3>Trust Network</h3>
            <p>D3 force physics edge topology</p>
          </header>
          <div class="viz-wrapper">
            <TrustNetworkGraph :simulationId="activeSimulationId" :round="currentRound" />
          </div>
        </section>
        <section class="sim-panel glass-panel">
          <header>
            <h3>Belief Evolution</h3>
            <p>Agent sentiment trajectory convergence</p>
          </header>
          <div class="viz-wrapper">
            <BeliefEvolutionChart :simulationId="activeSimulationId" :round="currentRound" />
          </div>
        </section>
      </div>

      <!-- Fusion Analysis Row -->
      <div class="fusion-grid">
        <section class="fusion-panel glass-panel">
          <header>
            <h3>Multimodal Audience Consensus</h3>
            <p>TRIBE v2 Segment-Specific Predictions</p>
          </header>
          <div class="audience-grid">
            <div v-for="(stats, segment) in audienceConsensus" :key="segment" class="audience-card">
              <div class="segment-name">{{ segment.replace(/_/g, ' ') }}</div>
              <div class="segment-viz">
                <div class="direction-bar">
                  <div class="bar-fill" :style="{ 
                    width: Math.abs(stats.direction * 100) + '%',
                    left: stats.direction >= 0 ? '50%' : 'auto',
                    right: stats.direction < 0 ? '50%' : 'auto',
                    background: stats.direction >= 0 ? 'var(--accent-color)' : '#ff4d4d'
                  }"></div>
                </div>
              </div>
              <div class="segment-meta">
                <span>{{ stats.direction >= 0 ? 'BULL' : 'BEAR' }}</span>
                <span>{{ (stats.confidence * 100).toFixed(0) }}% CONF</span>
              </div>
            </div>
          </div>
        </section>
        <section class="fusion-panel glass-panel">
          <header>
            <h3>Temporal Dynamics</h3>
            <p>Momentum, Velocity & Acceleration</p>
          </header>
          <div class="temporal-stats">
            <div class="t-stat">
              <label>MOMENTUM</label>
              <div class="value">{{ temporalDynamics.momentum.toFixed(3) }}</div>
            </div>
            <div class="t-stat">
              <label>VELOCITY</label>
              <div class="value">{{ temporalDynamics.velocity.toFixed(3) }}</div>
            </div>
            <div class="t-stat">
              <label>ACCELERATION</label>
              <div class="value">{{ temporalDynamics.acceleration.toFixed(3) }}</div>
            </div>
          </div>
        </section>
      </div>

      <div class="content-grid">
        <section class="main-chart glass-panel">
          <header>
            <h3 :class="{'glow-alert': activeFingerprints.some(f => f.isTipping)}">Live Contagion Network</h3>
            <p>Real-time cascade prediction</p>
          </header>
          <div class="chart-container">
            <ContagionGraph />
          </div>
        </section>
        <section class="side-panel glass-panel">
          <header>
            <h3>Narrative DNA</h3>
          </header>
          <div class="dna-list">
            <div 
              v-for="fp in activeFingerprints" 
              :key="fp.id" 
              class="dna-card"
              :class="{ 'tipping': fp.isTipping }"
            >
              <div class="dna-header">
                <strong>{{ fp.name.replace(/_/g, ' ') }}</strong>
                <span class="platform-badge">{{ fp.platform }}</span>
              </div>
              <div class="dna-details">
                <span class="stage">{{ fp.stage.replace(/_/g, ' ') }}</span>
                <span class="sentiment" :style="{ color: fp.score >= 0 ? 'var(--accent-color)' : '#ff4d4d' }">
                  Velocity: {{ fp.score.toFixed(2) }}
                </span>
              </div>
            </div>
            <div v-if="activeFingerprints.length === 0" class="empty-state">
              Waiting for analysis signals...
            </div>
          </div>
        </section>
        <section class="learning-panel glass-panel">
          <LearningStatsPanel />
        </section>
        <section class="side-panel glass-panel">
          <DebatePanel :report="activePrediction" />
        </section>
      </div>
      <div class="history-row glass-panel">
        <PredictionHistory />
      </div>
    </main>
  </div>
</template>

<style scoped>
.topic-input {
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(102, 252, 241, 0.3);
  color: white;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 12px;
  outline: none;
  font-family: inherit;
}
.topic-input:focus {
  border-color: var(--accent-color);
}
.secondary-btn {
  background: rgba(255,255,255,0.05);
  color: var(--text-highlight);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  margin-bottom: 8px;
  transition: all 0.2s;
}
.secondary-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.1);
  border-color: rgba(255,255,255,0.2);
}
.secondary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.dashboard {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: 100vh;
  gap: 20px;
  padding: 20px;
  box-sizing: border-box;
}

.sidebar {
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.logo h2 {
  color: var(--text-highlight);
  margin: 0 0 8px 0;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.badge {
  background: rgba(102, 252, 241, 0.1);
  color: var(--accent-color);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  display: inline-block;
  margin-bottom: 32px;
  transition: all 0.3s;
}

.badge.flashing {
  background: rgba(255, 77, 77, 0.2);
  color: #ff4d4d;
  animation: pulse 1s infinite alternate;
}

.actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
}

.primary-btn {
  background: var(--accent-color);
  color: #0b0c10;
  border: none;
  padding: 12px 16px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes pulse {
  0% { opacity: 0.7; box-shadow: 0 0 5px rgba(255, 77, 77, 0.4); }
  100% { opacity: 1; box-shadow: 0 0 15px rgba(255, 77, 77, 0.8); }
}

nav {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

nav a {
  color: var(--text-primary);
  text-decoration: none;
  padding: 12px 16px;
  border-radius: 8px;
  transition: all 0.2s ease;
  font-weight: 500;
}

nav a:hover, nav a.active {
  background: rgba(102, 252, 241, 0.05);
  color: var(--accent-color);
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.top-nav {
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats {
  display: flex;
  gap: 24px;
  font-size: 0.9rem;
}

.stats span {
  color: var(--text-highlight);
  font-weight: 600;
  margin-left: 8px;
}

.stats .accent {
  color: var(--accent-color);
}

.simulation-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.sim-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
  min-height: 350px;
}

.sim-panel header h3 {
  margin: 0;
  color: var(--text-highlight);
}

.sim-panel header p {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  opacity: 0.7;
}

.viz-wrapper {
  flex: 1;
  margin-top: 16px;
  position: relative;
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  flex: 1;
}

.learning-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.history-row {
  margin-top: 24px;
}

.main-chart {
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.main-chart header h3 {
  margin: 0;
  color: var(--text-highlight);
  transition: color 0.3s, text-shadow 0.3s;
}

.glow-alert {
  color: #ff4d4d !important;
  text-shadow: 0 0 10px rgba(255, 77, 77, 0.6);
}

.main-chart header p {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  opacity: 0.7;
}

.chart-container {
  flex: 1;
  margin-top: 24px;
  position: relative;
  min-height: 400px;
}

.side-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
  min-height: 400px;
}

.side-panel h3 {
  margin: 0 0 16px 0;
  color: var(--text-highlight);
}

.dna-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.dna-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.3s;
}

.dna-card.tipping {
  border-color: #ff4d4d;
  box-shadow: 0 0 10px rgba(255, 77, 77, 0.2);
}

.dna-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  text-transform: capitalize;
  font-size: 0.9rem;
  color: var(--text-highlight);
}

.platform-badge {
  font-size: 0.7rem;
  opacity: 0.6;
  text-transform: uppercase;
}

.dna-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  opacity: 0.9;
}

.stage {
  color: #b3b3b3;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.5px;
}

.empty-state {
  text-align: center;
  font-size: 0.85rem;
  opacity: 0.5;
  margin-top: 40px;
}

/* Fusion Styles */
.fusion-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.fusion-panel {
  padding: 24px;
}

.audience-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 20px;
}

.audience-card {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.segment-name {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-highlight);
  margin-bottom: 12px;
  letter-spacing: 1px;
}

.direction-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  position: relative;
  margin-bottom: 8px;
}

.bar-fill {
  height: 100%;
  position: absolute;
  border-radius: 3px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.segment-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  font-weight: 600;
  opacity: 0.8;
}

.temporal-stats {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 20px;
}

.t-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.t-stat label {
  font-size: 0.7rem;
  letter-spacing: 1px;
  opacity: 0.6;
}

.t-stat .value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.2rem;
  color: var(--accent-color);
  font-weight: 700;
}
</style>
