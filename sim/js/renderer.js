/* renderer.js: draws the world through a pan/zoom camera onto the main canvas, plus the minimap.
 * Pure output: reads state, never mutates it (the camera is the only thing it owns).
 *
 * Camera: `cam.x / cam.y` is the world coordinate at the top-left of the view,
 * `cam.zoom` is screen px per world px. Zoom is clamped between "whole world fits" and maxZoom.
 */
'use strict';

const STATE_COLORS = {
  fight: '#ff4d4d',
  hunt: '#ffa640',
  flee: '#ffe066',
  mate: '#ff7ac6',
  goHome: '#7fb3ff',
};

class Renderer {
  constructor(canvas, minimap, world) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.minimap = minimap;
    this.mctx = minimap.getContext('2d');
    this.world = world;
    this.showSenses = false;
    this.showStates = true;
    this.showHomes = true;
    this.follow = false;

    this.cam = { x: 0, y: 0, zoom: 1 };
    this.viewW = 1; this.viewH = 1; this.dpr = 1;
    this.resize();
    this.fit();
    new ResizeObserver(() => this.resize()).observe(canvas);
  }

  // ---- camera -------------------------------------------------------------------
  resize() {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (!w || !h) return;
    const dpr = window.devicePixelRatio || 1;
    this.viewW = w; this.viewH = h; this.dpr = dpr;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);

    const mw = this.minimap.clientWidth || 200;
    const mh = Math.round(mw * this.world.height / this.world.width);
    this.minimap.style.height = mh + 'px';
    this.minimap.width = Math.round(mw * dpr);
    this.minimap.height = Math.round(mh * dpr);
    this.clampCamera();
  }

  fitZoom() {
    return Math.min(this.viewW / this.world.width, this.viewH / this.world.height);
  }

  /** show the whole world */
  fit() {
    this.cam.zoom = this.fitZoom();
    this.cam.x = (this.world.width - this.viewW / this.cam.zoom) / 2;
    this.cam.y = (this.world.height - this.viewH / this.cam.zoom) / 2;
    this.clampCamera();
  }

  clampCamera() {
    const c = this.cam;
    c.zoom = Math.min(CONFIG.camera.maxZoom, Math.max(this.fitZoom(), c.zoom));
    const vw = this.viewW / c.zoom, vh = this.viewH / c.zoom;
    // if the world is narrower than the view, centre it; otherwise keep the view inside the world
    c.x = vw >= this.world.width ? (this.world.width - vw) / 2 : Math.min(this.world.width - vw, Math.max(0, c.x));
    c.y = vh >= this.world.height ? (this.world.height - vh) / 2 : Math.min(this.world.height - vh, Math.max(0, c.y));
  }

  /** zoom by `factor` keeping the world point under screen (sx, sy) fixed */
  zoomAt(sx, sy, factor) {
    const c = this.cam;
    const wx = c.x + sx / c.zoom, wy = c.y + sy / c.zoom;
    c.zoom = Math.min(CONFIG.camera.maxZoom, Math.max(this.fitZoom(), c.zoom * factor));
    c.x = wx - sx / c.zoom;
    c.y = wy - sy / c.zoom;
    this.clampCamera();
  }

  /** pan by a screen-space delta */
  pan(dx, dy) {
    this.cam.x -= dx / this.cam.zoom;
    this.cam.y -= dy / this.cam.zoom;
    this.clampCamera();
  }

  centerOn(wx, wy) {
    this.cam.x = wx - this.viewW / (2 * this.cam.zoom);
    this.cam.y = wy - this.viewH / (2 * this.cam.zoom);
    this.clampCamera();
  }

  /** screen (CSS px, relative to the canvas) -> world */
  screenToWorld(sx, sy) {
    return { x: this.cam.x + sx / this.cam.zoom, y: this.cam.y + sy / this.cam.zoom };
  }

  /** map a mouse event on the canvas to world coordinates */
  toWorld(ev) {
    const rect = this.canvas.getBoundingClientRect();
    return this.screenToWorld(ev.clientX - rect.left, ev.clientY - rect.top);
  }

  /** minimap event -> world */
  minimapToWorld(ev) {
    const rect = this.minimap.getBoundingClientRect();
    return {
      x: (ev.clientX - rect.left) / rect.width * this.world.width,
      y: (ev.clientY - rect.top) / rect.height * this.world.height,
    };
  }

  // ---- drawing --------------------------------------------------------------------
  draw(selected) {
    const ctx = this.ctx, c = this.cam;
    if (this.follow && selected && selected.alive) this.centerOn(selected.x, selected.y);

    // screen space: page background
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.fillStyle = '#080808';
    ctx.fillRect(0, 0, this.viewW, this.viewH);

    // world space
    const s = this.dpr * c.zoom;
    ctx.setTransform(s, 0, 0, s, -c.x * s, -c.y * s);
    ctx.fillStyle = '#0d0d0d';
    ctx.fillRect(0, 0, this.world.width, this.world.height);

    // visible window in world coords (with a margin so big things at the edge still draw)
    const m = 40;
    this.view = { x0: c.x - m, y0: c.y - m, x1: c.x + this.viewW / c.zoom + m, y1: c.y + this.viewH / c.zoom + m };

    this.drawFood();
    if (this.showHomes) this.drawHomes();
    this.drawOrganisms();

    // world edge
    ctx.strokeStyle = 'rgba(255,255,255,0.18)';
    ctx.lineWidth = 2 / c.zoom;
    ctx.strokeRect(0, 0, this.world.width, this.world.height);

    // night tint in screen space so it covers the whole view evenly
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    this.drawNight();

    ctx.setTransform(s, 0, 0, s, -c.x * s, -c.y * s);
    if (selected && selected.alive) this.drawSelection(selected);

    this.drawMinimap(selected);
  }

  inView(x, y) {
    const v = this.view;
    return x >= v.x0 && x <= v.x1 && y >= v.y0 && y <= v.y1;
  }

  drawFood() {
    const ctx = this.ctx;
    const r = CONFIG.food.plantRadius;
    // at low zoom plants would vanish; keep them at least ~1.5 screen px
    const pr = Math.max(r, 0.75 / this.cam.zoom);
    ctx.fillStyle = '#5fd068';
    for (const f of this.world.foods) {
      if (!f.alive || f.kind !== 'plant' || !this.inView(f.x, f.y)) continue;
      ctx.fillRect(f.x - pr, f.y - pr, pr * 2, pr * 2);
    }
    for (const f of this.world.foods) {
      if (!f.alive || f.kind !== 'corpse' || !this.inView(f.x, f.y)) continue;
      const s = f.size;
      ctx.fillStyle = Genetics.hueCss(f.hue, 25, 28, 0.9);
      ctx.fillRect(f.x - s / 2, f.y - s / 2, s, s);
      if (this.cam.zoom > 0.6) {
        ctx.strokeStyle = 'rgba(255,255,255,0.15)';
        ctx.lineWidth = 1 / this.cam.zoom;
        ctx.beginPath();
        ctx.moveTo(f.x - s / 2, f.y - s / 2); ctx.lineTo(f.x + s / 2, f.y + s / 2);
        ctx.moveTo(f.x + s / 2, f.y - s / 2); ctx.lineTo(f.x - s / 2, f.y + s / 2);
        ctx.stroke();
      }
    }
  }

  /** every home as a small hollow diamond in its owner's lineage colour */
  drawHomes() {
    const ctx = this.ctx, zoom = this.cam.zoom;
    const r = Math.max(4, 2.5 / zoom);
    ctx.lineWidth = 1 / zoom;
    for (const o of this.world.organisms) {
      if (!o.alive || !o.home || !this.inView(o.home.x, o.home.y)) continue;
      this.diamond(o.home.x, o.home.y, r, Genetics.hueCss(o.hue, 60, 55, 0.7));
    }
  }

  diamond(x, y, r, color) {
    const ctx = this.ctx;
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y);
    ctx.closePath();
    ctx.stroke();
  }

  drawOrganisms() {
    const ctx = this.ctx, world = this.world, zoom = this.cam.zoom;
    const outline = 1.5 / zoom;
    for (const o of world.organisms) {
      if (!o.alive || !this.inView(o.x, o.y)) continue;
      const s = Math.max(o.drawSize(), 2 / zoom);   // never smaller than ~2 screen px
      const x = o.x - s / 2, y = o.y - s / 2;
      // hungry organisms dim toward a darker tone of their lineage colour
      const light = 58 - 28 * o.hunger;
      ctx.fillStyle = Genetics.hueCss(o.hue, 72, light, o.asleep ? 0.55 : 1);
      ctx.fillRect(x, y, s, s);

      if (o.asleep && zoom > 0.5) {
        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        const d = 1 / zoom;
        ctx.fillRect(o.x - d, o.y - d, 2 * d, 2 * d);
      }

      if (this.showStates) {
        const c = STATE_COLORS[o.state];
        if (c) {
          ctx.strokeStyle = c;
          ctx.lineWidth = outline;
          ctx.strokeRect(x - outline, y - outline, s + 2 * outline, s + 2 * outline);
        }
      }

      if (world.tick - o.lastDamageTick < 6) {
        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.fillRect(x, y, s, s);
      }
    }
  }

  drawNight() {
    const light = this.world.light();
    const alpha = (1 - light) * 0.6;
    if (alpha < 0.02) return;
    this.ctx.fillStyle = `rgba(6, 10, 30, ${alpha.toFixed(3)})`;
    this.ctx.fillRect(0, 0, this.viewW, this.viewH);
  }

  drawSelection(o) {
    const ctx = this.ctx, zoom = this.cam.zoom;
    const s = o.drawSize();

    if (this.showSenses) {
      const R = o.senseRanges();
      const ring = (r, color, dash) => {
        ctx.beginPath();
        ctx.setLineDash(dash.map(d => d / zoom));
        ctx.strokeStyle = color;
        ctx.lineWidth = 1 / zoom;
        ctx.arc(o.x, o.y, r, 0, Math.PI * 2);
        ctx.stroke();
      };
      ring(R.vision, 'rgba(255,255,255,0.45)', []);
      ring(R.smell, 'rgba(120,255,140,0.45)', [6, 4]);
      ring(R.hearing, 'rgba(120,180,255,0.45)', [2, 4]);
      ctx.setLineDash([]);

      if (o.perception) {
        ctx.lineWidth = 1 / zoom;
        ctx.strokeStyle = 'rgba(255,255,255,0.25)';
        for (const p of o.perception.orgs) {
          if (!p.other.alive) continue;
          ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(p.other.x, p.other.y); ctx.stroke();
        }
        ctx.strokeStyle = 'rgba(120,255,140,0.25)';
        for (const p of o.perception.foods) {
          if (!p.item.alive) continue;
          ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(p.item.x, p.item.y); ctx.stroke();
        }
      }
    }

    if (o.home) {
      ctx.strokeStyle = 'rgba(127,179,255,0.55)';
      ctx.lineWidth = 1 / zoom;
      ctx.setLineDash([3 / zoom, 5 / zoom]);
      ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(o.home.x, o.home.y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineWidth = 1.5 / zoom;
      this.diamond(o.home.x, o.home.y, Math.max(7, 4 / zoom), '#ffffff');
      // leash radius, faint
      ctx.strokeStyle = 'rgba(127,179,255,0.18)';
      ctx.lineWidth = 1 / zoom;
      ctx.beginPath(); ctx.arc(o.home.x, o.home.y, o.leashRadius(), 0, Math.PI * 2); ctx.stroke();
    }

    if (o.targetPos && o.state !== 'goHome') {
      ctx.strokeStyle = STATE_COLORS[o.state] || 'rgba(255,255,255,0.6)';
      ctx.lineWidth = 1.5 / zoom;
      ctx.setLineDash([4 / zoom, 3 / zoom]);
      ctx.beginPath(); ctx.moveTo(o.x, o.y); ctx.lineTo(o.targetPos.x, o.targetPos.y); ctx.stroke();
      ctx.setLineDash([]);
    }

    const pad = 4 / zoom;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2 / zoom;
    ctx.strokeRect(o.x - s / 2 - pad, o.y - s / 2 - pad, s + 2 * pad, s + 2 * pad);
  }

  drawMinimap(selected) {
    const ctx = this.mctx, world = this.world;
    const w = this.minimap.width, h = this.minimap.height;
    const sx = w / world.width, sy = h / world.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = 'rgba(13,13,13,0.92)';
    ctx.fillRect(0, 0, w, h);

    const dot = Math.max(1.5, 1.2 * this.dpr);
    for (const o of world.organisms) {
      if (!o.alive) continue;
      ctx.fillStyle = Genetics.hueCss(o.hue, 72, 55, o.asleep ? 0.5 : 0.95);
      ctx.fillRect(o.x * sx - dot / 2, o.y * sy - dot / 2, dot, dot);
    }
    if (selected && selected.alive) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1 * this.dpr;
      ctx.strokeRect(selected.x * sx - 3 * this.dpr, selected.y * sy - 3 * this.dpr, 6 * this.dpr, 6 * this.dpr);
    }

    // current view
    const c = this.cam;
    ctx.strokeStyle = 'rgba(255,255,255,0.7)';
    ctx.lineWidth = 1 * this.dpr;
    ctx.strokeRect(c.x * sx, c.y * sy, (this.viewW / c.zoom) * sx, (this.viewH / c.zoom) * sy);
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
  }
}
