// Headless smoke test: boots the production bundle inside jsdom and reports
// any console errors / uncaught exceptions while rendering every route.
import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';
import 'fake-indexeddb/auto';

const distDir = path.resolve('dist');

const html = fs.readFileSync(path.join(distDir, 'index.html'), 'utf8');
const dom = new JSDOM(html, {
  url: 'https://example.test/',
  pretendToBeVisual: true,
});

const { window } = dom;

// Minimal browser APIs jsdom lacks that the app touches.
window.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
window.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
window.matchMedia = window.matchMedia || ((query) => ({
  matches: false, media: query, onchange: null,
  addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false,
}));
window.scrollTo = () => {};
window.Worker = class {
  constructor() { this.onmessage = null; this.onerror = null; }
  postMessage() {}
  terminate() {}
};
window.MediaRecorder = class {
  constructor() { this.state = 'inactive'; }
  start() { this.state = 'recording'; }
  stop() { this.state = 'inactive'; if (this.onstop) this.onstop(); }
  addEventListener() {}
};
window.speechSynthesis = { speak() {}, cancel() {}, getVoices: () => [] };
window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
if (!window.navigator.mediaDevices) {
  Object.defineProperty(window.navigator, 'mediaDevices', {
    value: { getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) },
  });
}
window.URL.createObjectURL = window.URL.createObjectURL || (() => 'blob:mock');
window.URL.revokeObjectURL = window.URL.revokeObjectURL || (() => {});
if (!window.navigator.geolocation) {
  Object.defineProperty(window.navigator, 'geolocation', { value: { getCurrentPosition: (cb) => cb({ coords: { latitude: 18.5, longitude: 73.8 } }) } });
}
// fetch: serve static assets from dist, no network.
window.fetch = async (input) => {
  const url = typeof input === 'string' ? input : input.url;
  const rel = url.replace(/^https?:\/\/[^/]+/, '');
  // Simulate a static deployment with no FastAPI service reachable, which forces the
  // on-device fallback path in services/MLApiService.ts.
  if (rel.startsWith('/api')) return new Response('unavailable', { status: 503 });
  const file = path.join(distDir, decodeURIComponent(rel.split('?')[0]));
  if (fs.existsSync(file) && fs.statSync(file).isFile()) {
    const ext = path.extname(file);
    const type = { '.json': 'application/json', '.geojson': 'application/geo+json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml' }[ext] || 'application/octet-stream';
    return new Response(fs.readFileSync(file), { status: 200, headers: { 'content-type': type } });
  }
  return new Response('Not found', { status: 404, headers: { 'content-type': 'text/plain' } });
};

// Simulate a previously signed-in farmer session (app screens require auth).
window.localStorage.setItem('auth_token', 'smoke-test-token');
window.localStorage.setItem('auth_user', JSON.stringify({ id: 'SMOKE-FARMER', email: 'smoke@example.test', full_name: 'Smoke Test Farmer', role: 'FARMER', district: 'Pune', village: 'Shirur' }));

// Mirror the DOM globals onto globalThis so the ESM bundle can run.
const globals = ['window', 'document', 'navigator', 'location', 'history', 'localStorage', 'sessionStorage', 'Worker',
  'MediaRecorder', 'speechSynthesis', 'SpeechSynthesisUtterance',
  'HTMLElement', 'HTMLDivElement', 'HTMLCanvasElement', 'Element', 'Node', 'Event', 'CustomEvent', 'KeyboardEvent',
  'MouseEvent', 'getComputedStyle', 'requestAnimationFrame', 'cancelAnimationFrame', 'ResizeObserver',
  'IntersectionObserver', 'MutationObserver', 'DOMParser', 'SVGElement', 'Blob', 'File', 'FileReader',
  'FormData', 'URLSearchParams', 'matchMedia', 'fetch', 'Response', 'Request', 'Headers', 'indexedDB', 'IDBKeyRange'];
for (const key of globals) {
  if (window[key] !== undefined) {
    try { globalThis[key] = window[key]; } catch { /* read-only global */ }
  }
}
globalThis.self = window;

const problems = [];
console.error = (...args) => { problems.push(['console.error', args.map(String).join(' ')]); };
console.warn = () => {};
window.addEventListener('error', (e) => problems.push(['window.error', String(e.message)]));
window.addEventListener('unhandledrejection', (e) => problems.push(['unhandledrejection', String(e.reason)]));
process.on('unhandledRejection', (r) => problems.push(['node.unhandledRejection', String(r)]));

