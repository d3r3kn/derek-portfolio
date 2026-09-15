/* food.js: things that can be eaten: plants (spawned by the world) and corpses (left by the dead). */
'use strict';

class Food {
  constructor(opts) {
    this.id = opts.id;
    this.kind = opts.kind;            // 'plant' | 'corpse'
    this.x = opts.x;
    this.y = opts.y;
    this.energy = opts.energy;
    this.size = opts.size || 0;       // corpse draw size (px)
    this.hue = opts.hue ?? 0;         // corpse keeps its lineage colour
    this.bornTick = opts.tick || 0;
    this.alive = true;
    this.eaters = new Set();          // ids of organisms that have taken a bite (for logging)
  }

  get radius() {
    return this.kind === 'plant' ? CONFIG.food.plantRadius : this.size / 2;
  }

  update() {
    if (this.kind === 'corpse') {
      this.energy -= CONFIG.energy.corpseDecayPerSec / CONFIG.tickRate;
      if (this.energy <= 1) this.alive = false;
    }
  }
}
