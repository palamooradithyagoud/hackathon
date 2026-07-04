/**
 * citation.js — Canvas-based Force-Directed citation network graph
 * Simulates nodes (Faculty, Topics, Publications) and links.
 * Supports pan, zoom, hover tooltip, search focus, and details display.
 */

import { stringToColor } from './utils.js';
import { searchSemanticScholar, fetchCitationGraph } from './api.js';

// Graph database structure
const graphData = {
  nodes: [
    // Faculty
    { id: 'F1', label: 'Dr. Padmaja', type: 'faculty', group: 1, desc: 'Computer Science Department. Author of Agri-AI disease detection.' },
    { id: 'F2', label: 'Dr. Venkateshwara', type: 'faculty', group: 1, desc: 'Computer Science Department. Focuses on Feature Extraction algorithms.' },
    { id: 'F3', label: 'Dr. Madhurya', type: 'faculty', group: 2, desc: 'IT Department. Focuses on IoT and Named Data Networking.' },
    { id: 'F4', label: 'Dr. Gagandeep', type: 'faculty', group: 3, desc: 'ECE Department. Focuses on IoT based remote health monitoring.' },
    { id: 'F5', label: 'Dr. Vasantha', type: 'faculty', group: 2, desc: 'IT Department. Focuses on network node power optimization.' },
    { id: 'F6', label: 'Prof. Srinivas Gongula', type: 'faculty', group: 1, desc: 'Computer Science Department. Focuses on streaming big data safety engines.' },
    { id: 'F7', label: 'Dr. Ravikumar', type: 'faculty', group: 3, desc: 'ECE Department. Focuses on IPv6 migration studies.' },
    { id: 'F8', label: 'Prof. Manzoor', type: 'faculty', group: 1, desc: 'Computer Science Department. Focuses on GANs and Diffusion models.' },

    // Domains
    { id: 'D1', label: 'Agriculture AI', type: 'domain', group: 4, desc: 'Plant pathology visual inspections using convolution matrices.' },
    { id: 'D2', label: 'Machine Learning', type: 'domain', group: 4, desc: 'Model architectures, classification matrices, and feature selections.' },
    { id: 'D3', label: 'IoT', type: 'domain', group: 4, desc: 'Internet of Things sensor networks, edge gateways, and messaging protocols.' },
    { id: 'D4', label: 'Healthcare IT', type: 'domain', group: 4, desc: 'Telemetry sensing, medical alert devices, and remote healthcare monitors.' },
    { id: 'D5', label: 'Network Power', type: 'domain', group: 4, desc: 'Green networking, routing node efficiency, and optical optimization.' },
    { id: 'D6', label: 'Big Data', type: 'domain', group: 4, desc: 'Apache Kafka streaming architectures, warning relays, and big data clusters.' },
    { id: 'D7', label: 'IPv6 Routing', type: 'domain', group: 4, desc: 'Internet routing address protocols and translation engines.' },
    { id: 'D8', label: 'Generative AI', type: 'domain', group: 4, desc: 'Generative adversarial networks, diffusion images, and generative text systems.' },

    // Papers
    { id: 'P1', label: 'Agri-AI Plant disease', type: 'paper', group: 5, desc: 'Agri-Ai-Intelligent-Plant-Disease-Surveillance-and-Predictive-Forecasting_PADMAJA.pdf' },
    { id: 'P2', label: 'Feature Extraction Comp Model', type: 'paper', group: 5, desc: 'Comprehensive Models Towards for Feature_venkateshwara.pdf' },
    { id: 'P3', label: 'NDN with IoT Networking', type: 'paper', group: 5, desc: 'Integrating Named Data Networking with IoT-Based Internet _MADHURYA.pdf' },
    { id: 'P4', label: 'IoT Health Monitoring System', type: 'paper', group: 5, desc: 'IOT based health monitoring_gagandeep.pdf' },
    { id: 'P5', label: 'Edge Energy Consumption', type: 'paper', group: 5, desc: 'Measuring Internet Energy Consumption at The Edge and Core_vasantha.pdf' },
    { id: 'P6', label: 'Big Data Accident Alert', type: 'paper', group: 5, desc: 'Accident Detection and Alert System Using Big Data Analytics_SRININVAS_GONGULA.pdf' },
    { id: 'P7', label: 'IPv6 Adoption study', type: 'paper', group: 5, desc: 'Characterizing Ipv6 Adoption Trends Through Longitudinal _RAVIKUMAR.pdf' },
    { id: 'P8', label: 'CNN to Diffusion models', type: 'paper', group: 5, desc: 'From CNNs to diffusion models_MANZOOR.pdf' }
  ],
  links: [
    // Faculty to Papers
    { source: 'F1', target: 'P1' },
    { source: 'F2', target: 'P2' },
    { source: 'F3', target: 'P3' },
    { source: 'F4', target: 'P4' },
    { source: 'F5', target: 'P5' },
    { source: 'F6', target: 'P6' },
    { source: 'F7', target: 'P7' },
    { source: 'F8', target: 'P8' },

    // Papers to Domains
    { source: 'P1', target: 'D1' },
    { source: 'P2', target: 'D2' },
    { source: 'P3', target: 'D3' },
    { source: 'P4', target: 'D4' },
    { source: 'P4', target: 'D3' }, // Dual link health is IoT
    { source: 'P5', target: 'D5' },
    { source: 'P6', target: 'D6' },
    { source: 'P7', target: 'D7' },
    { source: 'P8', target: 'D8' },
    { source: 'P8', target: 'D2' } // Diffusion is ML
  ]
};

