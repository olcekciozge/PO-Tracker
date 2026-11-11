// Generates the presentation diagrams (16:9, 1600x900) in the style of the course slides.
// Run: node docs/diagrams/presentation/generate.js  -> *.svg next to this file
const fs = require('fs');
const path = require('path');
const OUT = __dirname;
fs.mkdirSync(OUT, { recursive: true });

const W = 1600, H = 900;
const MONO = "Menlo, Consolas, 'DejaVu Sans Mono', monospace";
const SANS = "Helvetica, Arial, sans-serif";
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const svg = (body, font) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="${font}">
<defs>
  <marker id="ok" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M0,0 L12,6 L0,12 z" fill="#000"/></marker>
  <marker id="okY" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L12,6 L0,12 z" fill="#F7B500"/></marker>
  <marker id="okG" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L12,6 L0,12 z" fill="#0A7A0A"/></marker>
</defs>
<rect width="${W}" height="${H}" fill="#fff"/>
${body}
</svg>`;

// multi-line text; y is the baseline of the first line
function text(cx, y, lines, { size = 26, weight = 'normal', fill = '#000', anchor = 'middle', lh = 1.3, italic = false } = {}) {
  return lines
    .map((l, i) => `<text x="${cx}" y="${y + i * size * lh}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}"${italic ? ' font-style="italic"' : ''}>${esc(l)}</text>`)
    .join('\n');
}
function box(x, y, w, h, lines, o = {}) {
  const { size = 26, weight = 'normal', stroke = '#000', sw = 2.5, fill = '#fff', dash = false, rx = 0, color = '#000' } = o;
  const lh = 1.3;
  const ty = y + h / 2 - ((lines.length - 1) * size * lh) / 2 + size * 0.35;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${dash ? ' stroke-dasharray="10 7"' : ''}/>
${text(x + w / 2, ty, lines, { size, weight, fill: color })}`;
}
function cylinder(cx, y, w, h, lines, { dash = false, size = 28 } = {}) {
  const rx = w / 2, ry = 16, x = cx - rx;
  const d = dash ? ' stroke-dasharray="10 7"' : '';
  return `<path d="M${x},${y + ry} L${x},${y + h - ry} A${rx},${ry} 0 0 0 ${x + w},${y + h - ry} L${x + w},${y + ry}" fill="#fff" stroke="#000" stroke-width="2.5"${d}/>
<ellipse cx="${cx}" cy="${y + ry}" rx="${rx}" ry="${ry}" fill="#fff" stroke="#000" stroke-width="2.5"${d}/>
${text(cx, y + h / 2 + ry / 2 - ((lines.length - 1) * size * 1.3) / 2 + size * 0.35, lines, { size })}`;
}
const line = (x1, y1, x2, y2, { dash = false, arrow = true, sw = 2.5 } = {}) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#000" stroke-width="${sw}"${dash ? ' stroke-dasharray="10 7"' : ''}${arrow ? ' marker-end="url(#ok)"' : ''}/>`;

/* ---------- 1) System architecture ---------- */
{
  let b = '';
  b += box(330, 30, 940, 70, ['Student · Instructor · Department Head · Admin  (web browser)'], { size: 26 });
  b += line(800, 100, 800, 160);
  b += text(815, 140, ['HTTPS'], { size: 22, anchor: 'start' });
  b += box(230, 160, 1140, 120, ['PO Tracker platform (Django)', 'accounts · courses · outcomes · grades · dashboard'], { size: 30, weight: 'bold', sw: 4 });

  const cols = [
    { cx: 215, label: ['Sessions +', 'computed PO profiles'], svc: 'Cache service', store: ['Key-Value', 'store (Redis)'], dash: true },
    { cx: 615, label: ['Users, courses,', 'LOs, POs, weights,', 'grades'], svc: 'Core data', store: ['RDBMS', 'PostgreSQL 16'], dash: false },
    { cx: 1015, label: ['Reports &', 'dashboards', '(read-only)'], svc: 'Reporting', store: ['Read', 'replica'], dash: true },
    { cx: 1395, label: ['Uploaded OBS', 'Excel files'], svc: 'File service', store: ['File', 'storage'], dash: true },
  ];
  for (const c of cols) {
    const lw = 300, ly = 380, lh = c.label.length === 3 ? 120 : 92;
    b += line(c.cx, 280, c.cx, ly, { dash: c.dash, arrow: false });
    b += box(c.cx - lw / 2, ly, lw, lh, c.label, { size: 25, dash: c.dash });
    // service frame (rounded) + cylinder
    b += `<rect x="${c.cx - 165}" y="555" width="330" height="262" rx="22" fill="#fff" stroke="#000" stroke-width="3"${c.dash ? ' stroke-dasharray="10 7"' : ''}/>`;
    b += text(c.cx, 595, [c.svc], { size: 26 });
    b += line(c.cx, ly + lh, c.cx, 553, { dash: c.dash });
    b += cylinder(c.cx, 618, 250, 170, c.store, { dash: c.dash, size: 28 });
  }
  // replication: PostgreSQL -> read replica, routed below the service frames
  b += `<path d="M615,788 L615,850 L1015,850 L1015,794" fill="none" stroke="#000" stroke-width="2.5" stroke-dasharray="10 7" marker-end="url(#ok)"/>`;
  b += text(815, 880, ['replication'], { size: 22 });
  fs.writeFileSync(path.join(OUT, 'architecture.svg'), svg(b, MONO));
}

