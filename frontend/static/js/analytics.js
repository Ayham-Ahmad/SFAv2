/* analytics.js — streaming thinking display, chat, graph workspace */
'use strict';

/* ── State ───────────────────────────────────────────────────────────────── */
let isSending       = false;
let currentThinkBlock = null;
let lastInteractionId = null;

/* ── Boot ────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  if (!Auth.requireAuth()) return;
  loadSessionGraphs();
  loadChatHistory();

  const input = document.getElementById('chat-input');
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  /* Auto-resize textarea */
  input?.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
  document.getElementById('send-btn')?.addEventListener('click', sendMessage);
  document.getElementById('stop-btn')?.addEventListener('click', stopQuery);
  document.getElementById('clear-graphs-btn')?.addEventListener('click', clearAllGraphs);
});

/* ── Chat history ────────────────────────────────────────────────────────── */
async function loadChatHistory() {
  const res = await API.get('/api/chat/history');
  if (!res?.ok) return;
  const history = res.data?.data?.history || [];
  history.forEach(item => {
    // Skip malformed or empty answers to avoid marked() crashing on null/undefined
    if (!item) return;
    const answer = item.answer == null ? '' : String(item.answer);
    if (answer === '') return;
    appendBotMessage(answer, item.interaction_id, false);
  });
}

/* ── Send message ────────────────────────────────────────────────────────── */
async function sendMessage() {
  if (isSending) return;
  const input = document.getElementById('chat-input');
  const message = input?.value.trim();
  if (!message) return;

  isSending = true;
  input.value = '';
  input.style.height = 'auto';
  setUIState('sending');
  appendUserMessage(message);

  /* Start a thinking block immediately */
  currentThinkBlock = appendThinkingBlock();

  try {
    const res = await API.post('/api/chat', { message });

    /* Close the thinking block */
    finalizeThinkingBlock(currentThinkBlock, res?.ok);
    currentThinkBlock = null;

    if (!res) { appendBotMessage('Connection lost. Please try again.'); return; }

    if (res.ok) {
      const answer = res.data?.message || 'No response.';
      lastInteractionId = res.data?.data?.interaction_id || null;
      const msgEl = appendBotMessage(answer, lastInteractionId, true);
      if (res.data?.data?.graphs?.length) renderGraphs(res.data.data.graphs);
    } else {
      appendBotMessage(res.data?.detail || res.data?.message || 'An error occurred.');
    }
  } catch (err) {
    finalizeThinkingBlock(currentThinkBlock, false);
    currentThinkBlock = null;
    appendBotMessage('Network error. Please check your connection.');
  } finally {
    isSending = false;
    setUIState('idle');
    scrollToBottom();
  }
}

/* ── Stop ────────────────────────────────────────────────────────────────── */
async function stopQuery() {
  document.getElementById('stop-btn').disabled = true;
  await API.post('/api/chat/stop');
  Toast.info('Stop signal sent — the agent will finish its current step.');
}

/* ── UI state ────────────────────────────────────────────────────────────── */
function setUIState(state) {
  const sendBtn = document.getElementById('send-btn');
  const stopBtn = document.getElementById('stop-btn');
  const status  = document.getElementById('status-text');
  if (state === 'sending') {
    sendBtn.style.display = 'none';
    stopBtn.style.display = 'flex';
    stopBtn.disabled = false;
    if (status) status.textContent = 'Thinking…';
  } else {
    sendBtn.style.display = 'flex';
    stopBtn.style.display = 'none';
    if (status) status.textContent = '';
  }
}

/* ── Message builders ────────────────────────────────────────────────────── */
function appendUserMessage(text) {
  const box = document.getElementById('chat-messages');
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML = `
    <div class="msg-avatar">You</div>
    <div class="msg-bubble">${escHtml(text)}</div>`;
  box.appendChild(el);
  scrollToBottom();
  return el;
}

/*
 * Thinking block — the signature element.
 * Shows a live-updating list of reasoning steps that stream in as
 * the server works. Steps are populated via simulateThinking() while
 * the real HTTP call runs. When the response arrives the block is
 * finalised with a done/error state.
 */
