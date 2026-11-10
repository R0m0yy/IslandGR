#!/usr/bin/env python3
"""Independent re-open of a .glb: parses the container from disk and checks structure (does not share code with the generator)."""
import json, struct, sys
import numpy as np
p = sys.argv[1]; d = open(p, 'rb').read()
magic, ver, total = struct.unpack_from('<III', d, 0); assert magic == 0x46546C67 and ver == 2 and total == len(d), 'bad header'
jl, jt = struct.unpack_from('<II', d, 12); assert jt == 0x4E4F534A; g = json.loads(d[20:20 + jl])
bl, bt = struct.unpack_from('<II', d, 20 + jl); assert bt == 0x004E4942; b = d[28 + jl:28 + jl + bl]; assert g['buffers'][0]['byteLength'] <= bl
tris = 0; lo = np.full(3, 1e9); hi = -lo; bad = 0
for n in g['nodes']:
    pr = g['meshes'][n['mesh']]['primitives'][0]; arrs = {}
    for k, ai in pr['attributes'].items():
        a = g['accessors'][ai]; v = g['bufferViews'][a['bufferView']]
        arr = np.frombuffer(b, '<f4', a['count'] * 3, v['byteOffset']).reshape(-1, 3); assert np.isfinite(arr).all(); arrs[k] = arr
    P, N, Cc = arrs['POSITION'], arrs['NORMAL'], arrs['COLOR_0']; assert len(P) == len(N) == len(Cc) and len(P) % 3 == 0
    a = g['accessors'][pr['attributes']['POSITION']]; assert np.allclose(P.min(0), a['min'], atol=1e-5) and np.allclose(P.max(0), a['max'], atol=1e-5)
    assert abs(np.linalg.norm(N, axis=1) - 1).max() < 1e-3 and Cc.min() >= 0 and Cc.max() <= 1
    T = P.reshape(-1, 3, 3); area = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2; bad += int((area < 1e-9).sum())
    tris += len(T); lo = np.minimum(lo, P.min(0)); hi = np.maximum(hi, P.max(0))
print(f'OK {p}\n bytes={len(d)} nodes={len(g["nodes"])} meshes={len(g["meshes"])} materials={len(g["materials"])} triangles={tris} degenerate_tris={bad}')
print(' bounds(m) min=%s max=%s' % (np.round(lo, 2).tolist(), np.round(hi, 2).tolist()))
print(' nodes with extras:', [n['name'] for n in g['nodes'] if 'extras' in n])
print(' node names:', ', '.join(n['name'] for n in g['nodes']))