/* ---------- 2) Simplified class diagram ---------- */
{
  let b = '';
  const cls = {};
  function klass(id, x, y, w, name, attrs) {
    const hh = 52, ah = 36, h = hh + attrs.length * ah + 16;
    cls[id] = { x, y, w, h };
    b += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff" stroke="#000" stroke-width="2.5"/>
<line x1="${x}" y1="${y + hh}" x2="${x + w}" y2="${y + hh}" stroke="#000" stroke-width="2.5"/>
${text(x + w / 2, y + 36, [name], { size: 28, weight: 'bold' })}
${attrs.map((a, i) => text(x + 18, y + hh + 30 + i * ah, [a], { size: 24, anchor: 'start' })).join('\n')}`;
  }
  klass('user', 40, 360, 280, 'User', ['username', 'role']);
  klass('enr', 400, 70, 260, 'Enrollment', []);
  klass('course', 560, 360, 280, 'Course', ['code', 'title', 'term']);
  klass('grade', 300, 680, 240, 'Grade', ['score 0–100']);
  klass('asm', 660, 680, 300, 'Assessment', ['name', 'weight %']);
  klass('lo', 990, 360, 300, 'LearningOutcome', ['code', 'description']);
  klass('alo', 1080, 680, 280, 'AssessmentLO', ['weight %']);
  klass('po', 1310, 60, 270, 'ProgramOutcome', ['code (PO1–PO11)', 'description']);
  klass('lopo', 1390, 360, 190, 'LOPO', ['weight 1–5']);

  // relationship line with multiplicity labels at both ends
  function rel(pts, m1, m2, label) {
    const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0] + ',' + p[1]).join(' ');
    b += `<path d="${d}" fill="none" stroke="#000" stroke-width="2.5"/>`;
    const lab = (p, q, m) => {
      const dx = Math.sign(q[0] - p[0]), dy = Math.sign(q[1] - p[1]);
      const x = p[0] + dx * 22 + (dy ? 16 : 0), y = p[1] + dy * 34 + (dx ? -10 : 0);
      b += text(x, y, [m], { size: 30, weight: 'bold', anchor: dx < 0 ? 'end' : 'start' });
    };
    lab(pts[0], pts[1], m1);
    lab(pts[pts.length - 1], pts[pts.length - 2], m2);
    if (label) b += text(label[0], label[1], [label[2]], { size: 22, italic: true });
  }
  const c = cls;
  // User 1 — * Course (teaches)
  rel([[320, 420], [560, 420]], '1', '*', [440, 405, 'teaches']);
  // User 1 — * Enrollment ; Course 1 — * Enrollment
  rel([[180, 360], [180, 105], [400, 105]], '1', '*');
  rel([[700, 360], [700, 104], [660, 104]], '1', '*');
  // User 1 — * Grade
  rel([[180, 500], [180, 740], [300, 740]], '1', '*');
  // Course 1 — * Assessment
  rel([[760, 536], [760, 680]], '1', '*');
  // Assessment 1 — * Grade
  rel([[660, 750], [540, 750]], '1', '*');
  // Course 1 — * LearningOutcome
  rel([[840, 430], [990, 430]], '1', '*');
  // Assessment 1 — * AssessmentLO
  rel([[960, 750], [1080, 750]], '1', '*');
  // LO 1 — * AssessmentLO
  rel([[1180, 500], [1180, 680]], '1', '*');
  // LO 1 — * LOPO
  rel([[1290, 420], [1390, 420]], '1', '*');
  // ProgramOutcome 1 — * LOPO
  rel([[1485, 196], [1485, 360]], '1', '*');
  fs.writeFileSync(path.join(OUT, 'class-diagram.svg'), svg(b, MONO));
}

/* ---------- 3) Tooling and workflow (CSE 311) ---------- */
{
  let b = '';
  // calm palette, same structure as the CSE 311 slide (IDEs -> GitHub -> CI, shared channel)
  const C = {
    frame: '#F1F3F6', frameLine: '#B9C0CB', ink: '#1F2933', soft: '#52606D',
    ciFill: '#E4F4EA', ciLine: '#2F855A', repoFill: '#FFF3DC', repoLine: '#C98A00',
    devFill: '#E6F0FB', devLine: '#2B6CB0', testFill: '#FDE8E6', testLine: '#C0392B',
    bandFill: '#FBEAF2', bandLine: '#C2578A', arrow: '#C98A00',
  };
  const rect = (x, y, w, h, fill, stroke, rx = 14, sw = 2.5, dash = '') =>
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
  b += `<defs><marker id="okA" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L12,6 L0,12 z" fill="${C.arrow}"/></marker>
<marker id="okC" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L12,6 L0,12 z" fill="${C.ciLine}"/></marker></defs>`;
  // GitHub frame
  b += rect(380, 24, 840, 340, C.frame, C.frameLine, 28, 2.5, '8 7');
  b += text(408, 64, ['GitHub'], { size: 24, anchor: 'start', fill: C.soft, weight: 'bold' });
  // CI
  b += rect(520, 50, 560, 104, C.ciFill, C.ciLine);
  b += text(800, 92, ['GitHub Actions CI'], { size: 28, weight: 'bold', fill: C.ink });
  b += text(800, 130, ['PostgreSQL 16 · Django checks · 143 tests'], { size: 23, fill: C.ink });
  b += `<line x1="800" y1="216" x2="800" y2="160" stroke="${C.ciLine}" stroke-width="4" marker-end="url(#okC)"/>`;
  b += text(816, 194, ['runs on every push & PR'], { size: 20, anchor: 'start', fill: C.soft });
  // repository
  b += rect(450, 220, 700, 118, C.repoFill, C.repoLine);
  b += text(800, 266, ['Repository: olcekciozge/PO-Tracker'], { size: 28, weight: 'bold', fill: C.ink });
  b += text(800, 306, ['main + one branch per member · merged via pull requests'], { size: 23, fill: C.ink });
  // members
  const devs = [['Rümeysa', 'data model'], ['Batuhan', 'architecture, CI'], ['Buğra', 'accounts, Scrum'], ['Özge', 'UI, dashboard']];
  devs.forEach(([n, r], i) => {
    const x = 130 + i * 350, y = 530, cx = x + 150, tx = 590 + i * 140;
    b += `<line x1="${cx}" y1="${y - 6}" x2="${tx}" y2="${344}" stroke="${C.arrow}" stroke-width="3.5" marker-start="url(#okA)" marker-end="url(#okA)"/>`;
    b += rect(x, y, 300, 150, C.devFill, C.devLine);
    b += text(x + 24, y + 52, [n], { size: 30, anchor: 'start', weight: 'bold', fill: C.ink });
    b += text(x + 24, y + 90, [r], { size: 23, anchor: 'start', fill: C.soft });
    b += rect(x + 24, y + 108, 150, 30, C.testFill, C.testLine, 15, 2);
    b += text(x + 99, y + 130, ['local unit tests'], { size: 17, fill: C.testLine, weight: 'bold' });
    b += `<line x1="${cx}" y1="${y + 150}" x2="${cx}" y2="${720}" stroke="${C.bandLine}" stroke-width="2.5"/>`;
  });
  // label for the push/pull arrows
  b += rect(690, 420, 220, 38, '#fff', '#fff', 8, 0);
  b += text(800, 446, ['push · pull request'], { size: 22, weight: 'bold', fill: C.arrow });
  // shared communication band
  b += rect(130, 720, 1350, 64, C.bandFill, C.bandLine, 32);
  b += text(805, 761, ['WhatsApp group  ·  task board with backlog & sprints'], { size: 25, weight: 'bold', fill: C.ink });
  b += text(805, 840, ['Each member works in their own IDE on their own branch; code reaches main only through a pull request.'], { size: 21, fill: C.soft });
  fs.writeFileSync(path.join(OUT, 'tooling.svg'), svg(b, SANS));
}
console.log('ok');