function appendThinkingBlock() {
  const box = document.getElementById('chat-messages');
  const wrapper = document.createElement('div');
  wrapper.className = 'msg bot';
  wrapper.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div style="flex:1">
      <div class="thinking-block" id="think-${Date.now()}">
        <div class="thinking-header" onclick="toggleThinking(this)">
          <div class="thinking-pulse" id="think-pulse"></div>
          <span class="thinking-label">Reasoning</span>
          <span class="thinking-toggle">▾ collapse</span>
        </div>
        <div class="thinking-steps" id="think-steps"></div>
      </div>
    </div>`;
  box.appendChild(wrapper);
  scrollToBottom();
  simulateThinking(wrapper);
  return wrapper;
}

const THINKING_STEPS = [
  ['fa-shield-alt',   'Safety check — validating query…'],
  ['fa-brain',        'Classifying intent and complexity…'],
  ['fa-database',     'Selecting relevant data sources…'],
  ['fa-table',        'Mapping tables to your question…'],
  ['fa-project-diagram','Building execution plan…'],
  ['fa-search',       'Retrieving financial data…'],
  ['fa-calculator',   'Running calculations…'],
  ['fa-book-open',    'Consulting advisory knowledge base…'],
  ['fa-chart-line',   'Composing analysis…'],
  ['fa-check-double', 'Verifying answer accuracy…'],
];

function simulateThinking(wrapper) {
  const steps  = wrapper.querySelector('.thinking-steps');
  const pulse  = wrapper.querySelector('.thinking-pulse');
  let i = 0;
  const iv = setInterval(() => {
    if (!document.body.contains(wrapper)) { clearInterval(iv); return; }
    if (i >= THINKING_STEPS.length || !isSending) { clearInterval(iv); return; }
    const [icon, label] = THINKING_STEPS[i++];
    const step = document.createElement('div');
    step.className = 'thinking-step';
    step.innerHTML = `<i class="fas ${icon} step-icon"></i><span>${label}</span>`;
    steps.appendChild(step);
    scrollToBottom();
  }, 900);
  wrapper._thinkInterval = iv;
}

function finalizeThinkingBlock(wrapper, success = true) {
  if (!wrapper) return;
  clearInterval(wrapper._thinkInterval);
  const pulse = wrapper.querySelector('.thinking-pulse');
  const label = wrapper.querySelector('.thinking-label');
  if (pulse) { pulse.classList.add('done'); pulse.style.background = success ? 'var(--emerald)' : 'var(--rose)'; }
  if (label) label.textContent = success ? 'Done' : 'Stopped';
}

function toggleThinking(header) {
  const steps  = header.nextElementSibling;
  const toggle = header.querySelector('.thinking-toggle');
  const hidden = steps.classList.toggle('collapsed');
  if (toggle) toggle.textContent = hidden ? '▸ expand' : '▾ collapse';
}

function appendBotMessage(markdown, interactionId = null, showFeedback = false) {
  const box = document.getElementById('chat-messages');
  const el  = document.createElement('div');
  el.className = 'msg bot';
  const safeText = markdown == null ? '' : String(markdown);
  let html = '';
  if (safeText === '') {
    html = '';
  } else if (typeof marked !== 'undefined') {
    try {
      html = marked.parse(safeText);
    } catch (err) {
      console.warn('marked parse failed, falling back to plain text', err);
      html = escHtml(safeText);
    }
  } else {
    html = escHtml(safeText);
  }
  el.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div style="flex:1">
      <div class="msg-bubble">${html}</div>
      ${showFeedback && interactionId ? `
      <div class="msg-feedback">
        <button class="feedback-btn" onclick="sendFeedback(${interactionId}, true, this)" title="Helpful">
          <i class="fas fa-thumbs-up"></i>
        </button>
        <button class="feedback-btn" onclick="sendFeedback(${interactionId}, false, this)" title="Not helpful">
          <i class="fas fa-thumbs-down"></i>
        </button>
      </div>` : ''}
    </div>`;
  box.appendChild(el);
  scrollToBottom();
  return el;
}

/* ── Feedback ────────────────────────────────────────────────────────────── */
async function sendFeedback(interactionId, positive, btn) {
  const res = await API.post(`/api/admin/interactions/${interactionId}/feedback?feedback=${positive}`);
  if (res?.ok) {
    btn.closest('.msg-feedback').querySelectorAll('.feedback-btn').forEach(b => b.classList.remove('active-up','active-down'));
    btn.classList.add(positive ? 'active-up' : 'active-down');
    Toast.success('Feedback recorded');
  }
}