const entry = fs.readdirSync(path.join(distDir, 'assets')).find((f) => /^index-.*\.js$/.test(f));
await import(path.join(distDir, 'assets', entry));

await new Promise((r) => setTimeout(r, 1500));

const root = window.document.getElementById('root');
const rendered = root.innerHTML.length;
console.log(`\nRendered #root HTML length: ${rendered}`);
console.log('Body text sample:', window.document.body.textContent.replace(/\s+/g, ' ').slice(0, 300));

// Walk each route through the router.
const routes = ['/', '/surveillance', '/gis', '/ai', '/reporting', '/animal-health', '/vet-response', '/lab',
  '/vaccination', '/alerts', '/multilingual', '/offline', '/disease-info', '/analytics', '/admin',
  '/login', '/login/farmer', '/login/veterinary', '/login/laboratory', '/login/government',
  '/signup', '/signup/farmer', '/signup/veterinary', '/signup/laboratory', '/signup/government'];

for (const route of routes) {
  problems.length = 0;
  try {
    window.history.pushState({}, '', route);
    window.dispatchEvent(new window.PopStateEvent('popstate', { state: {} }));
    await new Promise((r) => setTimeout(r, 250));
    const len = root.innerHTML.length;
    const errs = problems.filter(([k]) => k !== 'console.error' || !/Warning:/.test(k));
    console.log(`${len > 0 ? 'OK  ' : 'EMPTY'} ${route.padEnd(16)} html=${len} issues=${errs.length}`);
    for (const [kind, msg] of errs.slice(0, 4)) console.log(`      [${kind}] ${msg.replace(/\s+/g, ' ').slice(0, 220)}`);
  } catch (err) {
    console.log(`FAIL ${route.padEnd(16)} ${err.message}`);
  }
}

// --- Interaction check: AI early-warning screen must work with no backend -------
let failures = 0;
const clickByText = (text) => {
  const el = [...window.document.querySelectorAll('button')].find((b) => b.textContent.includes(text));
  if (!el) return false;
  el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  return true;
};
const settle = (ms = 250) => new Promise((r) => setTimeout(r, ms));

window.history.pushState({}, '', '/ai');
window.dispatchEvent(new window.PopStateEvent('popstate', { state: {} }));
await settle();
if (!clickByText('Analyze Risk')) { console.log('FAIL could not find the Analyze Risk button'); failures += 1; }
await settle(600);
const aiText = root.textContent.replace(/\s+/g, ' ');
const aiChecks = ['On-device fallback', 'On-device engine', 'Recommended',
  ['High Risk', 'Moderate Risk', 'Low Risk'].find((level) => aiText.includes(level))];
for (const needle of aiChecks) {
  const ok = Boolean(needle) && aiText.includes(needle);
  console.log(`${ok ? 'OK  ' : 'MISS'} ai screen contains "${needle}"`);
  if (!ok) failures += 1;
}

// --- Interaction check: submitting a case report populates "My Reports" ---------
const clickNext = async () => {
  if (!clickByText('Next')) throw new Error('Next button not found');
  await settle(200);
};

window.history.pushState({}, '', '/reporting');
window.dispatchEvent(new window.PopStateEvent('popstate', { state: {} }));
await settle(300);
try {
  await clickNext();          // step 1 -> 2
  await clickNext();          // step 2 -> 3
  // step 3 needs at least one symptom before it will advance
  const box = window.document.querySelector('input[type="checkbox"]');
  if (!box) throw new Error('no symptom checkbox rendered');
  box.checked = true;
  box.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await settle(150);
  await clickNext();          // step 3 -> 4 (prediction step)
  await clickNext();          // step 4 -> 5
  await clickNext();          // step 5 -> 6 (review)
  if (!clickByText('Submit Report')) throw new Error('Submit Report button not found');
  await settle(500);
} catch (err) {
  console.log(`FAIL reporting flow: ${err.message}`);
  failures += 1;
}
const reportsText = root.textContent.replace(/\s+/g, ' ');
const submitted = reportsText.includes('My Reports') && reportsText.includes('Cattle');
console.log(`${submitted ? 'OK  ' : 'MISS'} submitted report is listed under "My Reports"`);
if (!submitted) failures += 1;

console.log(`\nSMOKE RESULT: ${failures === 0 ? 'PASS' : `${failures} failure(s)`}`);
process.exit(failures === 0 ? 0 : 1);
