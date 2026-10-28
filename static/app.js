const $ = id => document.getElementById(id);
const chat = $('chat'), scroller = $('scroll'), txt = $('txt'), pick = $('pick');
const sendBtn = $('send'), chip = $('chip');
const PLACEHOLDER = 'Attach a resume, paste text, or ask a question...';
let token = localStorage.getItem('token');
let mode = 'login';
let file = null, busy = false, jdMode = false;
let currentChat = null;

const DOTS = '<div class="dots"><i></i><i></i><i></i></div>';
const esc = s => { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; };
const pretty = r => r.replace(/-/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
const toBottom = () => { scroller.scrollTop = scroller.scrollHeight; };

// ---------- Markdown (AI ke jawab ke liye) ----------
function md(src) {
  const inline = s => s
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>');
  let out = '', list = null, inTable = false, first = true;
  const closeList = () => { if (list) { out += '</' + list + '>'; list = null; } };
  const closeTable = () => { if (inTable) { out += '</table></div>'; inTable = false; } };

  for (const raw of esc(src).split('\n')) {
    const l = raw.trimEnd();
    let m;

    if (/^\s*\|.*\|\s*$/.test(l)) {                       // table row
      if (/^\s*\|[\s:|-]+\|\s*$/.test(l)) continue;       // |---|---| line
      closeList();
      if (!inTable) { out += '<div class="tw"><table>'; inTable = true; first = true; }
      const tag = first ? 'th' : 'td'; first = false;
      out += '<tr>' + l.trim().slice(1, -1).split('|')
        .map(c => '<' + tag + '>' + inline(c.trim()) + '</' + tag + '>').join('') + '</tr>';
      continue;
    }
    closeTable();

    if ((m = l.match(/^\s*[-*•]\s+(.*)/))) {
      if (list !== 'ul') { closeList(); out += '<ul>'; list = 'ul'; }
      out += '<li>' + inline(m[1]) + '</li>';
    } else if ((m = l.match(/^\s*\d+[.)]\s+(.*)/))) {
      if (list !== 'ol') { closeList(); out += '<ol>'; list = 'ol'; }
      out += '<li>' + inline(m[1]) + '</li>';
    } else if ((m = l.match(/^#{1,6}\s+(.*)/))) {
      closeList(); out += '<h4 class="mdh">' + inline(m[1]) + '</h4>';
    } else if (l.trim() === '') {
      closeList();
    } else {
      closeList(); out += '<p>' + inline(l) + '</p>';
    }
  }
  closeList(); closeTable();
  return out;
}
const answerHtml = t => '<div class="answer">' + md(t) + '</div>';

// ---------- API helper (token + chat id bhejta hai) ----------
async function api(path, opts = {}) {
  const h = Object.assign({}, opts.headers);
  if (token) h.Authorization = 'Bearer ' + token;
  if (currentChat) h['X-Chat-Id'] = String(currentChat);
  opts.headers = h;
  const r = await fetch('/api' + path, opts);
  const data = await r.json().catch(() => ({}));
  if (r.status === 401 && token) {
    logout();
    throw new Error('Session expired. Please log in again.');
  }
  if (!r.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Please fill all the fields correctly');
  }
  return data;
}

// ---------- Login / signup ----------
function setMode(m) {
  mode = m;
  $('tab-login').classList.toggle('active', m === 'login');
  $('tab-signup').classList.toggle('active', m === 'signup');
  $('a-name').hidden = m === 'login';
  $('a-submit').textContent = m === 'login' ? 'Log in' : 'Create account';
  $('a-pass').autocomplete = m === 'login' ? 'current-password' : 'new-password';
  $('a-err').textContent = '';
}
$('tab-login').onclick = () => setMode('login');
$('tab-signup').onclick = () => setMode('signup');

async function authSubmit() {
  $('a-err').textContent = '';
  const body = { email: $('a-email').value, password: $('a-pass').value };
  if (mode === 'signup') body.name = $('a-name').value;
  try {
    const d = await api('/' + mode, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    token = d.token;
    localStorage.setItem('token', token);
    $('a-pass').value = '';
    currentChat = null;
    await openApp();
  } catch (e) { $('a-err').textContent = e.message; }
}
$('a-submit').onclick = authSubmit;
$('a-pass').addEventListener('keydown', e => { if (e.key === 'Enter') authSubmit(); });

function logout() {
  token = null;
  currentChat = null;
  localStorage.removeItem('token');
  clearChatUI();
  $('chatlist').innerHTML = '';
  closeSide();
  $('app').hidden = true;
  $('auth').hidden = false;
}
$('logout').onclick = logout;

// ---------- Chat UI ----------
function userMsg(text) {
  $('welcome').hidden = true;
  const row = document.createElement('div');
  row.className = 'row user';
  const b = document.createElement('div');
  b.className = 'bubble';
  b.textContent = text;
  row.appendChild(b);
  chat.appendChild(row);
  toBottom();
}

function botMsg(html) {
  $('welcome').hidden = true;
  const row = document.createElement('div');
  row.className = 'row bot';
  row.innerHTML = '<div class="avatar">R</div><div class="content"></div>';
  row.querySelector('.content').innerHTML = html;
  chat.appendChild(row);
  toBottom();
  return row;
}

function setJdMode(on) {
  jdMode = on;
  txt.placeholder = on ? 'Paste the job description here...' : PLACEHOLDER;
}

function clearChatUI() {
  chat.querySelectorAll('.row').forEach(r => r.remove());
  $('welcome').hidden = false;
  clearFile();
  setJdMode(false);
  txt.value = '';
}

const tags = (arr, cls) => arr.map(x => '<span class="tag ' + (cls || '') + '">' + esc(x) + '</span>').join('');

function resultHtml(res) {
  const max = Math.max(...res.predictions.map(p => p.percent)) || 1;
  const rows = res.predictions.map((p, i) =>
    '<div class="role"><div class="top"><span><b>' + esc(pretty(p.role)) + '</b>' +
    (i === 0 ? '<span class="badge">Top match</span>' : '') + '</span><span>' + p.percent + '%</span></div>' +
    '<div class="bar"><u style="width:' + (p.percent / max * 100) + '%"></u></div></div>'
  ).join('');

  const s = res.suggestions;
  const hcol = s.health >= 75 ? 'var(--pri)' : s.health >= 50 ? '#d98a1f' : 'var(--bad)';

  let html =
    '<p class="res-title">Your resume best matches these fields</p>' +
    '<p class="res-sub">' + esc(res.filename) + ' &middot; ' + res.words + ' words read</p>' + rows +
    '<p class="note">Probability is split across 24 categories, so the percentages look small.</p>' +

    '<h3 class="sec">Resume health</h3>' +
    '<div class="health"><div class="hnum" style="color:' + hcol + '">' + s.health + '<small>/100</small></div>' +
    '<div class="hbar"><u style="width:' + s.health + '%;background:' + hcol + '"></u></div></div>' +
    '<div>' + tags(s.passed, 'ok') + tags(s.failed, 'no') + '</div>';

  if (s.tips.length)
    html += '<h3 class="sec">How to improve</h3><ul class="tips">' +
      s.tips.map(t => '<li>' + esc(t) + '</li>').join('') + '</ul>';

  html += '<h3 class="sec">Skills for ' + esc(s.field) + '</h3>' +
    (s.skills_have.length ? '<div class="lbl">You already have</div><div>' + tags(s.skills_have, 'ok') + '</div>' : '') +
    (s.skills_missing.length ? '<div class="lbl">Worth learning</div><div>' + tags(s.skills_missing, 'no') + '</div>' : '');

  html += '<h3 class="sec">Roles you can apply for</h3><div>' + tags(s.roles) + '</div>' +
    '<h3 class="sec">Companies (examples)</h3><div>' + tags(s.companies) + '</div>' +
    '<p class="note">Company names are only examples. Check their careers pages for current openings before applying.</p>' +

    '<div class="qchips">' +
    '<button data-jd="1">Match with a job</button>' +
    '<button data-q="Write a strong summary for my resume">Write summary</button>' +
    '<button data-q="Give me 5 important interview questions for this field">Interview prep</button>' +
    '<button data-q="What should I learn in the next 3 months? Give a short plan">Learning plan</button>' +
    '</div>';
  return html;
}

function jdHtml(r) {
  const col = r.match >= 70 ? 'var(--pri)' : r.match >= 40 ? '#d98a1f' : 'var(--bad)';
  return '<p class="res-title">Job match: ' + esc(r.verdict) + '</p>' +
    '<div class="health"><div class="hnum" style="color:' + col + '">' + r.match + '<small>%</small></div>' +
    '<div class="hbar"><u style="width:' + r.match + '%;background:' + col + '"></u></div></div>' +
    '<p class="note">Keyword match shows how many important keywords of the job description appear in your resume. ' +
    'Overall text similarity (TF-IDF + cosine): ' + r.similarity + '%.</p>' +
    '<h3 class="sec">Keywords you have</h3><div>' + (r.matched.length ? tags(r.matched, 'ok') : '<span class="note">None found</span>') + '</div>' +
    '<h3 class="sec">Keywords missing</h3><div>' + (r.missing.length ? tags(r.missing, 'no') : '<span class="note">Nothing missing, great!</span>') + '</div>' +
    '<p class="note">Add a missing keyword only if you truly have that skill or experience. Do not copy keywords just to raise the score.</p>' +
    '<div class="qchips"><button data-jd="1">Match with another job</button></div>';
}

// ---------- File handling ----------
function setFile(f) {
  if (!f) return;
  if (!/\.(pdf|docx|txt)$/i.test(f.name)) { botMsg('<span class="err">Please upload a PDF, DOCX or TXT file only.</span>'); return; }
  file = f;
  $('chipname').textContent = '📎 ' + f.name;
  chip.hidden = false;
  txt.focus();
}
function clearFile() { file = null; pick.value = ''; chip.hidden = true; }

// ---------- Talking to the server ----------
async function analyse(path, opts, label, render = resultHtml) {
  userMsg(label);
  const wait = botMsg(DOTS);
  try {
    const data = await api(path, opts);
    wait.querySelector('.content').innerHTML = render(data);
  } catch (e) {
    wait.querySelector('.content').innerHTML = '<span class="err">Error: ' + esc(e.message) + '</span>';
  }
}

async function askAI(text) {
  userMsg(text);
  const wait = botMsg(DOTS);
  try {
    const data = await api('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    wait.querySelector('.content').innerHTML = answerHtml(data.reply);
  } catch (e) {
    wait.querySelector('.content').innerHTML = '<span class="err">Error: ' + esc(e.message) + '</span>';
  }
}

async function submit(forcedText) {
  if (busy) return;
  const t = (forcedText ?? txt.value).trim();
  if (!file && !t) return;
  busy = true; sendBtn.disabled = true;

  const f = file;
  const wasJd = jdMode;
  txt.value = ''; txt.style.height = 'auto'; clearFile(); setJdMode(false);

  if (f) {
    const fd = new FormData(); fd.append('file', f);
    await analyse('/predict', { method: 'POST', body: fd }, '📎 ' + f.name);
  } else if (wasJd) {
    await analyse('/jd-match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: t })
    }, 'Job description: ' + t.slice(0, 150) + (t.length > 150 ? '...' : ''), jdHtml);
  } else if (t.split(/\s+/).length >= 120) {
    // long text = a pasted resume
    await analyse('/predict-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: t })
    }, t.slice(0, 200) + '...');
  } else {
    await askAI(t);
  }

  busy = false; sendBtn.disabled = false; toBottom();
  renderSide();   // sidebar me chat ka title update ho jaaye
}

// ---------- Confirm popup ----------
function confirmBox(title, text, okLabel) {
  return new Promise(resolve => {
    const modal = $('modal'), ok = $('mok'), cancel = $('mcancel');
    $('mtitle').textContent = title;
    $('mtext').textContent = text;
    ok.textContent = okLabel || 'OK';
    modal.hidden = false;
    cancel.focus();

    const finish = v => {
      modal.hidden = true;
      ok.onclick = cancel.onclick = modal.onclick = null;
      document.removeEventListener('keydown', onKey);
      resolve(v);
    };
    const onKey = e => { if (e.key === 'Escape') finish(false); };

    ok.onclick = () => finish(true);
    cancel.onclick = () => finish(false);
    modal.onclick = e => { if (e.target === modal) finish(false); };
    document.addEventListener('keydown', onKey);
  });
}

// ---------- Sidebar ----------
function closeSide() { document.body.classList.remove('side-open'); }

async function renderSide() {
  try {
    const d = await api('/chats');
    const list = $('chatlist');
    list.innerHTML = '';
    d.chats.forEach(c => {
      const row = document.createElement('div');
      row.className = 'citem' + (c.id === currentChat ? ' active' : '');

      const b = document.createElement('button');
      b.className = 'ctitle';
      b.textContent = c.title;
      b.onclick = () => { if (!busy && c.id !== currentChat) loadChat(c.id); closeSide(); };

      const x = document.createElement('button');
      x.className = 'cdel';
      x.textContent = '✕';
      x.title = 'Delete chat';
      x.onclick = async e => {
        e.stopPropagation();
        if (busy) return;
        if (!await confirmBox('Delete chat?', '"' + c.title + '" and its results will be permanently deleted.', 'Delete')) return;
        try {
          await api('/chats/' + c.id, { method: 'DELETE' });
          if (c.id === currentChat) await loadChat(null); else await renderSide();
        } catch (err) { /* ignore */ }
      };

      row.append(b, x);
      list.appendChild(row);
    });
  } catch (e) { /* ignore */ }
}

// ---------- Open a chat (restores saved messages) ----------
async function loadChat(id) {
  currentChat = id;
  clearChatUI();
  try {
    const h = await api('/history');
    currentChat = h.chat_id;
    h.messages.forEach(m => {
      if (m.role === 'user') userMsg(m.content);
      else if (m.kind === 'result') botMsg(resultHtml(m.content));
      else if (m.kind === 'jd') botMsg(jdHtml(m.content));
      else botMsg(answerHtml(m.content));
    });
    toBottom();
  } catch (e) { /* if the session expired, api() already showed the login screen */ }
  await renderSide();
}

async function openApp() {
  $('auth').hidden = true;
  $('app').hidden = false;
  try {
    const me = await api('/me');
    $('who').textContent = me.name;
    await loadChat(null);
  } catch (e) { /* handled in api() */ }
}

// ---------- Buttons ----------
$('attach').onclick = () => pick.click();
$('c-upload').onclick = () => pick.click();
$('c-paste').onclick = () => txt.focus();
$('chipx').onclick = clearFile;
pick.onchange = () => setFile(pick.files[0]);
sendBtn.onclick = () => submit();
chat.addEventListener('click', e => {
  const b = e.target.closest('.qchips button');
  if (!b) return;
  if (b.dataset.jd) {
    setJdMode(true);
    botMsg('<div class="answer"><p>Paste the job description in the box below and press send.</p></div>');
    txt.focus();
  } else if (b.dataset.q) {
    submit(b.dataset.q);
  }
});
$('newchat').onclick = async () => {
  if (busy) return;
  try {
    const d = await api('/chats/new', { method: 'POST' });
    await loadChat(d.chat_id);
    closeSide();
  } catch (e) { /* ignore */ }
};
$('menu').onclick = () => document.body.classList.toggle('side-open');
$('scrim').onclick = closeSide;

txt.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } });
txt.addEventListener('input', () => { txt.style.height = 'auto'; txt.style.height = Math.min(txt.scrollHeight, 150) + 'px'; });

window.addEventListener('dragover', e => { e.preventDefault(); document.body.classList.add('drag'); });
window.addEventListener('dragleave', e => { if (!e.relatedTarget) document.body.classList.remove('drag'); });
window.addEventListener('drop', e => { e.preventDefault(); document.body.classList.remove('drag'); setFile(e.dataTransfer.files[0]); });

// ---------- Start ----------
if (token) openApp(); else $('auth').hidden = false;