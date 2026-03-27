<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as d3 from 'd3';

const props = defineProps({
  simulationId: String,
  round: Number
});

const svgContainer = ref<HTMLElement | null>(null);

// Since the Trust Network needs agent data, we will mock the force graph shape 
// until we build the API endpoints to stream the dictionaries.
const drawGraph = () => {
  if (!svgContainer.value) return;
  
  // Clear previous
  d3.select(svgContainer.value).selectAll('*').remove();

  const width = svgContainer.value.clientWidth;
  const height = svgContainer.value.clientHeight || 400;

  const svg = d3.select(svgContainer.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  // Example dummy data showing Stance coloring and Trust thickness
  const nodes = [
    { id: 1, name: 'Alpha', stance: 'supportive' },
    { id: 2, name: 'Beta', stance: 'opposing' },
    { id: 3, name: 'Gamma', stance: 'neutral' },
    { id: 4, name: 'Delta', stance: 'supportive' },
  ];

  const links = [
    { source: 1, target: 2, trust: 0.8 },
    { source: 1, target: 3, trust: 0.2 },
    { source: 4, target: 1, trust: 0.9 },
    { source: 3, target: 2, trust: 0.5 },
  ];

  const simulation = d3.forceSimulation(nodes as any)
    .force('link', d3.forceLink(links).id((d: any) => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .enter().append('line')
    .attr('stroke', 'rgba(102, 252, 241, 0.3)')
    .attr('stroke-width', d => Math.max(1, d.trust * 5)); // Edge thickness = trust level

  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter().append('circle')
    .attr('r', 12)
    .attr('fill', d => {
      // Node color = stance
      if (d.stance === 'supportive') return '#66fcf1'; // Green/Cyan
      if (d.stance === 'opposing') return '#ff4d4d'; // Red
      return '#888888'; // Neutral
    })
    .call(d3.drag()
      .on('start', (e, d: any) => {
        if (!e.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (e, d: any) => {
        d.fx = e.x; d.fy = e.y;
      })
      .on('end', (e, d: any) => {
        if (!e.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      }) as any);

  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y);
    node
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y);
  });
};

onMounted(() => {
  drawGraph();
  window.addEventListener('resize', drawGraph);
});

onUnmounted(() => {
  window.removeEventListener('resize', drawGraph);
});

// Reactively redraw the layout as the rounds proceed
watch(() => props.round, () => {
  // In a real scenario, fetch state for simulationId and mutate d3 nodes smoothly
});
</script>

<template>
  <div class="trust-network-graph" ref="svgContainer"></div>
</template>

<style scoped>
.trust-network-graph {
  width: 100%;
  height: 100%;
  min-height: 300px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
}
</style>
