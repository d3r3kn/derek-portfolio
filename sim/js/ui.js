/* ui.js: controls, camera input, HUD, inspector, event log and tabs.
 * Talks to the App (main.js), the World and the Renderer's camera. */
'use strict';

class UI {
  constructor(app) {
    this.app = app;
    this.selected = null;
    this.lastInspector = 0;
    this.logAutoScroll = true;
    this.logFilter = 'all';

    const $ = (id) => document.getElementById(id);
    this.$ = $;
    const world = app.world, renderer = app.renderer;

    // ---- transport
    $('btnPlay').addEventListener('click', () => this.togglePlay());
    $('btnStep').addEventListener('click', () => { app.running = false; world.step(); this.syncPlayButton(); });
    $('btnReset').addEventListener('click', () => app.reset($('inpSeed').value.trim() || RNG.randomSeed()));
    $('btnNewSeed').addEventListener('click', () => app.reset(RNG.randomSeed()));
    $('btnFit').addEventListener('click', () => { renderer.follow = false; $('chkFollow').checked = false; renderer.fit(); });
    document.addEventListener('keydown', (ev) => {
      if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT') return;
      if (ev.code === 'Space') { ev.preventDefault(); this.togglePlay(); }
      if (ev.key === 'f' || ev.key === 'F') { renderer.follow = false; $('chkFollow').checked = false; renderer.fit(); }
    });

    // ---- speed
    const sel = $('selSpeed');
    CONFIG.speeds.forEach((s, i) => {
      const opt = document.createElement('option');
      opt.value = String(i); opt.textContent = s + '×';
      if (i === CONFIG.defaults.speedIndex) opt.selected = true;
      sel.append(opt);
    });
    sel.addEventListener('change', () => { app.speed = CONFIG.speeds[Number(sel.value)]; });

    // ---- world size (restarts the simulation)
    const selSize = $('selSize');
    CONFIG.world.sizes.forEach((s, i) => {
      const opt = document.createElement('option');
      opt.value = String(i); opt.textContent = s.label;
      if (s.width === world.settings.width && s.height === world.settings.height) opt.selected = true;
      selSize.append(opt);
    });
    selSize.addEventListener('change', () => {
      const s = CONFIG.world.sizes[Number(selSize.value)];
      world.settings.width = s.width;
      world.settings.height = s.height;
      world.settings.population = null;          // back to reference density for the new area
      app.reset($('inpSeed').value.trim() || RNG.randomSeed());
    });

    // ---- population (applied on reset)
    const inpPop = $('inpPop');
    inpPop.addEventListener('change', () => {
      const v = Math.max(2, Math.min(20000, Math.round(Number(inpPop.value) || 0)));
      inpPop.value = v;
      world.settings.population = v;
    });

    // ---- live sliders
    this.bindSlider('sldFood', 'valFood', (v) => {
      world.settings.foodDensity = v;
      return `${v.toFixed(1)}× (${world.foodPerSecond.toFixed(0)} /s)`;
    });
    this.bindSlider('sldDay', 'valDay', (v) => { world.settings.dayLengthSec = v; return v + ' s'; });

    $('chkSenses').addEventListener('change', (ev) => { renderer.showSenses = ev.target.checked; });
    $('chkStates').addEventListener('change', (ev) => { renderer.showStates = ev.target.checked; });
    $('chkFollow').addEventListener('change', (ev) => { renderer.follow = ev.target.checked; });
    $('chkHomes').addEventListener('change', (ev) => { renderer.showHomes = ev.target.checked; });

    this.bindCamera();

    // ---- tabs
    for (const btn of document.querySelectorAll('.tab-btn')) {
      btn.addEventListener('click', () => this.showTab(btn.dataset.tab));
    }

    // ---- log
    this.logList = $('logList');
    $('logFilter').addEventListener('change', (ev) => { this.logFilter = ev.target.value; this.rebuildLog(); });
    this.logList.addEventListener('scroll', () => {
      const el = this.logList;
      this.logAutoScroll = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    });
    this.logList.addEventListener('click', (ev) => {
      const row = ev.target.closest('.log-entry');
      if (!row || !row.dataset.refs) return;
      const ids = row.dataset.refs.split(',').map(Number);
      const org = world.organisms.find(o => ids.includes(o.id));
      if (org) { this.select(org); renderer.centerOn(org.x, org.y); }
    });
    world.log.onAdd((entry) => entry ? this.appendLog(entry) : this.rebuildLog());
    this.rebuildLog();

    $('btnDeselect').addEventListener('click', () => this.select(null));
    this.onReset();
  }

