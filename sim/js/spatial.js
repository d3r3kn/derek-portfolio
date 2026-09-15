/* spatial.js: uniform grid for cheap neighbourhood queries. Rebuilt every tick. */
'use strict';

class SpatialHash {
  constructor(width, height, cellSize) {
    this.width = width;
    this.height = height;
    this.cell = cellSize;
    this.cols = Math.ceil(width / cellSize);
    this.rows = Math.ceil(height / cellSize);
    this.cells = Array.from({ length: this.cols * this.rows }, () => []);
  }

  clear() {
    for (const c of this.cells) c.length = 0;
  }

  _col(x) { return Math.min(this.cols - 1, Math.max(0, Math.floor(x / this.cell))); }
  _row(y) { return Math.min(this.rows - 1, Math.max(0, Math.floor(y / this.cell))); }

  insert(e) {
    this.cells[this._row(e.y) * this.cols + this._col(e.x)].push(e);
  }

  /** calls cb(entity) for every entity in cells overlapping the circle (caller checks exact distance) */
  query(x, y, r, cb) {
    const c0 = this._col(x - r), c1 = this._col(x + r);
    const r0 = this._row(y - r), r1 = this._row(y + r);
    for (let row = r0; row <= r1; row++) {
      for (let col = c0; col <= c1; col++) {
        const cell = this.cells[row * this.cols + col];
        for (let i = 0; i < cell.length; i++) cb(cell[i]);
      }
    }
  }
}
