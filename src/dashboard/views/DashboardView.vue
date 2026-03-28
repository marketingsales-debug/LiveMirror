<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import ContagionGraph from '@livemirror/visualization/charts/ContagionGraph.vue';
import TrustNetworkGraph from '@livemirror/visualization/charts/TrustNetworkGraph.vue';
import BeliefEvolutionChart from '@livemirror/visualization/charts/BeliefEvolutionChart.vue';

// Reactive State
const totalSignals = ref(0);
const totalEntities = ref(0);
const latestQuery = ref('...');

// Simulation State
const isSimulating = ref(false);
const activeSimulationId = ref<string | null>(null);
const currentRound = ref(0);
const totalRounds = ref(0);
const roundActions = ref(0);

interface Fingerprint {
  id: string;
  name: string;
  stage: string;
  score: number;
  platform: string;
  isTipping: boolean;
}

const activeFingerprints = ref<Fingerprint[]>([]);
let es: EventSource | null = null;

const runSimulation = async () => {
  if (isSimulating.value) return;
  isSimulating.value = true;
  currentRound.value = 0;
  
  // Call backend to start
  try {
    const res = await fetch('http://localhost:5001/api/simulation/start', { method: 'POST' });
    const data = await res.json();
    activeSimulationId.value = data.simulation_id;
  } catch(err) {
    console.error('Failed to start sim', err);
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
    } catch(err) {}
  }) as EventListener);

  es.addEventListener('graph_update', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      totalEntities.value = data.total_entities || 0;
    } catch(err) {}
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
    } catch(err) {}
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
    } catch(err) {}
  }) as EventListener);

  es.addEventListener('simulation_complete', ((e: Event) => {
    try {
      const msgEvent = e as MessageEvent;
      const data = JSON.parse(msgEvent.data);
      isSimulating.value = false;
      currentRound.value = data.total_rounds;
    } catch(err) {}
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
        <button class="primary-btn" @click="runSimulation" :disabled="isSimulating">
          {{ isSimulating ? 'Simulating...' : 'Run Simulation' }}
        </button>
      </div>
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
      </div>
    </main>
  </div>
</template>

<style scoped>
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
</style>
