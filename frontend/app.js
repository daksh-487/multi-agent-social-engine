/* ══════════════════════════════════════════════════════
   Grid07 AI — app.js
   ══════════════════════════════════════════════════════ */

const API = '/api';

// ──────────────────────────────────────────────────────
// Tab navigation
// ──────────────────────────────────────────────────────
document.querySelectorAll('.nav-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove('hidden');
  });
});

// ──────────────────────────────────────────────────────
// Health check
// ──────────────────────────────────────────────────────
async function checkHealth() {
  const dot   = document.querySelector('.dot');
  const label = document.querySelector('.health-label');
  try {
    const res  = await fetch(`${API}/health`);
    const data = await res.json();
    if (data.status === 'ok') {
      dot.className   = 'dot ok';
      label.textContent = data.groq_key_configured ? 'API Ready' : 'No Groq Key';
      if (!data.groq_key_configured) dot.className = 'dot warn';
    }
  } catch {
    dot.className   = 'dot err';
    label.textContent = 'API Offline';
  }
}
checkHealth();
setInterval(checkHealth, 10000);

// ──────────────────────────────────────────────────────
// Spinner helpers
// ──────────────────────────────────────────────────────
function showSpinner(msg = 'Processing…') {
  document.getElementById('spinner-overlay').classList.remove('hidden');
  document.getElementById('spinner-msg').textContent = msg;
}
function hideSpinner() {
  document.getElementById('spinner-overlay').classList.add('hidden');
}

// ──────────────────────────────────────────────────────
// PHASE 1
// ──────────────────────────────────────────────────────
const p1Thresh = document.getElementById('p1-thresh');
const p1ThreshVal = document.getElementById('p1-thresh-val');
p1Thresh.addEventListener('input', () => { p1ThreshVal.textContent = p1Thresh.value; });

const PERSONA_EMOJIS = {
  'Bot A (Tech Maximalist)': '🚀',
  'Bot B (Doomer / Skeptic)': '☠️',
  'Bot C (Finance Bro)': '💰'
};

document.getElementById('p1-run').addEventListener('click', async () => {
  const post      = document.getElementById('p1-post').value.trim();
  const threshold = parseFloat(p1Thresh.value);
  if (!post) { alert('Please enter a post.'); return; }

  showSpinner('Running vector router…');
  try {
    const res  = await fetch(`${API}/phase1/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_content: post, threshold })
    });
    const data = await res.json();
    hideSpinner();

    if (data.error) { renderError('p1-results', data.error); return; }

    // Render persona cards with match status
    const grid = document.getElementById('p1-personas-grid');
    const matchedIds = new Set((data.matches || []).map(m => m.bot_id));
    grid.innerHTML = (data.all_personas || []).map(p => `
      <div class="persona-card ${matchedIds.has(p.id) ? 'matched' : ''}">
        <div class="persona-emoji">${PERSONA_EMOJIS[p.id] || '🤖'}</div>
        <div class="persona-id">${p.id}</div>
        <div class="persona-desc">${p.description}</div>
      </div>
    `).join('');

    // Results panel
    const panel = document.getElementById('p1-results');
    document.getElementById('p1-placeholder').classList.add('hidden');
    panel.classList.remove('hidden');

    if (!data.matches || data.matches.length === 0) {
      panel.innerHTML = `<div class="no-match">⚠️ No bots matched at threshold <strong>${threshold}</strong>. Try lowering the slider.</div>`;
    } else {
      panel.innerHTML = `
        <p style="font-size:0.78rem;color:var(--muted);margin-bottom:0.75rem;">
          ${data.matches.length} bot(s) matched above <strong>${threshold}</strong>
        </p>
        ${data.matches.map(m => `
          <div class="match-item">
            <div style="flex:1">
              <div class="match-name">${PERSONA_EMOJIS[m.bot_id] || '🤖'} ${m.bot_id}</div>
              <div class="score-bar-wrap">
                <div class="score-bar" style="width:${(m.similarity_score * 100).toFixed(1)}%"></div>
              </div>
            </div>
            <div class="match-score">${(m.similarity_score * 100).toFixed(1)}%</div>
          </div>
        `).join('')}
      `;
    }
  } catch (e) {
    hideSpinner();
    renderError('p1-results', 'Could not reach the API server. Is api.py running?');
  }
});

// ──────────────────────────────────────────────────────
// PHASE 2
// ──────────────────────────────────────────────────────
let selectedBotId      = 'Bot A (Tech Maximalist)';
let selectedBotPersona = 'I believe AI and crypto will solve all human problems. I am highly optimistic about technology, Elon Musk, and space exploration. I dismiss regulatory concerns.';

function updatePersonaPreview() {
  document.getElementById('p2-persona-preview').textContent = `"${selectedBotPersona}"`;
}
updatePersonaPreview();

document.getElementById('p2-bot-selector').querySelectorAll('.bot-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.bot-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedBotId      = btn.dataset.botId;
    selectedBotPersona = btn.dataset.persona;
    updatePersonaPreview();
  });
});

const pipeNodes = {
  start:  document.getElementById('pn-start'),
  decide: document.getElementById('pn-decide'),
  search: document.getElementById('pn-search'),
  draft:  document.getElementById('pn-draft'),
  end:    document.getElementById('pn-end'),
};

function resetPipe() {
  Object.values(pipeNodes).forEach(n => { n.classList.remove('active','done'); });
}
function activateNode(key) {
  pipeNodes[key].classList.add('active');
}
function completeNode(key) {
  pipeNodes[key].classList.remove('active');
  pipeNodes[key].classList.add('done');
}

document.getElementById('p2-run').addEventListener('click', async () => {
  showSpinner('Running LangGraph pipeline…');
  resetPipe();
  activateNode('start');

  const steps = ['decide','search','draft'];
  const delay = ms => new Promise(r => setTimeout(r, ms));

  try {
    const fetchPromise = fetch(`${API}/phase2/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bot_id: selectedBotId, bot_persona: selectedBotPersona })
    });

    // Animate nodes while waiting
    completeNode('start');
    for (const step of steps) {
      activateNode(step);
      await delay(900);
      completeNode(step);
    }
    activateNode('end');

    const res  = await fetchPromise;
    const data = await res.json();
    completeNode('end');
    hideSpinner();

    const panel = document.getElementById('p2-results');
    document.getElementById('p2-placeholder').classList.add('hidden');
    panel.classList.remove('hidden');

    if (data.error) {
      panel.innerHTML = `<div class="error-box">⚠️ ${data.error}</div>`;
    } else {
      panel.innerHTML = `
        <div class="output-meta">
          <span class="tag tag-bot">🤖 ${data.bot_id}</span>
          <span class="tag tag-topic">📌 ${data.topic}</span>
          <span class="tag tag-search">🔍 ${data.search_query}</span>
        </div>

        <div class="result-label">Search Result</div>
        <div class="result-block">${data.search_results}</div>

        <div class="result-label">Generated Post</div>
        <div class="post-output">"${data.post_content}"</div>
        <p style="font-size:0.72rem;color:var(--muted);margin-top:0.5rem;text-align:right">
          ${data.post_content.length} / 280 chars
        </p>
      `;
    }
  } catch (e) {
    hideSpinner(); resetPipe();
    renderError('p2-results', 'Could not reach the API server. Is api.py running?');
  }
});

