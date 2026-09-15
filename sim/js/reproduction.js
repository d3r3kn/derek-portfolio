/* reproduction.js: two well-fed, awake, mature organisms in contact produce a child.
 * Each gene is inherited Mendelian-style (see genetics.js); lineage hue follows the same rule.
 */
'use strict';

const Reproduction = {
  canMate(o) {
    const M = CONFIG.mating;
    return o.alive && !o.asleep && !o.groggy && o.isMature && o.mateCooldown === 0 &&
           o.energyFrac >= M.minEnergyFrac && o.state !== 'fight' && o.state !== 'flee';
  },

  /** returns the child, or null if mating did not happen */
  tryMate(a, b, world) {
    const M = CONFIG.mating;
    if (!Reproduction.canMate(a) || !Reproduction.canMate(b)) return null;

    const cooldown = Math.round(M.cooldownDays * world.ticksPerDay);
    if (world.organisms.length >= world.maxPopulation) {
      // overcrowded: nothing comes of it, try again later
      a.mateCooldown = b.mateCooldown = Math.round(cooldown * 0.2);
      return null;
    }

    a.energy -= a.capacity * M.costFrac;
    b.energy -= b.capacity * M.costFrac;
    a.mateCooldown = b.mateCooldown = cooldown;

    const rng = world.rng;
    const [mom, dad] = rng.chance(0.5) ? [a, b] : [b, a];
    const child = world.spawnOrganism({
      x: (a.x + b.x) / 2 + rng.range(-6, 6),
      y: (a.y + b.y) / 2 + rng.range(-6, 6),
      genome: Genetics.inherit(mom.genome, dad.genome, rng),
      hue: Genetics.inheritHue(mom.hue, dad.hue, rng),
      generation: Math.max(a.generation, b.generation) + 1,
      parents: [mom.id, dad.id],
      energyFrac: M.childEnergyFrac,
    });

    a.children++; b.children++;
    a.state = b.state = 'wander';
    a.clearTarget(); b.clearTarget();

    world.stats.count('births');
    world.log.add('birth', `${a.name} and ${b.name} had a child: ${child.name} (gen ${child.generation})`, [a, b, child]);
    return child;
  },
};