// Canvas Settings
const canvas = document.getElementById('graph-canvas');
const workspace = document.getElementById('graph-workspace');
const searchInput = document.getElementById('graph-search-input');
const resetPanBtn = document.getElementById('graph-reset-pan-btn');
const fullscreenBtn = document.getElementById('graph-fullscreen-btn');
const zoomInBtn = document.getElementById('graph-zoom-in');
const zoomOutBtn = document.getElementById('graph-zoom-out');

const detailPanel = document.getElementById('graph-node-details');
const detailClose = document.getElementById('graph-details-close-btn');
const detailTitle = document.getElementById('detail-title');
const detailType = document.getElementById('detail-type');
const detailDesc = document.getElementById('detail-desc');

let ctx = null;
let width = 800;
let height = 600;

// Simulation State
let nodes = [];
let links = [];
let transform = { x: 0, y: 0, k: 1 };
let draggedNode = null;
let hoveredNode = null;
let selectedNode = null;
let isPanning = false;
let startPan = { x: 0, y: 0 };
let searchHighlight = '';
let simulationInterval = null;

function loadGraph(nodesData, linksData) {
  selectedNode = null;
  hoveredNode = null;
  if (detailPanel) detailPanel.classList.remove('visible');

  nodes = nodesData.map(n => ({
    ...n,
    x: Math.random() * (width - 100) + 50,
    y: Math.random() * (height - 100) + 50,
    vx: 0,
    vy: 0
  }));

  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  links = [];
  linksData.forEach(l => {
    const srcNode = nodeMap.get(l.source);
    const tgtNode = nodeMap.get(l.target);
    if (srcNode && tgtNode) {
      links.push({
        source: srcNode,
        target: tgtNode
      });
    }
  });

  recenter();
  startSimulation();
}

