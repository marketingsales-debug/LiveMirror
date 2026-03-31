<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import ContagionGraph from '@/visualization/charts/ContagionGraph.vue';
import BeliefEvolutionChart from '@/visualization/charts/BeliefEvolutionChart.vue';
import NarrativeGalaxy from '@/visualization/NarrativeGalaxy.vue';
import DebatePanel from '../components/DebatePanel.vue';
import PlatformHealth from '../components/PlatformHealth.vue';
import PredictionHistory from '../components/PredictionHistory.vue';
import LearningStatsPanel from '../components/LearningStatsPanel.vue';
import MetricsDashboard from '../components/MetricsDashboard.vue';
import SecretsPanel from '../components/SecretsPanel.vue';
import LogsPanel from '../components/LogsPanel.vue';
import ThoughtStream from '../components/ThoughtStream.vue';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const apiUrl = (path: string) => `${API_BASE_URL}${path}`;

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

type Direction = 'BULL' | 'BEAR' | 'NEUTRAL';

interface FusionSignal {
  id: string;
  direction: Direction | string;
  confidence: number;
  modalities: Record<string, unknown>;
}

interface AudienceConsensus {
  direction: number;
  confidence: number;
}

interface TemporalDynamics {
  momentum: number;
  velocity: number;
  acceleration: number;
}

interface PredictionDetails {
  text: string;
  confidence_level: string;
  confidence: number;
  consensus: number;
  bull_score: number;
  bear_score: number;
}

interface DebateDetails {
  direction: Direction | string;
  bull_count: number;
  bear_count: number;
}

interface PredictionReport {
  status: string;
  topic: string;
  prediction: PredictionDetails;
  debate: DebateDetails;
}

// Fusion State
const fusionSignals = ref<FusionSignal[]>([]);
const audienceConsensus = ref<Record<string, AudienceConsensus>>({
  crypto_twitter: { direction: 0, confidence: 0 },
  mainstream_media: { direction: 0, confidence: 0 },
  retail_investors: { direction: 0, confidence: 0 },
  tech_community: { direction: 0, confidence: 0 }
});
const temporalDynamics = ref<TemporalDynamics>({
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
const activePrediction = ref<PredictionReport | null>(null);
const activeView = ref('overview');

let es: EventSource | null = null;
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

const parseEvent = (event: Event, label: string) => {
  const msgEvent = event as MessageEvent;
  const envelope = safeParse<Record<string, unknown>>(msgEvent.data, label);
  if (!envelope) return null;
  // The SSE stream wraps data in {type, data, timestamp} - extract inner data
  return (envelope.data as Record<string, unknown>) ?? envelope;
};

const scheduleReconnect = () => {
  if (reconnectTimer !== null || isUnmounted) return;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectStream();
  }, retryDelay);
  retryDelay = Math.min(retryDelay * 2, maxRetryDelay);
};

const handleIngestionComplete = (e: Event) => {
  const data = parseEvent(e, 'ingestion_complete');
  if (!data) return;
  totalSignals.value += Number(data.total_signals ?? 0);
  latestQuery.value = (data.query as string) || '...';
};

const handleGraphUpdate = (e: Event) => {
  const data = parseEvent(e, 'graph_update');
  if (!data) return;
  totalEntities.value = Number(data.total_entities ?? 0);
};

const handleAnalysisResult = (e: Event) => {
  const data = parseEvent(e, 'analysis_result');
  if (!data) return;
  activeFingerprints.value.unshift({
    id: String(data.signal_id ?? ''),
    name: String(data.fingerprint ?? ''),
    stage: String(data.narrative_stage ?? ''),
    score: Number(data.emotional_velocity ?? 0),
    platform: String(data.platform ?? ''),
    isTipping: Boolean(data.is_tipping_point)
  });
  if (activeFingerprints.value.length > 8) {
    activeFingerprints.value.pop();
  }
};

const handlePredictionNew = async (e: Event) => {
  const data = parseEvent(e, 'prediction_new');
  if (!data || typeof data.prediction_id !== 'string') return;
  try {
    const res = await fetch(apiUrl(`/api/predict/report/${data.prediction_id}`));
    if (res.ok) {
      const report: PredictionReport = await res.json();
      activePrediction.value = report;
    }
  } catch (err) {
    console.error('Failed to load prediction report', err);
  }
};