  // ---- camera input --------------------------------------------------------------
  bindCamera() {
    const renderer = this.app.renderer, canvas = renderer.canvas, minimap = renderer.minimap;

    canvas.addEventListener('wheel', (ev) => {
      ev.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const factor = Math.exp(-ev.deltaY * CONFIG.camera.wheelSensitivity);
      renderer.zoomAt(ev.clientX - rect.left, ev.clientY - rect.top, factor);
    }, { passive: false });

    // drag to pan, click (without moving) to select
    let drag = null;
    canvas.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      drag = { x: ev.clientX, y: ev.clientY, moved: false };
      canvas.setPointerCapture(ev.pointerId);
    });
    canvas.addEventListener('pointermove', (ev) => {
      if (!drag) return;
      const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < 4) return;
      drag.moved = true;
      renderer.follow = false;
      this.$('chkFollow').checked = false;
      renderer.pan(dx, dy);
      drag.x = ev.clientX; drag.y = ev.clientY;
      canvas.classList.add('dragging');
    });
    const end = (ev) => {
      if (!drag) return;
      if (!drag.moved) {
        const p = renderer.toWorld(ev);
        this.select(this.pickOrganism(p.x, p.y));
      }
      drag = null;
      canvas.classList.remove('dragging');
    };
    canvas.addEventListener('pointerup', end);
    canvas.addEventListener('pointercancel', () => { drag = null; canvas.classList.remove('dragging'); });

    canvas.addEventListener('dblclick', (ev) => {
      const rect = canvas.getBoundingClientRect();
      renderer.zoomAt(ev.clientX - rect.left, ev.clientY - rect.top, 2);
    });

    // minimap: click or drag to move the view
    let mmDown = false;
    const jump = (ev) => { const p = renderer.minimapToWorld(ev); renderer.centerOn(p.x, p.y); };
    minimap.addEventListener('pointerdown', (ev) => {
      mmDown = true; minimap.setPointerCapture(ev.pointerId);
      renderer.follow = false; this.$('chkFollow').checked = false;
      jump(ev);
    });
    minimap.addEventListener('pointermove', (ev) => { if (mmDown) jump(ev); });
    minimap.addEventListener('pointerup', () => { mmDown = false; });
    minimap.addEventListener('pointercancel', () => { mmDown = false; });
  }

  // ---- helpers -----------------------------------------------------------------------
  bindSlider(id, valId, apply) {
    const s = this.$(id), v = this.$(valId);
    const sync = () => { v.textContent = apply(Number(s.value)); };
    s.addEventListener('input', sync);
    sync();
  }

  togglePlay() { this.app.running = !this.app.running; this.syncPlayButton(); }

  syncPlayButton() {
    this.$('btnPlay').textContent = this.app.running ? '⏸ Pause' : '▶ Play';
  }

  onReset() {
    const world = this.app.world;
    this.$('inpSeed').value = world.seed;
    this.$('inpPop').value = world.settings.population ?? world.defaultPopulation;
    this.$('valFood').textContent = `${world.settings.foodDensity.toFixed(1)}× (${world.foodPerSecond.toFixed(0)} /s)`;
    this.select(null);
    this.app.renderer.resize();
    this.app.renderer.fit();
    this.app.running = true;
    this.syncPlayButton();
    this.app.charts.render(true);
  }

  showTab(name) {
    for (const btn of document.querySelectorAll('.tab-btn')) btn.classList.toggle('active', btn.dataset.tab === name);
    for (const pane of document.querySelectorAll('.tab-pane')) pane.hidden = pane.dataset.tab !== name;
    if (name === 'stats') this.app.charts.render(true);
  }

  pickOrganism(x, y) {
    const zoom = this.app.renderer.cam.zoom;
    let best = null, bestD = Infinity;
    for (const o of this.app.world.organisms) {
      if (!o.alive) continue;
      const d = Math.hypot(o.x - x, o.y - y);
      const hit = Math.max(10 / zoom, o.drawSize() / 2 + 4 / zoom);
      if (d < hit && d < bestD) { best = o; bestD = d; }
    }
    return best;
  }

  select(org) {
    this.selected = org;
    this.renderInspector(true);
  }

  // ---- per-frame ---------------------------------------------------------------------
  update() {
    const w = this.app.world;
    this.$('hudPop').textContent = w.organisms.length;
    let plants = 0, corpses = 0;
    for (const f of w.foods) if (f.alive) (f.kind === 'plant' ? plants++ : corpses++);
    this.$('hudFood').textContent = plants;
    this.$('hudCorpses').textContent = corpses;
    this.$('hudZoom').textContent = this.app.renderer.cam.zoom.toFixed(2) + '×';
    this.$('clockDay').textContent = 'Day ' + w.day;
    this.$('clockTime').textContent = w.clockString;
    this.$('clockPhase').textContent = w.isNight() ? '🌙' : '☀️';

    const now = performance.now();
    if (now - this.lastInspector > 100) { this.lastInspector = now; this.renderInspector(); }

    if (!document.querySelector('.tab-pane[data-tab="stats"]').hidden) this.app.charts.render();
  }

  // ---- inspector -----------------------------------------------------------------------
  renderInspector(force = false) {
    const box = this.$('inspectorBody');
    const o = this.selected;
    if (!o) {
      box.innerHTML = '<p class="hint">Click an organism to inspect it. Drag to pan, wheel to zoom, double-click to zoom in, F to fit.</p>';
      this.$('inspectorTitle').textContent = 'Inspector';
      return;
    }
    const title = this.$('inspectorTitle');
    title.innerHTML = `<span class="swatch" style="background:${Genetics.hueCss(o.hue)}"></span> ${o.name}` +
      (o.alive ? '' : ` <span class="dead">dead (${o.deathCause})</span>`);

    const bar = (label, frac, cls, text) => `
      <div class="bar-row"><span class="bar-label">${label}</span>
        <div class="bar"><div class="bar-fill ${cls}" style="width:${(Math.max(0, Math.min(1, frac)) * 100).toFixed(1)}%"></div></div>
        <span class="bar-text">${text}</span></div>`;

    const R = o.alive ? o.senseRanges() : { vision: 0, smell: 0, hearing: 0 };
    const STATE_NAMES = { goHome: 'going home', atHome: 'at home', seekFood: 'seeking food' };
    const stateText = o.asleep ? 'sleeping' : o.groggy ? 'dazed' : (STATE_NAMES[o.state] || o.state);
    let homeText;
    if (o.isNomad) homeText = 'nomad (never settles)';
    else if (!o.home) homeText = `none yet · settles when asleep with ≥ ${(o.foundEnergyFrac() * 100).toFixed(0)}% energy`;
    else homeText = `(${o.home.x.toFixed(0)}, ${o.home.y.toFixed(0)}) · ${o.homeDistance().toFixed(0)} px away · leash ${o.leashRadius().toFixed(0)} px` +
                    ` · returns at ${(o.returnEnergyFrac() * 100).toFixed(0)}% energy` +
                    (o.homeDanger > 0 ? ` · danger ${o.homeDanger.toFixed(1)}` : '');
    const targetText = o.target ? (o.targetKind === 'org' ? o.target.name : (o.target.kind === 'corpse' ? 'a corpse' : 'a plant')) : '-';
    const parents = o.parents.length ? o.parents.map(id => '#' + id).join(' & ') : 'founder';

    let html = `
      <div class="kv"><span>State</span><b class="state-${o.state}">${stateText}</b></div>
      <div class="kv"><span>Target</span><b>${targetText}</b></div>
      <div class="kv"><span>Position</span><b>${o.x.toFixed(0)}, ${o.y.toFixed(0)}</b></div>
      <div class="kv"><span>Home</span><b>${homeText}</b></div>
      <div class="kv"><span>Age</span><b>${o.ageDays.toFixed(2)} days · factor ${o.ageFactor().toFixed(2)}</b></div>
      <div class="kv"><span>Generation</span><b>${o.generation} · parents ${parents}</b></div>
      <div class="kv"><span>Record</span><b>${o.kills} kills · ${o.children} children · ${o.plantsEaten} plants · ${o.corpsesEaten} corpses</b></div>
      ${bar('Energy', o.energyFrac, 'energy', `${o.energy.toFixed(0)} / ${o.capacity.toFixed(0)}`)}
      ${bar('Health', o.healthFrac, 'health', `${o.health.toFixed(0)} / ${o.maxHealth.toFixed(0)}`)}
      ${bar('Fatigue', o.fatigue / 1.5, 'fatigue', o.fatigue.toFixed(2))}
      <div class="kv"><span>Mate cooldown</span><b>${o.mateCooldown > 0 ? (o.mateCooldown / CONFIG.tickRate).toFixed(0) + ' s' : (o.isMature ? 'ready' : 'juvenile')}</b></div>
      <div class="kv"><span>Senses now</span><b>👁 ${R.vision.toFixed(0)} · 👃 ${R.smell.toFixed(0)} · 👂 ${R.hearing.toFixed(0)} px</b></div>
      <div class="kv"><span>Perceiving</span><b>${o.perception ? `${o.perception.orgs.length} organisms · ${o.perception.foods.length} food` : '-'}</b></div>
      <div class="kv"><span>Power / noise</span><b>${o.power().toFixed(2)} / ${o.noiseLevel().toFixed(2)}</b></div>
      <table class="genes"><thead><tr><th>Gene</th><th>Base</th><th>Now</th></tr></thead><tbody>`;
    for (const g of CONFIG.genes) {
      const base = o.traits[g.key], now = o.eff(g.key);
      const pct = ((o.genome[g.key]) * 100).toFixed(0);
      html += `<tr><td>${g.label}</td>
        <td>${base.toFixed(g.dp)}${g.unit ? ' ' + g.unit : ''} <span class="pct">(${pct}%)</span></td>
        <td>${g.ages ? now.toFixed(g.dp) : '·'}</td></tr>`;
    }
    html += '</tbody></table>';
    box.innerHTML = html;
  }

  // ---- log -------------------------------------------------------------------------------
  entryVisible(entry) {
    return this.logFilter === 'all' || entry.category === this.logFilter;
  }

  appendLog(entry) {
    if (!this.entryVisible(entry)) return;
    const list = this.logList;
    list.append(this.logRow(entry));
    while (list.children.length > CONFIG.log.max) list.removeChild(list.firstChild);
    if (this.logAutoScroll) list.scrollTop = list.scrollHeight;
  }

  rebuildLog() {
    const list = this.logList;
    list.innerHTML = '';
    for (const e of this.app.world.log.entries) if (this.entryVisible(e)) list.append(this.logRow(e));
    list.scrollTop = list.scrollHeight;
    this.logAutoScroll = true;
  }

  logRow(entry) {
    const row = document.createElement('div');
    row.className = `log-entry cat-${entry.category}`;
    if (entry.refs.length) row.dataset.refs = entry.refs.join(',');
    const t = document.createElement('span');
    t.className = 'log-time';
    t.textContent = `D${entry.day} ${entry.clock}`;
    const txt = document.createElement('span');
    txt.textContent = entry.text;
    row.append(t, txt);
    return row;
  }
}