document.addEventListener('DOMContentLoaded', () => {
  if (!canvas) return;
  ctx = canvas.getContext('2d');
  resizeCanvas();

  // Load datasets
  loadGraph(graphData.nodes, graphData.links);

  // Listeners
  window.addEventListener('resize', resizeCanvas);
  canvas.addEventListener('mousedown', onMouseDown);
  canvas.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
  canvas.addEventListener('wheel', onWheel);

  if (resetPanBtn) resetPanBtn.addEventListener('click', recenter);
  if (fullscreenBtn) fullscreenBtn.addEventListener('click', toggleFullscreen);
  if (zoomInBtn) zoomInBtn.addEventListener('click', () => zoom(1.2));
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => zoom(0.8));
  if (detailClose) detailClose.addEventListener('click', () => detailPanel.classList.remove('visible'));

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchHighlight = e.target.value.toLowerCase().trim();
    });
  }

  // Hook up Scholar Dynamic Search
  const scholarInput = document.getElementById('scholar-search-input');
  const scholarBtn = document.getElementById('scholar-search-btn');
  const scholarResults = document.getElementById('scholar-search-results');

  if (scholarBtn && scholarInput && scholarResults) {
    scholarBtn.addEventListener('click', async () => {
      const q = scholarInput.value.trim();
      if (!q) return;

      scholarBtn.disabled = true;
      scholarBtn.textContent = 'Searching...';

      try {
        const papers = await searchSemanticScholar(q);
        scholarResults.innerHTML = '';
        if (papers.length === 0) {
          scholarResults.innerHTML = '<div style="color:var(--text-muted); font-size:11px; padding:6px;">No papers found on Semantic Scholar.</div>';
        } else {
          papers.forEach(p => {
            const item = document.createElement('div');
            item.style.padding = '8px';
            item.style.cursor = 'pointer';
            item.style.borderBottom = '1px solid var(--border-color)';
            item.style.fontSize = '11px';
            item.innerHTML = `
              <div style="font-weight:600; color:var(--text-primary); text-align: left;">${p.title}</div>
              <div style="color:var(--text-muted); margin-top:2px; text-align: left;">${p.authors.join(', ')} (${p.year || 'N/A'})</div>
            `;
            item.addEventListener('click', async () => {
              scholarResults.style.display = 'none';
              scholarInput.value = p.title;
              
              // Load the citation graph
              try {
                const graph = await fetchCitationGraph(p.paperId);
                if (graph && graph.nodes && graph.nodes.length > 0) {
                  // Map the standard graph model keys to the visualizer keys if different
                  const mappedNodes = graph.nodes.map(n => ({
                    id: n.id,
                    label: n.label,
                    type: n.type || 'paper',
                    desc: `Resource ID: ${n.id}. Type: ${n.type || 'paper'} node.`,
                    color: n.color
                  }));
                  loadGraph(mappedNodes, graph.links);
                } else {
                  alert('No references or citations found for this paper.');
                }
              } catch (err) {
                alert('Failed to load citation graph: ' + err.message);
              }
            });
            scholarResults.appendChild(item);
          });
        }
        scholarResults.style.display = 'block';
      } catch (err) {
        alert('Search failed: ' + err.message);
      } finally {
        scholarBtn.disabled = false;
        scholarBtn.textContent = 'Search & Build';
      }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.graph-search')) {
        scholarResults.style.display = 'none';
      }
    });
  }
});

function resizeCanvas() {
  const rect = workspace.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  canvas.width = width;
  canvas.height = height;
}

/**
 * Basic Force Simulation Engine
 */
function startSimulation() {
  function step() {
    // 1. Repulsion (between all nodes)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const n1 = nodes[i];
        const n2 = nodes[j];
        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 600 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        n1.vx -= fx;
        n1.vy -= fy;
        n2.vx += fx;
        n2.vy += fy;
      }
    }

    // 2. Attraction (along links)
    links.forEach(l => {
      const dx = l.target.x - l.source.x;
      const dy = l.target.y - l.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const desiredDist = 120;
      const force = (dist - desiredDist) * 0.03;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      l.source.vx += fx;
      l.source.vy += fy;
      l.target.vx -= fx;
      l.target.vy -= fy;
    });

    // 3. Gravity / Center attraction
    nodes.forEach(n => {
      const dx = width / 2 - n.x;
      const dy = height / 2 - n.y;
      n.vx += dx * 0.005;
      n.vy += dy * 0.005;

      // Friction
      n.vx *= 0.85;
      n.vy *= 0.85;

      // Update positions
      if (n !== draggedNode) {
        n.x += n.vx;
        n.y += n.vy;
      }
    });

    draw();
    requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/**
 * Draw Canvas Graph Nodes and Links
 */
