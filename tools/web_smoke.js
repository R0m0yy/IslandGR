// Browser smoke gate for the web build (audit: "wait for an actual rendered frame and an
// advancing clock, not only a removed loading overlay").
//   cd web_site && python3 -m http.server 8765 &     then     node tools/web_smoke.js [url] [outdir]
// Passes only if: the game prints LT_READY, the canvas shows a real picture (many distinct
// colours, not a flat sky), and the village clock advances by at least 20 game minutes in 30 s.
const { chromium } = require('playwright');
const url = process.argv[2] || 'http://localhost:8765/index.html';
const out = process.argv[3] || '.';
(async () => {
  const b = await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox']});
  const p = await b.newPage({viewport:{width:800,height:450}});
  const t0 = Date.now();
  await p.goto(url, {waitUntil:'load'});
  let ready = false, stages = new Set();
  for (let i = 0; i < 150 && !ready; i++) {
    await p.waitForTimeout(2000);
    const s = await p.evaluate(() => ({ready: !!(window.__lt && window.__lt.ready), stage: (document.getElementById('stage-msg')||{}).textContent || '', err: document.getElementById('err').textContent}));
    if (s.err) { console.log('FAIL  loader error: ' + s.err); process.exit(1); }
    stages.add(s.stage.split('·')[0].trim()); ready = s.ready;
  }
  const tReady = (Date.now() - t0) / 1000;
  const log = () => p.evaluate(() => window.__lt.log.join('\n'));
  const clock = async () => { const png = null; return p.evaluate(() => window.__lt.log.filter(l => l.indexOf('LT_CLOCK') === 0).pop() || ''); };
  const results = [];
  const check = (n, ok, d) => { results.push(ok); console.log((ok ? 'PASS  ' : 'FAIL  ') + n + '  ' + (d === undefined ? '' : JSON.stringify(d))); };
  check('loader showed its stages and the game announced LT_READY', ready && (await log()).includes('LT_READY'), {seconds: tReady, stages: [...stages]});
  await p.waitForTimeout(3000);
  const shot1 = await p.screenshot({path: out + '/web_smoke_a.png', timeout: 150000});
  const c1 = await clock();
  await p.waitForTimeout(30000);
  await p.screenshot({path: out + '/web_smoke_b.png', timeout: 150000});
  const c2 = await clock();
  const m = s => { const r = /minutes=(\d+)/.exec(s); return r ? +r[1] : -1; };
  check('village clock advances (>= 20 game minutes in 30 s at x1)', m(c1) >= 0 && m(c2) - m(c1) >= 20, {from: m(c1), to: m(c2)});
  // distinct colours in the frame: a flat sky has a handful, the village thousands
  const colours = await p.evaluate(async (b64) => { const im = new Image(); im.src = 'data:image/png;base64,' + b64; await im.decode();
    const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const g = c.getContext('2d'); g.drawImage(im, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data; const s = new Set(); for (let i = 0; i < d.length; i += 16) s.add((d[i] >> 3) << 10 | (d[i+1] >> 3) << 5 | (d[i+2] >> 3)); return s.size; }, shot1.toString('base64'));
  check('a real picture is drawn (not a flat sky)', colours > 400, {distinct_colours: colours});
  const lg = await log();
  const q = lg.split('\n').filter(l => /LT_QUALITY|LT_READY/.test(l));
  console.log('INFO  ' + q.join(' | '));
  console.log('RESULT: ' + (results.every(x => x) ? 'PASSED' : 'FAILED'));
  await b.close();
  process.exit(results.every(x => x) ? 0 : 1);
})();
