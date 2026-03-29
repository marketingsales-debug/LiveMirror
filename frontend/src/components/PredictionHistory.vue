<script setup lang="ts">
import { ref, onMounted } from 'vue';

const history = ref<any[]>([]);

const fetchHistory = async () => {
  try {
    const res = await fetch('http://localhost:5001/api/predict/history');
    if (res.ok) {
      const data = await res.json();
      history.value = data.predictions || [];
    }
  } catch(e) { console.error('Failed to fetch prediction history', e); }
};

const validateOutcome = async (predId: string, outcome: string, accuracy: number) => {
  try {
    const res = await fetch('http://localhost:5001/api/predict/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prediction_id: predId, real_outcome: outcome, accuracy })
    });
    if (res.ok) {
      alert('Validation submitted. Learning Loop updated.');
      fetchHistory();
    }
  } catch(e) { console.error('Failed to submit validation', e); }
};

// Optionally refresh periodically or refresh when a new prediction completes
onMounted(() => {
  fetchHistory();
});
</script>

<template>
  <div class="prediction-history">
    <header>
      <h3>Prediction History</h3>
      <button class="refresh-btn" @click="fetchHistory">↻ Refresh</button>
    </header>

    <div class="table-container" v-if="history.length > 0">
      <table>
        <thead>
          <tr>
            <th>Topic</th>
            <th>Confidence</th>
            <th>Direction</th>
            <th>Validate</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pred in history.slice().reverse()" :key="pred.prediction_id">
            <td>{{ pred.topic }}</td>
            <td>
              <span v-if="pred.confidence">{{ (pred.confidence * 100).toFixed(1) }}%</span>
              <span v-else>-</span>
            </td>
            <td>
              <span class="badge" :class="pred.direction?.toLowerCase() || 'pending'">
                {{ pred.direction || 'PENDING' }}
              </span>
            </td>
            <td>
              <div class="validation-actions" v-if="pred.status === 'completed'">
                <button class="btn ok" @click="validateOutcome(pred.prediction_id, pred.direction, 1.0)">✓</button>
                <button class="btn fail" @click="validateOutcome(pred.prediction_id, pred.direction === 'BULL' ? 'BEAR' : 'BULL', 0.0)">✗</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="empty">
      No past predictions available.
    </div>
  </div>
</template>

<style scoped>
.prediction-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
header h3 {
  margin: 0;
  color: var(--text-highlight);
}
.refresh-btn {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 0.75rem;
}
.refresh-btn:hover { background: rgba(255,255,255,0.1); }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
th, td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
th {
  opacity: 0.6;
  text-transform: uppercase;
  font-weight: 500;
  font-size: 0.75rem;
}
.badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
}
.badge.bull { background: rgba(102,252,241,0.2); color: var(--accent-color); }
.badge.bear { background: rgba(255,77,77,0.2); color: #ff4d4d; }
.badge.pending { background: rgba(255,255,255,0.1); color: #aaa; }
.validation-actions {
  display: flex;
  gap: 4px;
}
.btn {
  border: none;
  border-radius: 4px;
  width: 24px;
  height: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
.btn.ok { background: rgba(102,252,241,0.3); }
.btn.ok:hover { background: rgba(102,252,241,0.6); }
.btn.fail { background: rgba(255,77,77,0.3); }
.btn.fail:hover { background: rgba(255,77,77,0.6); }
.empty {
  opacity: 0.5;
  font-size: 0.85rem;
  padding: 16px;
  text-align: center;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
}
</style>
