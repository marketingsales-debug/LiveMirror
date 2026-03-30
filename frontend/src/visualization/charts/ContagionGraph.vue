<script setup lang="ts">
import { onMounted, ref } from 'vue';
import * as d3 from 'd3';

const chartRef = ref<HTMLElement | null>(null);

interface GraphNode extends d3.SimulationNodeDatum {
  id: number;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: number | GraphNode;
  target: number | GraphNode;
}

onMounted(() => {
  if (!chartRef.value) return;

  const width = chartRef.value.clientWidth;
  const height = chartRef.value.clientHeight || 400;

  const svg = d3.select(chartRef.value)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', [0, 0, width, height]);

  // Mock data for initial stub
  const nodes: GraphNode[] = Array.from({ length: 50 }, (_, i) => ({ id: i }));
  const links: GraphLink[] = Array.from({ length: 60 }, () => ({
    source: Math.floor(Math.random() * 50),
    target: Math.floor(Math.random() * 50)
  }));

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(50))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', 'rgba(69, 162, 158, 0.3)')
    .attr('stroke-width', 1.5);

  function dragstarted(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>, d: GraphNode) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>, d: GraphNode) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>, d: GraphNode) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', 5)
    .attr('fill', '#66fcf1')
    .call(d3.drag<SVGCircleElement, GraphNode>()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  simulation.on('tick', () => {
    link
      .attr('x1', (d) => (d.source as GraphNode).x ?? 0)
      .attr('y1', (d) => (d.source as GraphNode).y ?? 0)
      .attr('x2', (d) => (d.target as GraphNode).x ?? 0)
      .attr('y2', (d) => (d.target as GraphNode).y ?? 0);

    node
      .attr('cx', (d) => d.x ?? 0)
      .attr('cy', (d) => d.y ?? 0);
  });
});
</script>

<template>
  <div ref="chartRef" class="d3-container"></div>
</template>

<style scoped>
.d3-container {
  width: 100%;
  height: 100%;
}
</style>