function draw() {
  if (!ctx) return;
  ctx.save();
  ctx.clearRect(0, 0, width, height);

  // Apply Panning and Zooming transformations
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);

  // Draw links
  ctx.lineWidth = 1.5;
  links.forEach(l => {
    ctx.strokeStyle = '#374151'; // Muted border
    ctx.beginPath();
    ctx.moveTo(l.source.x, l.source.y);
    ctx.lineTo(l.target.x, l.target.y);
    ctx.stroke();
  });

  // Draw nodes
  nodes.forEach(n => {
    const radius = n.type === 'faculty' ? 14 : (n.type === 'domain' ? 10 : 8);
    const color = n.type === 'faculty' ? '#4F46E5' : (n.type === 'domain' ? '#06B6D4' : '#10B981');

    ctx.beginPath();
    ctx.arc(n.x, n.y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Node Outline selection/highlights
    let isHighlighted = searchHighlight && n.label.toLowerCase().includes(searchHighlight);
    if (isHighlighted || n === hoveredNode || n === selectedNode) {
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#FFFFFF';
      ctx.stroke();
    } else {
      ctx.lineWidth = 1;
      ctx.strokeStyle = '#1F2937';
      ctx.stroke();
    }

    // Text Label below node
    ctx.font = '10px Inter';
    ctx.fillStyle = isHighlighted ? '#FFFFFF' : '#9CA3AF';
    ctx.textAlign = 'center';
    ctx.fillText(n.label, n.x, n.y + radius + 14);
  });

  ctx.restore();
}

// ── Event Handlers ──

function getMousePos(e) {
  const rect = canvas.getBoundingClientRect();
  const rawX = e.clientX - rect.left;
  const rawY = e.clientY - rect.top;

  // Convert raw coords back through translation and scaling
  return {
    x: (rawX - transform.x) / transform.k,
    y: (rawY - transform.y) / transform.k
  };
}

function getNodeAtPos(pos) {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    const dx = n.x - pos.x;
    const dy = n.y - pos.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const radius = n.type === 'faculty' ? 14 : (n.type === 'domain' ? 10 : 8);
    if (dist <= radius + 5) return n;
  }
  return null;
}

function onMouseDown(e) {
  const pos = getMousePos(e);
  const target = getNodeAtPos(pos);

  if (target) {
    draggedNode = target;
    selectedNode = target;
    showNodeDetails(target);
  } else {
    isPanning = true;
    startPan = { x: e.clientX - transform.x, y: e.clientY - transform.y };
  }
}

function onMouseMove(e) {
  const pos = getMousePos(e);
  const node = getNodeAtPos(pos);
  hoveredNode = node;

  if (draggedNode) {
    draggedNode.x = pos.x;
    draggedNode.y = pos.y;
    draggedNode.vx = 0;
    draggedNode.vy = 0;
  } else if (isPanning) {
    transform.x = e.clientX - startPan.x;
    transform.y = e.clientY - startPan.y;
  }
}

function onMouseUp() {
  draggedNode = null;
  isPanning = false;
}

function onWheel(e) {
  e.preventDefault();
  const zoomFactor = e.deltaY < 0 ? 1.05 : 0.95;
  zoom(zoomFactor);
}

function zoom(factor) {
  transform.k = Math.max(0.2, Math.min(4, transform.k * factor));
}

function recenter() {
  transform = { x: 0, y: 0, k: 1 };
  nodes.forEach(n => {
    n.x = Math.random() * width;
    n.y = Math.random() * height;
  });
}

function showNodeDetails(node) {
  detailTitle.textContent = node.label;
  const types = { faculty: 'Faculty Profile', domain: 'Research Area', paper: 'Seed Paper Document' };
  detailType.textContent = `Type: ${types[node.type] || 'Node'}`;
  detailDesc.textContent = node.desc;
  detailPanel.classList.add('visible');
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    workspace.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen();
  }
}
