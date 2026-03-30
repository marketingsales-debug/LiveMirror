<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as d3 from 'd3';

const props = defineProps<{
  simulationId?: string | null;
  round?: number;
}>();

const svgContainer = ref<HTMLElement | null>(null);

interface TrustNode extends d3.SimulationNodeDatum {
  id: string;
  stance?: string;
}

interface TrustLink extends d3.SimulationLinkDatum<TrustNode> {
  source: string | TrustNode;
  target: string | TrustNode;
  trust?: number;
}

const nodes = ref<TrustNode[]>([]);
const links = ref<TrustLink[]>([]);
let eventSource: EventSource | null = null;

const setupSSE = () => {
  eventSource = new EventSource('/api/events');
  
  eventSource.addEventListener('simulation_round', (event: MessageEvent) => {
    const message = JSON.parse(event.data);
    const data = message.data;
    
    if (data.simulation_id === props.simulationId && data.trust_network) {
      nodes.value = data.trust_network.nodes;
      links.value = data.trust_network.links;
      drawGraph();
    }
  });

  eventSource.onerror = (err) => {
    console.error("SSE Connection Failed:", err);
    eventSource?.close();
  };
};

const drawGraph = () => {
  if (!svgContainer.value || nodes.value.length === 0) return;
  
  // Clear previous
  d3.select(svgContainer.value).selectAll('*').remove();

  const width = svgContainer.value.clientWidth;
  const height = svgContainer.value.clientHeight || 400;

  const svg = d3.select(svgContainer.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const graphNodes = JSON.parse(JSON.stringify(nodes.value)) as TrustNode[];
  const graphLinks = JSON.parse(JSON.stringify(links.value)) as TrustLink[];

  const simulation = d3.forceSimulation(graphNodes)
    .force('link', d3.forceLink<TrustNode, TrustLink>(graphLinks).id((d) => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg.append('g')
    .selectAll('line')
    .data(graphLinks)
    .enter().append('line')
    .attr('stroke', 'rgba(102, 252, 241, 0.3)')
    .attr('stroke-width', (d) => Math.max(1, (d.trust ?? 0) * 5)); 

  const node = svg.append('g')
    .selectAll('circle')
    .data(graphNodes)
    .enter().append('circle')
    .attr('r', 12)
    .attr('fill', (d) => {
      // Node color = stance
      if (d.stance === 'supportive') return '#66fcf1'; // Green/Cyan
      if (d.stance === 'opposing') return '#ff4d4d'; // Red
      return '#888888'; // Neutral
    })
    .call(d3.drag()
      .on('start', (event: d3.D3DragEvent<SVGCircleElement, TrustNode, TrustNode>, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event: d3.D3DragEvent<SVGCircleElement, TrustNode, TrustNode>, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event: d3.D3DragEvent<SVGCircleElement, TrustNode, TrustNode>, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }));

  simulation.on('tick', () => {
    link
      .attr('x1', (d) => (d.source as TrustNode).x ?? 0)
      .attr('y1', (d) => (d.source as TrustNode).y ?? 0)
      .attr('x2', (d) => (d.target as TrustNode).x ?? 0)
      .attr('y2', (d) => (d.target as TrustNode).y ?? 0);
    node
      .attr('cx', (d) => d.x ?? 0)
      .attr('cy', (d) => d.y ?? 0);
  });
};

onMounted(() => {
  setupSSE();
  window.addEventListener('resize', drawGraph);
});

onUnmounted(() => {
  eventSource?.close();
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