const handleSimulationRound = (e: Event) => {
  const data = parseEvent(e, 'simulation_round');
  if (!data) return;
  activeSimulationId.value = data.simulation_id as string;
  currentRound.value = Number(data.round_num ?? data.round ?? 0);
  totalRounds.value = Number(data.total_rounds ?? 0);
  roundActions.value = Number(data.actions_this_round ?? data.actions ?? 0);
  isSimulating.value = true;
};

const handleSimulationComplete = (e: Event) => {
  const data = parseEvent(e, 'simulation_complete');
  if (!data) return;
  isSimulating.value = false;
  currentRound.value = Number(data.total_rounds ?? 0);
};

const handleFusionResult = (e: Event) => {
  const data = parseEvent(e, 'fusion_result');
  if (!data) return;
  fusionSignals.value.unshift({
    id: String(data.signal_id ?? ''),
    direction: String(data.direction ?? ''),
    confidence: Number(data.confidence ?? 0),
    modalities: (data.modalities as Record<string, unknown>) ?? {}
  });
  if (fusionSignals.value.length > 5) fusionSignals.value.pop();
};

const handleAudiencePrediction = (e: Event) => {
  const data = parseEvent(e, 'audience_prediction');
  if (!data || typeof data.segment !== 'string') return;
  audienceConsensus.value[data.segment] = {
    direction: Number(data.direction ?? 0) || 0,
    confidence: Number(data.confidence ?? 0) || 0
  };
};

const handleTemporalUpdate = (e: Event) => {
  const data = parseEvent(e, 'temporal_update');
  if (!data) return;
  temporalDynamics.value = {
    momentum: Number(data.momentum ?? 0),
    velocity: Number(data.velocity ?? 0),
    acceleration: Number(data.acceleration ?? 0)
  };
};

const connectStream = () => {
  if (es) es.close();
  es = new EventSource(apiUrl('/api/stream/events'));
  es.addEventListener('ingestion_complete', handleIngestionComplete as EventListener);
  es.addEventListener('graph_update', handleGraphUpdate as EventListener);
  es.addEventListener('analysis_result', handleAnalysisResult as EventListener);
  es.addEventListener('prediction_new', handlePredictionNew as EventListener);
  es.addEventListener('simulation_round', handleSimulationRound as EventListener);
  es.addEventListener('simulation_complete', handleSimulationComplete as EventListener);
  es.addEventListener('fusion_result', handleFusionResult as EventListener);
  es.addEventListener('audience_prediction', handleAudiencePrediction as EventListener);
  es.addEventListener('temporal_update', handleTemporalUpdate as EventListener);

  es.onopen = () => {
    retryDelay = 1000;
  };

  es.onerror = (err) => {
    console.warn('SSE connection error', err);
    es?.close();
    es = null;
    scheduleReconnect();
  };
};


const runIngestion = async () => {
  try {
    const res = await fetch(apiUrl('/api/ingest/start'), { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        topic: topicInput.value, 
        platforms: ['reddit', 'twitter', 'bluesky', 'youtube', 'tiktok', 'instagram', 'hackernews', 'polymarket', 'web', 'news', 'moltbook'] 
      })
    });
    if (!res.ok) throw new Error('Ingestion start failed');
  } catch(err) { console.error('Failed to start ingestion', err); }
};

const runSimulation = async () => {
  if (isSimulating.value) return;
  isSimulating.value = true;
  currentRound.value = 0;
  activePrediction.value = null;
  
  try {
    const res = await fetch(apiUrl('/api/simulate/start'), { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topicInput.value, agent_count: 50, total_rounds: 72 })
    });
    if (!res.ok) throw new Error('Simulation start failed');
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
    const res = await fetch(apiUrl('/api/predict/start'), { 
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
  isUnmounted = false;
  connectStream();
});

