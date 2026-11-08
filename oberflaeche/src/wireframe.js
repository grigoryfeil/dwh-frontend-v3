// <dd-wireframe kind="terrain|globe|lattice"> — calm monochrome 3D wireframe on canvas.
(function () {
  if (customElements.get('dd-wireframe')) return;
  const LEVELS = 8;
  const rot = (p, yaw, pitch) => {
    let [x, y, z] = p;
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    [x, z] = [x * cy - z * sy, x * sy + z * cy];
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    [y, z] = [y * cp - z * sp, y * sp + z * cp];
    return [x, y, z];
  };
  class DDWireframe extends HTMLElement {
    set kind(v) { this._kind = v; }
    get kind() { return this._kind || this.getAttribute('kind') || 'terrain'; }
    connectedCallback() {
      Object.assign(this.style, { display: 'block', position: 'relative', width: this.style.width || '100%', height: this.style.height || '100%' });
      this.c = document.createElement('canvas');
      Object.assign(this.c.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', display: 'block' });
      this.appendChild(this.c);
      this.ctx = this.c.getContext('2d');
      this.ro = new ResizeObserver(() => this.size()); this.ro.observe(this); this.size();
      this.reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
      this.visible = true;
      this.io = new IntersectionObserver(es => { this.visible = es[0].isIntersecting; if (this.visible) this.kick(); }); this.io.observe(this);
      this.t0 = performance.now(); this.last = 0;
      this.kick();
    }
    kick() {
      if (this.raf) return;
      const loop = now => {
        this.raf = 0;
        if (now - this.last >= 33) { this.last = now; this.draw((now - this.t0) / 1000); }
        if (!this.reduce && this.visible && this.isConnected) this.raf = requestAnimationFrame(loop);
      };
      this.raf = requestAnimationFrame(loop);
    }
    disconnectedCallback() { cancelAnimationFrame(this.raf); this.raf = 0; this.ro && this.ro.disconnect(); this.io && this.io.disconnect(); }
    size() {
      const r = this.getBoundingClientRect(), d = Math.min(window.devicePixelRatio || 1, 1.5);
      this.w = r.width; this.h = r.height; this.c.width = Math.max(1, Math.round(r.width * d)); this.c.height = Math.max(1, Math.round(r.height * d));
      this.ctx.setTransform(d, 0, 0, d, 0, 0);
      this.last = 0;
    }
    proj(p) {
      const cx = this.w * (parseFloat(this.getAttribute('cx')) || 0.56), cy = this.h * (parseFloat(this.getAttribute('cy')) || 0.46);
      const s = Math.min(this.w, this.h) * (parseFloat(this.getAttribute('scale')) || 0.36), f = 3.2, k = f / (f + p[2]);
      return [cx + p[0] * s * k, cy + p[1] * s * k, p[2]];
    }
    // collect segments into alpha buckets; alpha = depth alpha × radial edge fade
    add(pts, depthFn) {
      const fx = this.w * (parseFloat(this.getAttribute('cx')) || 0.56), fy = this.h * (parseFloat(this.getAttribute('cy')) || 0.46);
      const rx = this.w * 0.48, ry = this.h * 0.44;
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i];
        const mx = ((a[0] + b[0]) / 2 - fx) / rx, my = ((a[1] + b[1]) / 2 - fy) / ry;
        const d = Math.sqrt(mx * mx + my * my), edge = d < 0.6 ? 1 : Math.max(0, 1 - (d - 0.6) / 0.4);
        const al = depthFn((a[2] + b[2]) / 2) * edge;
        if (al < 0.02) continue;
        const k = Math.min(LEVELS - 1, Math.floor(al / 0.7 * LEVELS));
        this.buckets[k].push(a[0], a[1], b[0], b[1]);
      }
    }
    flush() {
      const ctx = this.ctx;
      for (let k = 0; k < LEVELS; k++) {
        const s = this.buckets[k]; if (!s.length) continue;
        ctx.strokeStyle = `rgba(28,28,28,${((k + 0.5) / LEVELS * 0.7).toFixed(3)})`;
        ctx.beginPath();
        for (let i = 0; i < s.length; i += 4) { ctx.moveTo(s[i], s[i + 1]); ctx.lineTo(s[i + 2], s[i + 3]); }
        ctx.stroke();
      }
    }
    draw(t) {
      const ctx = this.ctx; if (!this.w) return;
      ctx.clearRect(0, 0, this.w, this.h); ctx.lineWidth = 1; ctx.lineCap = 'round';
      this.buckets = Array.from({ length: LEVELS }, () => []);
      const k = this.kind;
      if (k === 'globe') { this.globe(t); this.flush(); } else if (k === 'lattice') this.lattice(t); else { this.terrain(t); this.flush(); }
    }
    terrain(t) {
      const N = 30, yaw = 0.6 + t * 0.05, pitch = 0.62, grid = [];
      for (let i = 0; i <= N; i++) {
        const row = [];
        for (let j = 0; j <= N; j++) {
          const x = -1.25 + 2.5 * i / N, z = -1.25 + 2.5 * j / N;
          const y = -(0.16 * Math.sin(2.6 * x + t * 0.45) * Math.cos(2.2 * z + t * 0.32) + 0.07 * Math.sin(4.2 * (x + z) - t * 0.6));
          row.push(this.proj(rot([x, y, z], yaw, pitch)));
        }
        grid.push(row);
      }
      const depth = z => Math.max(0.05, Math.min(0.62, 0.36 - z * 0.24));
      for (let i = 0; i <= N; i++) { this.add(grid[i], depth); this.add(grid.map(r => r[i]), depth); }
    }
    globe(t) {
      const yaw = t * 0.12, pitch = 0.38, seg = 60;
      const depth = z => z > 0 ? 0.08 : 0.55;
      for (let lat = -75; lat <= 75; lat += 15) {
        const a = lat * Math.PI / 180, pts = [];
        for (let i = 0; i <= seg; i++) { const b = i / seg * Math.PI * 2; pts.push(this.proj(rot([Math.cos(a) * Math.cos(b), Math.sin(a), Math.cos(a) * Math.sin(b)], yaw, pitch))); }
        this.add(pts, depth);
      }
      for (let lon = 0; lon < 180; lon += 15) {
        const b = lon * Math.PI / 180, pts = [];
        for (let i = 0; i <= seg; i++) { const a = i / seg * Math.PI * 2; pts.push(this.proj(rot([Math.cos(a) * Math.cos(b), Math.sin(a), Math.cos(a) * Math.sin(b)], yaw, pitch))); }
        this.add(pts, depth);
      }
      const ring = [];
      for (let i = 0; i <= 96; i++) { const b = i / 96 * Math.PI * 2; ring.push(this.proj(rot([1.45 * Math.cos(b), 0.0, 1.45 * Math.sin(b)], -yaw * 0.6, pitch + 0.22))); }
      this.add(ring, z => z > 0 ? 0.06 : 0.3);
    }
    lattice(t) {
      const n = 5, yaw = t * 0.09 + 0.5, pitch = 0.5 + Math.sin(t * 0.13) * 0.12, s = 0.82 * (1 + 0.035 * Math.sin(t * 0.5));
      const P0 = (i, j, l) => this.proj(rot([(-1 + 2 * i / (n - 1)) * s, (-1 + 2 * j / (n - 1)) * s, (-1 + 2 * l / (n - 1)) * s], yaw, pitch));
      // optical centring: keep the projected bounding box centred on (cx, cy), smoothed so it never jitters
      let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (const i of [0, n - 1]) for (const j of [0, n - 1]) for (const l of [0, n - 1]) { const q = P0(i, j, l); x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]); }
      const tx = this.w * (parseFloat(this.getAttribute('cx')) || 0.5) - (x0 + x1) / 2, ty = this.h * (parseFloat(this.getAttribute('cy')) || 0.5) - (y0 + y1) / 2;
      if (!this.off) this.off = [tx, ty]; else { this.off[0] += (tx - this.off[0]) * 0.08; this.off[1] += (ty - this.off[1]) * 0.08; }
      const ox = this.off[0], oy = this.off[1];
      const P = (i, j, l) => { const q = P0(i, j, l); return [q[0] + ox, q[1] + oy, q[2]]; };
      const depth = z => Math.max(0.06, Math.min(0.6, 0.32 - z * 0.3));
      for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) {
        const lx = [], ly = [], lz = [];
        for (let c = 0; c < n; c++) { lx.push(P(c, a, b)); ly.push(P(a, c, b)); lz.push(P(a, b, c)); }
        this.add(lx, depth); this.add(ly, depth); this.add(lz, depth);
      }
      this.flush();
      if (this.getAttribute('electron') !== 'false') this.electron(t, P, n);
    }
    // small orange point travelling node to node along the lattice lines, with a soft glow and short trail
    electron(t, P, n) {
      let e = this.e;
      const pick = (at, prev) => {
        const opts = [];
        for (let ax = 0; ax < 3; ax++) for (const d of [-1, 1]) {
          const nx = at.slice(); nx[ax] += d;
          if (nx[ax] < 0 || nx[ax] >= n) continue;
          if (prev && nx.every((v, i) => v === prev[i])) continue;
          opts.push(nx);
        }
        return opts[Math.floor(Math.random() * opts.length)];
      };
      if (!e) { const s = [2, 2, 2]; e = this.e = { from: s, to: pick(s), start: t, dur: 0.7, trail: [] }; }
      while (t - e.start >= e.dur) { const nf = e.to; e.to = pick(nf, e.from); e.from = nf; e.start += e.dur; e.dur = 0.55 + Math.random() * 0.35; }
      const u = Math.min(1, (t - e.start) / e.dur), k = u * u * (3 - 2 * u);
      const g = e.from.map((v, i) => v + (e.to[i] - v) * k);
      const p = P(g[0], g[1], g[2]);
      e.trail.push(p); if (e.trail.length > 9) e.trail.shift();
      const ctx = this.ctx;
      for (let i = 1; i < e.trail.length; i++) {
        const a = e.trail[i - 1], b = e.trail[i];
        ctx.strokeStyle = 'rgba(255,105,0,' + (i / e.trail.length * 0.5).toFixed(3) + ')';
        ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      }
      const front = Math.max(0.55, Math.min(1, 0.8 - p[2] * 0.3));
      const glow = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], 14);
      glow.addColorStop(0, 'rgba(255,105,0,' + (0.42 * front).toFixed(3) + ')');
      glow.addColorStop(1, 'rgba(255,105,0,0)');
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(p[0], p[1], 14, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#FF6900'; ctx.beginPath(); ctx.arc(p[0], p[1], 2.6, 0, Math.PI * 2); ctx.fill();
    }
  }
  customElements.define('dd-wireframe', DDWireframe);
})();
