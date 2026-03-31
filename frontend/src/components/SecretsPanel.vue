<template>
  <div class="secrets-panel">
    <h3>🔐 API Key Management</h3>
    <p class="description">Manage your institutional and reasoning API keys securely.</p>

    <div class="add-secret">
      <input v-model="newSecret.name" placeholder="KEY_NAME (e.g. OPENAI_API_KEY)" />
      <input v-model="newSecret.value" type="password" placeholder="Key Value" />
      <button @click="saveSecret" :disabled="loading">Save Key</button>
    </div>

    <div v-if="loading" class="loader">Loading secrets...</div>

    <div v-else class="secrets-list">
      <div v-for="secret in secrets" :key="secret.name" class="secret-item">
        <div class="info">
          <span class="name">{{ secret.name }}</span>
          <span class="status" :class="secret.status">{{ secret.status }}</span>
          <span class="updated">Updated: {{ formatDate(secret.updated_at) }}</span>
        </div>
        <div class="actions">
          <button @click="deleteSecret(secret.name)" class="delete-btn">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface SecretItem {
  name: string;
  status: string;
  updated_at: string;
}

interface SecretListResponse {
  secrets: SecretItem[];
}

interface NewSecret {
  name: string;
  value: string;
}

const secrets = ref<SecretItem[]>([]);
const loading = ref(false);
const newSecret = ref<NewSecret>({ name: '', value: '' });

const authHeaders = (): Record<string, string> => {
  const key = import.meta.env.VITE_SELFMIRROR_API_KEY;
  return key ? { 'X-API-Key': key } : {};
};

const fetchSecrets = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/self-mirror/secrets', {
      headers: authHeaders()
    });
    const data: SecretListResponse = await response.json();
    secrets.value = data.secrets ?? [];
  } catch (err) {
    console.error('Failed to fetch secrets', err);
  } finally {
    loading.value = false;
  }
};

const saveSecret = async () => {
  if (!newSecret.value.name || !newSecret.value.value) return;
  loading.value = true;
  try {
    await fetch('/api/self-mirror/secrets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(newSecret.value)
    });
    newSecret.value = { name: '', value: '' };
    await fetchSecrets();
  } catch (err) {
    console.error('Failed to save secret', err);
    alert('Failed to save secret');
  } finally {
    loading.value = false;
  }
};

const deleteSecret = async (name: string) => {
  if (!confirm(`Are you sure you want to delete ${name}?`)) return;
  try {
    await fetch(`/api/self-mirror/secrets/${name}`, { method: 'DELETE', headers: authHeaders() });
    await fetchSecrets();
  } catch (err) {
    console.error('Failed to delete secret', err);
    alert('Failed to delete secret');
  }
};

const formatDate = (iso: string) => new Date(iso).toLocaleString();

onMounted(fetchSecrets);
</script>

<style scoped>
.secrets-panel {
  background: #1a1a1a;
  color: #fff;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #333;
}

h3 { margin-top: 0; color: #00f2ff; }
.description { font-size: 0.9em; color: #888; margin-bottom: 20px; }

.add-secret {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

input {
  background: #000;
  border: 1px solid #444;
  color: #fff;
  padding: 8px;
  border-radius: 4px;
  flex: 1;
}

button {
  background: #00f2ff;
  color: #000;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

button:disabled { opacity: 0.5; }

.secret-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #222;
  border-bottom: 1px solid #333;
  margin-bottom: 5px;
}

.info { display: flex; flex-direction: column; gap: 4px; }
.name { font-weight: bold; color: #fff; }
.status { font-size: 0.8em; text-transform: uppercase; }
.status.active { color: #00ff88; }
.updated { font-size: 0.75em; color: #666; }

.delete-btn { background: #ff4444; color: #fff; }
</style>