onUnmounted(() => {
  isUnmounted = true;
  if (es) es.close();
  if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
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
        <a href="#" :class="{ active: activeView === 'overview' }" @click.prevent="activeView = 'overview'">Overview</a>
        <a href="#" :class="{ active: activeView === 'simulations' }" @click.prevent="activeView = 'simulations'">Simulations</a>
        <a href="#" :class="{ active: activeView === 'entities' }" @click.prevent="activeView = 'entities'">Entities</a>
        <a href="#" :class="{ active: activeView === 'alerts' }" @click.prevent="activeView = 'alerts'">Alerts</a>
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
      
      <!-- Overview: Full Dashboard -->
      <template v-if="activeView === 'overview'">
        <div class="simulation-grid">
          <section class="sim-panel glass-panel">
            <NarrativeGalaxy />
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
          <section class="metrics-panel glass-panel">
            <MetricsDashboard />
          </section>
          <section class="learning-panel glass-panel">
            <LearningStatsPanel />
          </section>
          <section class="side-panel glass-panel">
            <DebatePanel :report="activePrediction" />
          </section>
        </div>
      </template>

      <!-- Simulations View -->
      <template v-if="activeView === 'simulations'">
        <section class="glass-panel full-width-panel">
          <header>
            <h3>Simulation Engine Status</h3>
            <p v-if="isSimulating">Current Round: {{ currentRound }} / {{ totalRounds }}</p>
            <p v-else>No simulation running</p>
          </header>
          <div class="viz-wrapper large">
            <BeliefEvolutionChart :simulationId="activeSimulationId" :round="currentRound" />
          </div>
        </section>
        <div class="grid-2">
          <MetricsDashboard />
          <LearningStatsPanel />
        </div>
      </template>

      <!-- Entities View -->
      <template v-if="activeView === 'entities'">
        <section class="glass-panel full-width-panel galaxy-focus">
          <header>
            <h3>Knowledge Graph Narrative Galaxy</h3>
            <p>3D projection of signal semantic proximity</p>
          </header>
          <NarrativeGalaxy />
        </section>
        <section class="glass-panel full-width-panel contagion-focus">
          <header>
            <h3>Live Contagion Network</h3>
            <p>Signal-to-signal propagation paths</p>
          </header>
          <ContagionGraph />
        </section>
      </template>

      <!-- Alerts View -->
      <template v-if="activeView === 'alerts'">
        <section class="glass-panel alerts-focus">
          <header>
            <h3 :class="{'glow-alert': activeFingerprints.some(f => f.isTipping)}">Narrative Alerts & Tipping Points</h3>
            <p>Active socio-emotional fingerprints exceeding velocity thresholds</p>
          </header>
          <div class="dna-list alerts-grid">
            <div 
              v-for="fp in activeFingerprints" 
              :key="fp.id" 
              class="dna-card alert-card"
              :class="{ 'tipping': fp.isTipping }"
            >
              <div class="alert-header">
                <span class="status-indicator" :class="{ 'tipping': fp.isTipping }"></span>
                <strong>{{ fp.name.replace(/_/g, ' ') }}</strong>
                <span class="platform-badge">{{ fp.platform }}</span>
              </div>
              <p class="alert-desc">Narrative is in the <strong>{{ fp.stage.replace(/_/g, ' ') }}</strong> stage.</p>
              <div class="alert-meta">
                <span class="velocity-tag" :style="{ color: fp.score >= 0 ? 'var(--accent-color)' : '#ff4d4d' }">
                  Velocity: {{ fp.score.toFixed(3) }}
                </span>
                <span v-if="fp.isTipping" class="warning-badge">CRITICAL</span>
              </div>
            </div>
          </div>
          <div v-if="activeFingerprints.length === 0" class="empty-state">
            No active alerts detected at this moment.
          </div>
        </section>
        <section class="metrics-panel glass-panel">
           <h3>System Performance Monitor</h3>
           <MetricsDashboard />
        </section>
      </template>

      <div class="history-row glass-panel logs-row">
        <div class="logs-grid">
          <LogsPanel />
          <div class="vertical-divider"></div>
          <ThoughtStream />
        </div>
      </div>
      <div class="history-row glass-panel">
        <SecretsPanel />
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
.metrics-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.history-row {
  margin-top: 24px;
}

.logs-row {
  padding: 20px 24px;
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

/* New View Layouts */
.full-width-panel {
  padding: 24px;
  width: 100%;
}

.viz-wrapper.large {
  min-height: 500px;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.galaxy-focus {
  height: 600px;
}

.contagion-focus {
  height: 500px;
}

.alerts-focus {
  padding: 24px;
  min-height: 400px;
}

.alerts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 24px;
}

.alert-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1rem;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent-color);
}

.status-indicator.tipping {
  background: #ff4d4d;
  box-shadow: 0 0 8px #ff4d4d;
}

.alert-desc {
  font-size: 0.85rem;
  color: #ccc;
  margin: 0;
}

.alert-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.velocity-tag {
  font-weight: 700;
  font-size: 0.9rem;
}

.warning-badge {
  background: #ff4d4d;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
}
</style>