// ──────────────────────────────────────────────────────
// PHASE 3 — Comment history
// ──────────────────────────────────────────────────────
document.getElementById('p3-add-comment').addEventListener('click', () => {
  addCommentRow('Bot A', '');
});

function addCommentRow(author = 'Human', text = '') {
  const row = document.createElement('div');
  row.className = 'comment-row';
  row.innerHTML = `
    <select class="comment-author-sel">
      <option ${author==='Bot A'?'selected':''}>Bot A</option>
      <option ${author==='Bot B'?'selected':''}>Bot B</option>
      <option ${author==='Bot C'?'selected':''}>Bot C</option>
      <option ${author==='Human'?'selected':''}>Human</option>
    </select>
    <input class="comment-text-inp" value="${escHtml(text)}" placeholder="Comment text…" />
    <button class="remove-comment-btn" title="Remove">✕</button>
  `;
  row.querySelector('.remove-comment-btn').addEventListener('click', () => row.remove());
  document.getElementById('p3-history').appendChild(row);
}

// Wire existing remove buttons
document.querySelectorAll('.remove-comment-btn').forEach(btn => {
  btn.addEventListener('click', () => btn.closest('.comment-row').remove());
});

document.getElementById('p3-run').addEventListener('click', async () => {
  const persona    = document.getElementById('p3-persona-select').value;
  const parentPost = document.getElementById('p3-post').value.trim();
  const attack     = document.getElementById('p3-attack').value.trim();

  if (!parentPost || !attack) { alert('Parent post and attack reply are required.'); return; }

  const rows = document.querySelectorAll('#p3-history .comment-row');
  const history = [...rows].map(r => ({
    author:  r.querySelector('.comment-author-sel').value,
    content: r.querySelector('.comment-text-inp').value.trim()
  })).filter(c => c.content);

  showSpinner('Generating defense reply…');
  try {
    const res  = await fetch(`${API}/phase3/defend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bot_persona:     persona,
        parent_post:     parentPost,
        comment_history: history,
        human_reply:     attack
      })
    });
    const data = await res.json();
    hideSpinner();

    const panel = document.getElementById('p3-results');
    document.getElementById('p3-placeholder').classList.add('hidden');
    panel.classList.remove('hidden');

    if (data.error) {
      panel.innerHTML = `<div class="error-box">⚠️ ${data.error}</div>`;
    } else {
      panel.innerHTML = `
        <div class="defense-label">🛡️ Bot Defense Response</div>
        <div class="defense-block">${data.reply.replace(/\n/g, '<br>')}</div>
        <p style="font-size:0.72rem;color:var(--muted);margin-top:0.75rem;">
          ✅ Prompt injection successfully neutralized — bot stayed in character.
        </p>
      `;
    }
  } catch (e) {
    hideSpinner();
    renderError('p3-results', 'Could not reach the API server. Is api.py running?');
  }
});

// ──────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────
function renderError(panelId, msg) {
  const panel = document.getElementById(panelId);
  const placeholder = panel.previousElementSibling;
  if (placeholder && placeholder.classList.contains('results-placeholder')) placeholder.classList.add('hidden');
  panel.classList.remove('hidden');
  panel.innerHTML = `<div class="error-box" style="width:100%">⚠️ ${msg}</div>`;
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
