#!/usr/bin/env python3
"""Captures WebGL frames of the TEMPORARY village massing model. Preview renderer only - not the game engine."""
import asyncio, json, subprocess, sys, time, os
from playwright.async_api import async_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = '/assets/glb/village_massing_v02.glb'; NAV = M + ',/assets/glb/village_nav_overlay_v02.glb'
BASE = 'ext=70&cx=0&cy=6&cz=-2&floor=-3.15'
SIZE = int(os.environ.get('LT_SIZE', '1300'))
VIEWS = {
 'V01_overview_day':        (M, 'mode=day&zoom=54&tx=-1&ty=5&tz=-3'),
 'V02_overview_sunset':     (M, 'mode=sunset&zoom=54&tx=-1&ty=5&tz=-3'),
 'V03_overview_night':      (M, 'mode=night&zoom=54&tx=-1&ty=5&tz=-3'),
 'V04_residential_hillside_day': (M, 'mode=day&zoom=24&tx=-18&ty=11&tz=-10&pitch=30'),
 'V05_harbour_day':         (M, 'mode=day&zoom=22&tx=6&ty=3&tz=10&pitch=32'),
 'V06_route_network':       (NAV, 'mode=day&zoom=54&tx=-1&ty=5&tz=-3&desat=1'),
 'V07_route_network_plan':  (NAV, 'mode=day&zoom=46&tx=-1&ty=5&tz=-3&desat=1&pitch=80&yaw=0'),
 'V08_gate_arch_and_bridge_day': (M, 'mode=day&zoom=22&tx=26&ty=6&tz=0&pitch=28&yaw=20'),
 'V09_harbour_night':       (M, 'mode=night&zoom=24&tx=2&ty=4&tz=6&pitch=32'),
}
only = sys.argv[1:]
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8766', '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0); logp = f'{ROOT}/evidence/logs/capture_village_log.json'; log = json.load(open(logp)) if os.path.exists(logp) else {}
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
            for name, (glb, qs) in VIEWS.items():
                if only and name not in only: continue
                pg = await b.new_page(viewport={'width': SIZE, 'height': SIZE}); errs = []
                pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
                await pg.goto(f'http://127.0.0.1:8766/tools/preview/viewer2.html?glb={glb}&{BASE}&{qs}&w={SIZE}&h={SIZE}')
                await pg.wait_for_function('window.__done===true', timeout=400000)
                err = await pg.evaluate('window.__err||null'); st = await pg.evaluate('window.__stats||null')
                out = f'{ROOT}/evidence/renders_village/{name}.png'; await pg.locator('canvas').screenshot(path=out)
                log[name] = {'query': qs, 'glb': glb, 'stats': st, 'error': err, 'console_errors': [e for e in errs if 'favicon' not in e and '404' not in e], 'file': os.path.relpath(out, ROOT)}
                print(name, st, err, flush=True); await pg.close()
            await b.close()
    finally: srv.terminate()
    json.dump(log, open(logp, 'w'), indent=1)
asyncio.run(main())
