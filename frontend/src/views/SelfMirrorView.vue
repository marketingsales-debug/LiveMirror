<script setup lang="ts">
import { ref, onMounted } from 'vue';
import ThoughtStream from '../components/ThoughtStream.vue';

const goal = ref('');
const files = ref<string[]>([]);
const currentFile = ref<string | null>(null);
const agentLoading = ref(false);

const authHeaders = (): Record<string, string> => {
  const key = import.meta.env.VITE_SELFMIRROR_API_KEY;
  return key ? { 'X-API-Key': key } : {};
};

const startGoal = async () => {
  if (!goal.value) return;
  agentLoading.value = true;
  try {
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/self-mirror/goal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        goal: goal.value,
        context_files: currentFile.value ? [currentFile.value] : []
      })
    });
    const data = await res.json();
    console.log('Agent starting:', data);
  } catch (err) {
    console.error('Failed to start goal:', err);
  } finally {
    agentLoading.value = false;
  }
};

const fetchFiles = async () => {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/self-mirror/files`, {
      headers: authHeaders()
    });
    const data = await res.json();
    files.value = data.files;
  } catch (err) {
    console.error('Failed to fetch files:', err);
  }
};

onMounted(() => {
  fetchFiles();
});
</script>

<template>
  <div class="h-screen flex flex-col bg-slate-950 overflow-hidden">
    <!-- Header -->
    <header class="h-14 border-b border-slate-800 flex items-center px-6 justify-between bg-slate-900/50 backdrop-blur">
      <div class="flex items-center gap-3">
        <span class="text-xl font-black text-white tracking-widest uppercase">SelfMirror <span class="text-indigo-500 font-light">IDE</span></span>
        <span class="bg-indigo-500/10 text-indigo-400 text-[10px] px-2 py-0.5 rounded border border-indigo-500/20">AUTONOMOUS AGENT ACTIVE</span>
      </div>
      <div class="flex items-center gap-4">
        <button class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded text-sm transition-colors border border-slate-700">Settings</button>
        <button class="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded text-sm transition-all shadow-lg shadow-indigo-500/20 font-bold">Deploy IDE Changes</button>
      </div>
    </header>

    <!-- Main Content Grid -->
    <main class="flex-grow flex overflow-hidden">
      <!-- File Explorer (Sidebar Left) -->
      <aside class="w-64 border-r border-slate-800 bg-slate-900/30 flex flex-col pt-4">
        <h4 class="px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Project Workspace</h4>
        <div class="overflow-y-auto flex-grow px-2 custom-scrollbar">
          <div v-for="file in files" 
               :key="file" 
               @click="currentFile = file"
               class="flex items-center gap-2 p-2 rounded text-xs transition-colors cursor-pointer"
               :class="currentFile === file ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'">
            <span class="opacity-60 text-lg">📄</span>
            {{ file }}
          </div>
        </div>
      </aside>

      <!-- Central Workspace (Prompt + Code Area) -->
      <section class="flex-grow flex flex-col overflow-hidden bg-slate-950/50">
        <!-- Goal Console -->
        <div class="p-6 border-b border-slate-800 bg-slate-900/20">
          <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Goal Definition</label>
          <div class="flex gap-4">
            <input v-model="goal" 
                   @keyup.enter="startGoal"
                   type="text" 
                   placeholder="e.g., 'Extract the API client into a separate service and add retry logic...'" 
                   class="bg-slate-900 border border-slate-800 p-3 rounded-lg flex-grow text-white focus:outline-none focus:border-indigo-500 transition-all font-mono text-sm" />
            <button @click="startGoal" 
                    :disabled="agentLoading || !goal"
                    class="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white px-8 rounded-lg font-bold transition-all flex items-center gap-2">
              <span v-if="agentLoading" class="animate-spin text-xl">🌀</span>
              {{ agentLoading ? 'THINKING...' : 'INITIATE AGENT' }}
            </button>
          </div>
        </div>

        <!-- Code Preview Area -->
        <div class="flex-grow flex flex-col relative items-center justify-center text-slate-700">
           <div class="opacity-20 text-9xl absolute pointer-events-none">CODE</div>
           <div class="z-10 bg-slate-900/40 p-10 rounded-3xl border border-slate-800/50 backdrop-blur-xl flex flex-col items-center max-w-lg text-center gap-6">
              <div class="text-6xl">🤖</div>
              <h2 class="text-slate-300 font-bold text-xl uppercase tracking-widest">Autonomous Workspace Idle</h2>
              <p class="text-slate-500 font-mono text-sm leading-relaxed">
                The agent is currently monitoring the environment. Define a goal above to start the self-evolution process. 
                Full code editing and execution logs will stream here.
              </p>
           </div>
        </div>
      </section>

      <!-- Lateral Panel (Thought Stream) -->
      <aside class="w-[450px]">
        <ThoughtStream />
      </aside>
    </main>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 10px;
}
</style>
