/* genetics.js: genomes, inheritance, mutation and lineage colour.
 *
 * A genome is { geneKey: value in 0..1 }. Real-world units come from CONFIG.genes.
 * Inheritance is Mendelian-ish: per gene, the child takes the mother's copy,
 * the father's copy, or the average, then may mutate. Lineage hue follows the same rule.
 */
'use strict';

const Genetics = {
  randomGenome(rng) {
    const g = {};
    for (const gene of CONFIG.genes) g[gene.key] = rng.next();
    return g;
  },

  /** map normalized gene value -> real units */
  value(genome, key) {
    const gene = CONFIG.geneMap[key];
    return gene.min + genome[key] * (gene.max - gene.min);
  },

  /** child genome from two parents */
  inherit(momG, dadG, rng) {
    const G = CONFIG.genetics;
    const child = {};
    for (const gene of CONFIG.genes) {
      const k = gene.key;
      const r = rng.next();
      let v = r < 0.4 ? momG[k] : r < 0.8 ? dadG[k] : (momG[k] + dadG[k]) / 2;
      if (rng.chance(G.mutationChance)) v += rng.gauss() * G.mutationSigma;
      child[k] = Math.min(1, Math.max(0, v));
    }
    return child;
  },

  /** child lineage hue (degrees) from two parents: mother's, father's or circular midpoint */
  inheritHue(momH, dadH, rng) {
    const G = CONFIG.genetics;
    const r = rng.next();
    let h;
    if (r < 0.4) h = momH;
    else if (r < 0.8) h = dadH;
    else h = Genetics.hueMidpoint(momH, dadH);
    if (rng.chance(G.hueMutationChance)) h += rng.gauss() * G.hueMutationSigma;
    return ((h % 360) + 360) % 360;
  },

  hueMidpoint(a, b) {
    let d = ((b - a + 540) % 360) - 180; // shortest signed arc
    return ((a + d / 2) % 360 + 360) % 360;
  },

  hueDistance(a, b) {
    const d = Math.abs(a - b) % 360;
    return d > 180 ? 360 - d : d;
  },

  /** evenly spaced starting hues so founding lineages are distinct */
  founderHue(index, count, rng) {
    const step = 360 / count;
    return (index * step + rng.range(-step * 0.25, step * 0.25) + 360) % 360;
  },

  hueName(h) {
    const names = ['Red', 'Orange', 'Amber', 'Yellow', 'Lime', 'Green', 'Teal', 'Cyan',
                   'Azure', 'Blue', 'Indigo', 'Violet', 'Purple', 'Magenta', 'Pink', 'Rose'];
    return names[Math.floor((((h % 360) + 360) % 360) / 360 * names.length) % names.length];
  },

  hueCss(h, s = 70, l = 55, a = 1) {
    return `hsla(${h.toFixed(0)}, ${s}%, ${l}%, ${a})`;
  },
};
