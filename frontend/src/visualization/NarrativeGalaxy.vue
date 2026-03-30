<template>
  <div ref="container" class="galaxy-container">
    <div class="overlay">
      <h4>3D NARRATIVE GALAXY</h4>
      <p>Semantic Signal Topology (Real-time)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import * as THREE from 'three';

const container = ref<HTMLElement | null>(null);
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let particles: THREE.Points;
let animationId: number;
let handleResize: (() => void) | null = null;

onMounted(() => {
  if (!container.value) return;

  // 1. Scene Setup
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(75, container.value.clientWidth / container.value.clientHeight, 0.1, 1000);
  camera.position.z = 50;

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(container.value.clientWidth, container.value.clientHeight);
  container.value.appendChild(renderer.domElement);

  // 2. Galaxy Particles
  const particleCount = 2000;
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount; i++) {
    // Distributed in a sphere (simulating semantic clusters)
    const r = 30 * Math.sqrt(Math.random());
    const theta = Math.random() * 2 * Math.PI;
    const phi = Math.acos(2 * Math.random() - 1);

    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);

    // Color based on position (Cyan/Amber/Red)
    colors[i * 3] = 0.4 + Math.random() * 0.2; // R
    colors[i * 3 + 1] = 0.8 + Math.random() * 0.2; // G
    colors[i * 3 + 2] = 0.9 + Math.random() * 0.1; // B
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const material = new THREE.PointsMaterial({
    size: 0.5,
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending,
  });

  particles = new THREE.Points(geometry, material);
  scene.add(particles);

  // 3. Animation Loop
  const animate = () => {
    animationId = requestAnimationFrame(animate);
    
    // Slow rotation
    particles.rotation.y += 0.001;
    particles.rotation.x += 0.0005;

    // Simulate "Pulsing" hot narratives
    const time = Date.now() * 0.001;
    material.size = 0.5 + Math.sin(time * 2) * 0.1;

    renderer.render(scene, camera);
  };

  animate();

  // Resize handler
  handleResize = () => {
    if (!container.value) return;
    camera.aspect = container.value.clientWidth / container.value.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.value.clientWidth, container.value.clientHeight);
  };
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  cancelAnimationFrame(animationId);
  if (renderer) renderer.dispose();
  if (handleResize) window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.galaxy-container {
  width: 100%;
  height: 400px;
  position: relative;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #333;
}

.overlay {
  position: absolute;
  top: 20px;
  left: 20px;
  pointer-events: none;
  z-index: 10;
}

h4 {
  margin: 0;
  color: #00f2ff;
  letter-spacing: 2px;
  font-size: 0.8rem;
}

p {
  margin: 4px 0 0 0;
  font-size: 0.65rem;
  color: #666;
  text-transform: uppercase;
}
</style>
