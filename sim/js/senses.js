/* senses.js: perception. Turns the world into what one organism can actually detect.
 *
 * Three channels:
 *   sight: anything within vision range (shrinks at night)
 *   smell: food within smell range (corpses reek further), organisms within a fraction of it
 *   hearing: organisms within hearing range scaled by how loud they currently are
 *
 * Sleeping organisms perceive at a fraction of their normal ranges.
 */
'use strict';

const Senses = {
  /**
   * @returns {{ foods: {item, dist, dx, dy}[], orgs: {other, dist, dx, dy, channels: string[]}[], ranges }}
   */
  perceive(org, world) {
    const R = org.senseRanges();
    const S = CONFIG.senses;
    const maxR = Math.max(R.vision, R.smell * S.corpseScent, R.hearing);
    const foods = [], orgs = [];

    world.foodGrid.query(org.x, org.y, maxR, (f) => {
      if (!f.alive) return;
      const dx = f.x - org.x, dy = f.y - org.y;
      const dist = Math.hypot(dx, dy);
      const scent = R.smell * (f.kind === 'corpse' ? S.corpseScent : S.plantScent);
      if (dist <= R.vision || dist <= scent) foods.push({ item: f, dist, dx, dy });
    });

    world.orgGrid.query(org.x, org.y, maxR, (o) => {
      if (o === org || !o.alive) return;
      const dx = o.x - org.x, dy = o.y - org.y;
      const dist = Math.hypot(dx, dy);
      const channels = [];
      if (dist <= R.vision) channels.push('sight');
      if (dist <= R.hearing * o.noiseLevel()) channels.push('sound');
      if (dist <= R.smell * S.organismScent) channels.push('scent');
      if (channels.length) orgs.push({ other: o, dist, dx, dy, channels });
    });

    return { foods, orgs, ranges: R };
  },
};
