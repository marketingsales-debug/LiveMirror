<script setup lang="ts">
import ContagionGraph from '@livemirror/visualization/charts/ContagionGraph.vue';
</script>

<template>
  <div class="dashboard">
    <aside class="sidebar glass-panel">
      <div class="logo">
        <h2>LiveMirror</h2>
        <div class="badge">LIVE STATUS</div>
      </div>
      <nav>
        <a href="#" class="active">Overview</a>
        <a href="#">Simulations</a>
        <a href="#">Entities</a>
        <a href="#">Alerts</a>
      </nav>
    </aside>
    <main class="main-content">
      <header class="top-nav glass-panel">
        <div class="stats">
          <div class="stat">Agents: <span>1,024</span></div>
          <div class="stat">Entities: <span>8,409</span></div>
          <div class="stat">Confidence: <span class="accent">89%</span></div>
        </div>
      </header>
      <div class="content-grid">
        <section class="main-chart glass-panel">
          <header>
            <h3>Live Contagion Network</h3>
            <p>Real-time cascade prediction</p>
          </header>
          <div class="chart-container">
            <ContagionGraph />
          </div>
        </section>
        <section class="side-panel glass-panel">
          <header>
            <h3>Narrative Trajectory</h3>
          </header>
          <!-- Additional stubs here -->
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
}

.side-panel h3 {
  margin: 0;
  color: var(--text-highlight);
}
</style>