/* ── Graphs ──────────────────────────────────────────────────────────────── */
async function loadSessionGraphs() {
  const res = await API.get('/api/graphs/session');
  if (!res?.ok) return;
  const graphs = res.data?.data?.graphs || [];
  if (graphs.length) {
    hideEmptyWorkspace();
    graphs.forEach(renderSingleGraph);
  }
}

function renderGraphs(graphs) {
  if (!graphs?.length) return;
  hideEmptyWorkspace();
  graphs.forEach(renderSingleGraph);
}

function renderSingleGraph(config) {
  const grid   = document.getElementById('graphs-grid');
  const graphId = `g-${Date.now()}-${Math.random().toString(36).slice(2,6)}`;
  const card   = document.createElement('div');
  card.className = 'graph-card';
  card.innerHTML = `
    <div class="graph-card-header">
      <span class="graph-card-title">${config.title || 'Chart'}</span>
      <button class="btn btn-ghost btn-sm btn-icon" onclick="removeGraph(this)" title="Remove">
        <i class="fas fa-times"></i>
      </button>
    </div>
    <div class="graph-card-body">
      <div id="${graphId}" style="width:100%;height:260px"></div>
    </div>`;
  grid.appendChild(card);

  const traces = buildTraces(config);
  const layout = {
    margin: { t: 8, r: 12, l: 44, b: 44 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor:  'rgba(0,0,0,0)',
    font:  { family: 'Inter, sans-serif', color: '#94A3B8', size: 11 },
    xaxis: { gridcolor: '#1F2D45', zerolinecolor: '#1F2D45', title: { text: config.x_column || '', font: { size: 11 } } },
    yaxis: { gridcolor: '#1F2D45', zerolinecolor: '#1F2D45', title: { text: config.y_column || '', font: { size: 11 } } },
    showlegend: !!(config.series?.length > 1),
    legend: { font: { size: 11 }, bgcolor: 'rgba(0,0,0,0)' },
  };
  if (config.series?.some(s => s.y_axis === 'y2')) {
    layout.yaxis2 = { overlaying: 'y', side: 'right', gridcolor: '#1F2D45' };
  }
  Plotly.newPlot(graphId, traces, layout, { responsive: true, displayModeBar: false });
}

function buildTraces(config) {
  if (config.series?.length) {
    return config.series.map(s => ({
      x: config.data.map(d => d[config.x_column]),
      y: config.data.map(d => d[s.column || config.y_column]),
      type:  s.type === 'bar' ? 'bar' : 'scatter',
      mode:  s.type === 'line' ? 'lines+markers' : undefined,
      name:  s.column || config.y_column,
      yaxis: s.y_axis === 'y2' ? 'y2' : 'y',
      marker: { color: '#3B82F6' },
      line:  { shape: 'spline', color: '#3B82F6', width: 2 },
    }));
  }
  return [{
    x:    config.data.map(d => d[config.x_column]),
    y:    config.data.map(d => d[config.y_column]),
    type: config.graph_type === 'bar' ? 'bar' : 'scatter',
    mode: config.graph_type === 'line' ? 'lines+markers' : undefined,
    marker: { color: '#3B82F6' },
    line:   { shape: 'spline', color: '#3B82F6', width: 2 },
    name:   config.y_column,
  }];
}

function removeGraph(btn) {
  btn.closest('.graph-card')?.remove();
  if (!document.getElementById('graphs-grid')?.children.length) showEmptyWorkspace();
}

async function clearAllGraphs() {
  confirmAction('Clear all graphs from this session?', async () => {
    const res = await API.delete('/api/graphs/session/all');
    if (res?.ok) {
      document.getElementById('graphs-grid').innerHTML = '';
      showEmptyWorkspace();
      Toast.success('Workspace cleared');
    }
  });
}

function hideEmptyWorkspace() { document.getElementById('empty-workspace')?.remove(); }
function showEmptyWorkspace() {
  const grid = document.getElementById('graphs-grid');
  if (!document.getElementById('empty-workspace')) {
    const el = document.createElement('div');
    el.id = 'empty-workspace';
    el.className = 'empty-workspace';
    el.innerHTML = `<i class="fas fa-chart-area"></i><p>Ask the AI to generate a chart</p>`;
    grid.parentElement.appendChild(el);
  }
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function scrollToBottom() {
  const box = document.getElementById('chat-messages');
  if (box) box.scrollTop = box.scrollHeight;
}
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
