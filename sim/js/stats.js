/* stats.js: time series of population / food / average genes, plus tallies of deaths and events.
 * Samples are taken every CONFIG.stats.sampleInterval ticks; when the series gets long it is
 * decimated (every other sample dropped, interval doubled) so the whole run always fits.
 */
'use strict';

class Stats {
  constructor() { this.reset(); }

  reset() {
    this.samples = [];
    this.stride = 1;
    this.deaths = { starvation: 0, killed: 0, ambushed: 0 };
    this.counters = { births: 0, fights: 0, kills: 0, plantsEaten: 0, corpsesEaten: 0,
                      homesFounded: 0, relocations: 0, abandonments: 0 };
    this.dirty = true;
  }

  recordDeath(cause) { this.deaths[cause] = (this.deaths[cause] || 0) + 1; this.dirty = true; }
  count(key, n = 1) { this.counters[key] = (this.counters[key] || 0) + n; this.dirty = true; }
  get totalDeaths() { return Object.values(this.deaths).reduce((a, b) => a + b, 0); }

  maybeSample(world) {
    if (world.tick % (CONFIG.stats.sampleInterval * this.stride) !== 0) return;
    this.sample(world);
  }

  sample(world, force = false) {
    const orgs = world.organisms;
    const genes = {};
    for (const g of CONFIG.genes) {
      let sum = 0;
      for (const o of orgs) sum += o.genome[g.key];
      genes[g.key] = orgs.length ? sum / orgs.length : NaN;
    }
    let plants = 0, corpses = 0;
    for (const f of world.foods) if (f.alive) (f.kind === 'plant' ? plants++ : corpses++);
    let homed = 0;
    for (const o of orgs) if (o.home) homed++;

    this.samples.push({
      tick: world.tick,
      day: world.tick / world.ticksPerDay,
      population: orgs.length,
      plants, corpses,
      homed: orgs.length ? homed / orgs.length : NaN,
      genes,
    });

    if (this.samples.length > CONFIG.stats.maxSamples && !force) {
      this.samples = this.samples.filter((_, i) => i % 2 === 0);
      this.stride *= 2;
    }
    this.dirty = true;
  }

  latest() { return this.samples[this.samples.length - 1]; }
}
