/* main.js: bootstraps the app and runs the animation loop.
 * Speed multiplier = simulation ticks per animation frame (fractional speeds accumulate).
 */
'use strict';

class App {
  constructor() {
    const canvas = document.getElementById('world');
    const minimap = document.getElementById('minimap');

    this.world = new World(RNG.randomSeed(), {
      foodDensity: Number(document.getElementById('sldFood').value) || CONFIG.defaults.foodDensity,
      dayLengthSec: Number(document.getElementById('sldDay').value) || CONFIG.defaults.dayLengthSec,
    });
    this.renderer = new Renderer(canvas, minimap, this.world);
    this.charts = new Charts(document.getElementById('stats'), this.world);
    this.ui = new UI(this);

    this.running = true;
    this.speed = CONFIG.speeds[CONFIG.defaults.speedIndex];
    this.accumulator = 0;
    this.lastFrame = performance.now();

    requestAnimationFrame((t) => this.frame(t));
  }

  reset(seed) {
    this.world.reset(seed);
    this.accumulator = 0;
    this.ui.onReset();
  }

  frame(now) {
    // cap catch-up so a background tab does not freeze on return
    const dt = Math.min(100, now - this.lastFrame);
    this.lastFrame = now;

    if (this.running) {
      this.accumulator += this.speed * (dt / (1000 / 60));
      // spend at most ~30 ms per frame on simulation so the UI stays responsive with big populations;
      // if we cannot keep up, drop the backlog and simply run slower than the requested multiplier
      const budgetEnd = performance.now() + 30;
      while (this.accumulator >= 1 && performance.now() < budgetEnd) {
        this.world.step();
        this.accumulator -= 1;
      }
      if (this.accumulator >= 1) this.accumulator = 0;
    }

    this.renderer.draw(this.ui.selected && this.ui.selected.alive ? this.ui.selected : null);
    this.ui.update();
    requestAnimationFrame((t) => this.frame(t));
  }
}

window.addEventListener('DOMContentLoaded', () => { window.app = new App(); });
