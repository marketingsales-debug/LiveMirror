<script setup lang="ts">
import { onMounted, ref } from 'vue';
import * as d3 from 'd3';

const chartRef = ref<HTMLElement | null>(null);

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
  const nodes = Array.from({ length: 50 }, (_, i) => ({ id: i }));
  const links = Array.from({ length: 60 }, () => ({
    source: Math.floor(Math.random() * 50),
    target: Math.floor(Math.random() * 50)
  }));

  const simulation = d3.forceSimulation(nodes as any)
    .force('link', d3.forceLink(links).id((d: any) => d.id).distance(50))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', 'rgba(69, 162, 158, 0.3)')
    .attr('stroke-width', 1.5);

  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', 5)
    .attr('fill', '#66fcf1')
    .call((() => {
      const dragBehavior = d3.drag<SVGCircleElement, any>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
      return dragBehavior as any;
    })());

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

  function dragstarted(event: any, d: any) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event: any, d: any) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event: any, d: any) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
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
