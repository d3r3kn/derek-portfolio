/* charts.js: statistics panel: stat tiles, population / plant time series and one sparkline per gene.
 * Plain canvas, no libraries. All charts share a hover crosshair (same x = same moment in time).
 */
'use strict';

const CHART_STYLE = {
  surface: '#1a1a19',
  grid: '#2c2c2a',
  axis: '#383835',
  muted: '#898781',
  text: '#ffffff',
  textSecondary: '#c3c2b7',
  series: '#3987e5',
  crosshair: 'rgba(255,255,255,0.35)',
};

class Charts {
  constructor(root, world) {
    this.root = root;
    this.world = world;
    this.hoverFrac = null;   // 0..1 across the time axis, shared by every chart
    this.lastRender = -1;
    this.build();
  }

  get stats() { return this.world.stats; }

  build() {
    const root = this.root;
    root.innerHTML = '';

    this.tiles = {};
    const tileRow = el('div', 'tiles');
    const tileDefs = [
      ['population', 'Population'], ['plants', 'Plants'], ['corpses', 'Corpses'],
      ['births', 'Births'], ['starvation', 'Starved'], ['killed', 'Killed'],
      ['ambushed', 'Killed asleep'], ['fights', 'Fights'],
      ['homed', 'Homed'], ['homesFounded', 'Homes founded'],
      ['relocations', 'Home moves'], ['abandonments', 'Homes abandoned'],
    ];
    for (const [key, label] of tileDefs) {
      const t = el('div', 'tile');
      const v = el('div', 'tile-value'); v.textContent = '0';
      const l = el('div', 'tile-label'); l.textContent = label;
      t.append(v, l);
      tileRow.append(t);
      this.tiles[key] = v;
    }
    root.append(tileRow);

    this.popChart = this.makeChart(root, 'Population', 110);
    this.plantChart = this.makeChart(root, 'Plants on the ground', 70);
    this.homedChart = this.makeChart(root, 'Share of organisms with a home', 70);

    const geneHeader = el('div', 'chart-section-title');
    geneHeader.textContent = 'Average genes (living population)';
    root.append(geneHeader);
    const grid = el('div', 'gene-grid');
    this.geneCharts = {};
    for (const g of CONFIG.genes) {
      this.geneCharts[g.key] = this.makeChart(grid, g.label, 46, true);
    }
    root.append(grid);

    this.tooltip = el('div', 'chart-tooltip');
    this.tooltip.hidden = true;
    root.append(this.tooltip);

    root.addEventListener('mouseleave', () => { this.hoverFrac = null; this.tooltip.hidden = true; this.render(true); });
  }

  makeChart(parent, title, height, compact = false) {
    const wrap = el('div', compact ? 'chart compact' : 'chart');
    const head = el('div', 'chart-head');
    const t = el('span', 'chart-title'); t.textContent = title;
    const v = el('span', 'chart-value'); v.textContent = '';
    head.append(t, v);
    const canvas = document.createElement('canvas');
    canvas.className = 'chart-canvas';
    canvas.style.height = height + 'px';
    wrap.append(head, canvas);
    parent.append(wrap);

    canvas.addEventListener('mousemove', (ev) => {
      const rect = canvas.getBoundingClientRect();
      this.hoverFrac = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
      this.tooltip.hidden = false;
      const rootRect = this.root.getBoundingClientRect();
      this.tooltip.style.left = (ev.clientX - rootRect.left + 12) + 'px';
      this.tooltip.style.top = (ev.clientY - rootRect.top + this.root.scrollTop + 12) + 'px';
      this.render(true);
    });
    return { wrap, canvas, value: v, height };
  }

  hoverIndex(n) {
    if (this.hoverFrac === null || n === 0) return -1;
    return Math.min(n - 1, Math.round(this.hoverFrac * (n - 1)));
  }

