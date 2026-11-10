#!/usr/bin/env python3
"""Captures genuine WebGL frames of the GLB through headless Chrome (software GL). Writes PNGs + a JSON log."""
import asyncio, json, subprocess, sys, time, os
from playwright.async_api import async_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = '/assets/glb/lt_pipeline_test_01.glb'
VIEWS = {
 '01_overview_day':    'mode=day',
 '02_overview_sunset': 'mode=sunset',
 '03_overview_night':  'mode=night',
 '04_cottage_closeup_day': 'mode=day&zoom=4.2&tx=-0.6&ty=4.3&tz=1.6&pitch=28',
 '05_dock_closeup_day': 'mode=day&zoom=4.0&tx=5.6&ty=1.0&tz=2.8&pitch=30&yaw=30',
 '06_reverse_angle_day': 'mode=day&yaw=-40&pitch=30',
 '07_cottage_closeup_night': 'mode=night&zoom=4.2&tx=-0.6&ty=4.3&tz=1.6&pitch=28',
}
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8765', '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0); log = {}
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
            for name, qs in VIEWS.items():
                pg = await b.new_page(viewport={'width': 1400, 'height': 1400}); errs = []
                pg.on('console', lambda m: errs.append(m.text) if m.type in ('error', 'warning') else None)
                await pg.goto(f'http://127.0.0.1:8765/engine/viewer.html?glb={GLB}&{qs}')
                await pg.wait_for_function('window.__done===true', timeout=180000)
                err = await pg.evaluate('window.__err||null'); st = await pg.evaluate('window.__stats||null')
                out = f'{ROOT}/evidence/renders/{name}.png'
                await pg.locator('canvas').screenshot(path=out)
                log[name] = {'query': qs, 'stats': st, 'error': err, 'console': errs, 'file': os.path.relpath(out, ROOT)}
                print(name, st, err, errs); await pg.close()
            await b.close()
    finally: srv.terminate()
    json.dump(log, open(f'{ROOT}/evidence/logs/capture_log.json', 'w'), indent=1)
asyncio.run(main())