  render(force = false) {
    const stats = this.stats;
    if (!force && !stats.dirty) return;
    stats.dirty = false;
    const samples = stats.samples;
    const n = samples.length;
    const hi = this.hoverIndex(n);
    const s = samples[hi >= 0 ? hi : n - 1] || null;

    // tiles (always live values)
    const latest = stats.latest();
    this.tiles.population.textContent = this.world.organisms.length;
    this.tiles.plants.textContent = latest ? latest.plants : 0;
    this.tiles.corpses.textContent = latest ? latest.corpses : 0;
    this.tiles.births.textContent = stats.counters.births;
    this.tiles.starvation.textContent = stats.deaths.starvation;
    this.tiles.killed.textContent = stats.deaths.killed;
    this.tiles.ambushed.textContent = stats.deaths.ambushed;
    this.tiles.fights.textContent = stats.counters.fights;
    const orgs = this.world.organisms;
    let homedNow = 0;
    for (const o of orgs) if (o.home) homedNow++;
    this.tiles.homed.textContent = orgs.length ? Math.round(100 * homedNow / orgs.length) + '%' : 'n/a';
    this.tiles.homesFounded.textContent = stats.counters.homesFounded;
    this.tiles.relocations.textContent = stats.counters.relocations;
    this.tiles.abandonments.textContent = stats.counters.abandonments;

    this.drawSeries(this.popChart, samples.map(x => x.population), hi, { minZero: true, fmt: v => String(Math.round(v)) });
    this.drawSeries(this.plantChart, samples.map(x => x.plants), hi, { minZero: true, fmt: v => String(Math.round(v)) });
    this.drawSeries(this.homedChart, samples.map(x => x.homed * 100), hi, { minZero: true, fmt: v => Math.round(v) + '%' });

    for (const g of CONFIG.genes) {
      const vals = samples.map(x => g.min + x.genes[g.key] * (g.max - g.min));
      this.drawSeries(this.geneCharts[g.key], vals, hi, { fmt: v => v.toFixed(g.dp) + (g.unit ? ' ' + g.unit : '') });
    }

    if (s && hi >= 0) {
      this.tooltip.textContent = `Day ${s.day.toFixed(2)} · pop ${s.population} · plants ${s.plants}`;
    }
  }

  drawSeries(chart, values, hoverIdx, opts) {
    const canvas = chart.canvas;
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 300, cssH = chart.height;
    if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    ctx.fillStyle = CHART_STYLE.surface;
    ctx.fillRect(0, 0, cssW, cssH);

    const n = values.length;
    const valid = values.filter(v => Number.isFinite(v));
    if (n < 2 || valid.length === 0) {
      chart.value.textContent = valid.length ? opts.fmt(valid[valid.length - 1]) : '-';
      return;
    }

    let min = Math.min(...valid), max = Math.max(...valid);
    if (opts.minZero) min = 0;
    if (max - min < 1e-9) { max = min + 1; }
    const pad = (max - min) * 0.08;
    const lo = opts.minZero ? 0 : min - pad, hi = max + pad;

    // left gutter sized to the axis labels so they never sit on top of the line
    ctx.font = '10px system-ui, sans-serif';
    const topLabel = opts.fmt(hi), bottomLabel = opts.fmt(lo);
    const gutter = Math.ceil(Math.max(ctx.measureText(topLabel).width, ctx.measureText(bottomLabel).width)) + 8;
    const padL = gutter, padR = 4, padT = 6, padB = 4;
    const plotW = cssW - padL - padR, plotH = cssH - padT - padB;
    const X = i => padL + (i / (n - 1)) * plotW;
    const Y = v => padT + (1 - (v - lo) / (hi - lo)) * plotH;

    // recessive gridlines
    ctx.strokeStyle = CHART_STYLE.grid;
    ctx.lineWidth = 1;
    for (let k = 0; k <= 2; k++) {
      const y = padT + (k / 2) * plotH + 0.5;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(cssW - padR, y); ctx.stroke();
    }

    // series
    ctx.strokeStyle = CHART_STYLE.series;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < n; i++) {
      const v = values[i];
      if (!Number.isFinite(v)) { started = false; continue; }
      if (!started) { ctx.moveTo(X(i), Y(v)); started = true; }
      else ctx.lineTo(X(i), Y(v));
    }
    ctx.stroke();

    // axis extremes as muted labels in the gutter
    ctx.fillStyle = CHART_STYLE.muted;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText(topLabel, padL - 5, padT);
    ctx.textBaseline = 'bottom';
    ctx.fillText(bottomLabel, padL - 5, cssH - padB);
    ctx.textAlign = 'left';

    // hover crosshair + marker
    const idx = hoverIdx >= 0 ? hoverIdx : n - 1;
    const hv = values[idx];
    if (hoverIdx >= 0) {
      ctx.strokeStyle = CHART_STYLE.crosshair;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(X(idx) + 0.5, padT); ctx.lineTo(X(idx) + 0.5, cssH - padB); ctx.stroke();
      if (Number.isFinite(hv)) {
        ctx.fillStyle = CHART_STYLE.series;
        ctx.beginPath(); ctx.arc(X(idx), Y(hv), 3.5, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = CHART_STYLE.surface; ctx.lineWidth = 2; ctx.stroke();
      }
    }
    chart.value.textContent = Number.isFinite(hv) ? opts.fmt(hv) : '-';
  }
}

function el(tag, className) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  return e;
}
