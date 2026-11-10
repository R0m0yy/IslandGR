"""LIVING TIDES - village layout v0.2 ("Saltcrown"). Single source of truth for terrain levels, buildings,
households, jobs, interior stubs and the walk graph. Engine-agnostic: exported to data/village_layout.json.
Axes: +x east, +z south (towards the default camera), +y up. Units: metres."""
import math
from lt_mesh import pt_in_poly

LAND = [  # ordered low -> high; a point's ground height is the highest polygon containing it
    dict(id='SP', name='Breakwater spit', h=0.8, poly=[(-5, 24), (13, 24.5), (15, 27), (-5, 28)]),
    dict(id='T1', name='Quay', h=1.5, poly=[(-22, 28), (-5, 28), (-5, 5), (30, 5), (30, -6), (-22, -6)]),
    dict(id='T2', name='Plaza terrace', h=5.5, poly=[(-30, 21), (-14, 21), (-14, -5), (19, -5), (19, -13.5), (-30, -13.5)]),
    dict(id='HD', name='Lookout headland', h=9.0, poly=[(30, -15), (40, -13), (42, 0), (38, 4.5), (31, 3.5), (30, -5)]),
    dict(id='ST', name='Beacon stack', h=9.0, poly=[(31.5, 13.5), (38.5, 13), (39.5, 19), (35.5, 21.5), (31, 19.5)]),
    dict(id='T3', name='Upper homes', h=10.0, poly=[(-36, 15), (-23, 15), (-23, -12.5), (13, -12.5), (13, -21), (-36, -21)]),
    dict(id='T4', name='Civic shelf', h=14.5, poly=[(-40, 9), (-31, 9), (-31, -19.5), (7, -19.5), (7, -28), (-40, -28)]),
    dict(id='T5', name='Crown', h=19.0, poly=[(-43, -9), (-36, -9), (-36, -26.5), (-11, -26.5), (-11, -34), (-43, -34)]),
]
ARCH = dict(name="The Gate (sea arch)", x0=32, x1=38, z0=2.5, z1=14.5, y0=5.8, y1=9.3)
LEVEL_H = {l['id']: l['h'] for l in LAND}
def ground_h(x, z):
    h = None
    for l in LAND:
        if pt_in_poly(x, z, l['poly']): h = l['h'] if h is None else max(h, l['h'])
    return h

DECKS = [  # timber over water: (id, y, x0, x1, z0, z1)
    ('pier_A', 1.3, 4, 6.5, 5, 14), ('pier_B', 1.3, 13, 15.5, 5, 13), ('boardwalk', 1.5, -5, 10, 19.3, 21.5),
    ('stilt_deck', 1.5, -4.4, 9.8, 14.9, 19.3), ('slipway', 0.6, -5, 0, 6.5, 10.5)]
def deck_at(x, z):
    return [d for d in DECKS if d[2] - 1e-6 <= x <= d[3] + 1e-6 and d[4] - 1e-6 <= z <= d[5] + 1e-6]

# id, name, kind, level, cx, cz, frontage, depth, storeys, facing, wall, roof
B = [
 ('P01', 'Fish market', 'market', 'T1', 9, -1, 10, 6, 1, 'S', 'cream', 'coral'),
 ('P02', 'Boat yard', 'boatyard', 'T1', -10.5, 8.5, 7, 5, 1, 'E', 'dwoodl', 'rust'),
 ('P03', 'Warehouse', 'warehouse', 'T1', 19.5, -2, 7, 5.5, 1, 'S', 'stonew', 'deep'),
 ('P04', 'Net loft', 'netloft', 'T1', -10.5, 17.5, 5, 5, 2, 'E', 'turq', 'red'),
 ('P05', 'General store', 'store', 'T2', -19.5, 3, 5.5, 5, 2, 'E', 'ochre', 'blue'),
 ('P06', 'Eatery', 'eatery', 'T2', -19.5, 10.3, 4.6, 5, 1, 'E', 'coral', 'turq'),
 ('P07', 'Carpenter', 'carpenter', 'T2', -19.5, 17, 5.5, 5, 1, 'E', 'lwoodw', 'red'),
 ('P08', 'Community hall', 'hall', 'T4', -21, -24, 8.5, 4.5, 2, 'S', 'turq', 'cream'),
 ('P09', 'School', 'school', 'T4', -10, -24, 6.5, 4.5, 1, 'S', 'ochre', 'red'),
 ('P10', 'First-aid house', 'clinic', 'T4', -1.5, -24, 4.8, 4.5, 1, 'S', 'white', 'red'),
 ('H01', 'Quay cottage', 'home', 'T1', -10.5, 24, 4.5, 4.5, 1, 'E', 'blue', 'ochre'),
 ('H02', 'Harbour office house', 'home', 'T1', -0.5, -2.2, 5, 4.5, 2, 'S', 'white', 'deep'),
 ('H03', 'Stilt house west', 'stilt_home', 'DECK', -2, 17.2, 4, 4, 1, 'S', 'coral', 'blue'),
 ('H04', 'Stilt house middle', 'stilt_home', 'DECK', 2.7, 17.2, 4, 4, 1, 'S', 'ochre', 'turq'),
 ('H05', 'Stilt house east', 'stilt_home', 'DECK', 7.4, 17.2, 4, 4, 1, 'S', 'turq', 'red'),
 ('H06', 'Terrace house 1', 'home', 'T2', -5.5, -10.4, 4.6, 4, 1, 'S', 'plum', 'ochre'),
 ('H07', 'Terrace house 2', 'home', 'T2', 0.5, -10.4, 4.2, 4, 2, 'S', 'blue', 'coral'),
 ('H08', 'Terrace house 3', 'home', 'T2', 6.5, -10.4, 5, 4, 1, 'S', 'ochre', 'deep'),
 ('H09', 'Terrace house 4', 'home', 'T2', 13, -10.4, 4.6, 4, 1, 'S', 'coral', 'turq'),
 ('H10', 'West lane house 1', 'home', 'T3', -27.5, -3, 5, 4.6, 1, 'E', 'turq', 'red'),
 ('H11', 'West lane house 2', 'home', 'T3', -27.5, 5.2, 4.4, 4.6, 2, 'E', 'cream', 'blue'),
 ('H12', 'West lane house 3', 'home', 'T3', -27.5, 11.5, 5, 4.6, 1, 'E', 'red', 'ochre'),
 ('H13', 'High row house 1', 'home', 'T3', -17.5, -17, 5, 4, 1, 'S', 'ochre', 'plum'),
 ('H14', 'High row house 2', 'home', 'T3', -11, -17, 4.4, 4, 2, 'S', 'coral', 'deep'),
 ('H15', 'High row house 3', 'home', 'T3', -4.5, -17, 5, 4, 1, 'S', 'blue', 'red'),
 ('H16', 'High row house 4', 'home', 'T3', 8.5, -17, 4.6, 4, 1, 'S', 'white', 'turq'),
 ('H17', 'Shelf house south', 'home', 'T4', -35.5, 5, 4.2, 4.5, 1, 'E', 'plum', 'coral'),
 ('H18', 'Shelf house north', 'home', 'T4', -35.5, -4.5, 4.6, 4.5, 1, 'E', 'ochre', 'blue'),
 ('H19', 'Crown cottage', 'home', 'T5', -17, -30.5, 4.2, 4, 1, 'S', 'red', 'cream'),
 ('H20', "Keeper's house", 'home', 'HD', 35, -8, 4.6, 4.2, 1, 'S', 'white', 'red'),
]
KEYS = ('id', 'name', 'kind', 'level', 'cx', 'cz', 'front', 'depth', 'storeys', 'facing', 'wall', 'roof')
BUILDINGS = [dict(zip(KEYS, b)) for b in B]
for b in BUILDINGS:
    b['y'] = 1.5 if b['level'] == 'DECK' else LEVEL_H[b['level']]
    hx, hz = (b['front'] / 2, b['depth'] / 2) if b['facing'] == 'S' else (b['depth'] / 2, b['front'] / 2)
    b['footprint'] = [b['cx'] - hx, b['cx'] + hx, b['cz'] - hz, b['cz'] + hz]      # x0,x1,z0,z1
    b['door'] = [b['cx'], b['y'], b['cz'] + hz + 0.9] if b['facing'] == 'S' else [b['cx'] + hx + 0.9, b['y'], b['cz']]

# ---------------- living-world contract: what each building must expose to the simulation
ROOMS = {'home': ['living_kitchen', 'bedroom'], 'stilt_home': ['living_kitchen', 'bedroom', 'net_porch'], 'market': ['hall', 'cold_store'],
         'boatyard': ['workshop', 'slip'], 'warehouse': ['store_floor'], 'netloft': ['workroom', 'loft'], 'store': ['shop', 'stockroom', 'flat_above'],
         'eatery': ['kitchen', 'dining_terrace'], 'carpenter': ['workshop', 'timber_store'], 'hall': ['main_hall', 'kitchen'], 'school': ['classroom'], 'clinic': ['treatment_room', 'ward']}
ANCH = {'home': ['door', 'bed', 'bed', 'stove', 'sink', 'table', 'chair', 'chair', 'cabinet', 'storage', 'lamp', 'lamp', 'washstand'],
        'market': ['stall', 'stall', 'stall', 'scales', 'ice_box', 'counter', 'lamp'], 'boatyard': ['door', 'workbench', 'saw_horse', 'tool_rack', 'timber_stack', 'slip_cradle', 'lamp'],
        'warehouse': ['door', 'shelf', 'shelf', 'shelf', 'loading_point', 'ledger_desk', 'lamp'], 'netloft': ['door', 'net_frame', 'net_frame', 'storage', 'lamp'],
        'store': ['door', 'counter', 'shelf', 'shelf', 'storage', 'lamp', 'bed', 'bed', 'stove', 'table', 'chair', 'chair'],
        'eatery': ['door', 'stove', 'stove', 'sink', 'counter', 'table', 'table', 'table', 'chair', 'chair', 'chair', 'chair', 'chair', 'chair', 'lamp'],
        'carpenter': ['door', 'workbench', 'workbench', 'saw_horse', 'tool_rack', 'timber_stack', 'lamp'], 'hall': ['door', 'bench', 'bench', 'bench', 'bench', 'stage', 'stove', 'table', 'lamp', 'lamp'],
        'school': ['door', 'desk', 'desk', 'desk', 'desk', 'teacher_desk', 'board', 'lamp'], 'clinic': ['door', 'bed', 'bed', 'cabinet', 'desk', 'chair', 'lamp']}
ANCH['stilt_home'] = ANCH['home'] + ['net_rack']
JOBS = {'market': ['fishmonger', 'fishmonger', 'market_clerk'], 'boatyard': ['boatwright', 'apprentice'], 'warehouse': ['storekeeper'], 'netloft': ['net_maker'],
        'store': ['shopkeeper', 'shop_hand'], 'eatery': ['cook', 'server'], 'carpenter': ['carpenter', 'apprentice'], 'hall': ['caretaker'], 'school': ['teacher'], 'clinic': ['healer']}
for b in BUILDINGS:
    k = b['kind']; home = k in ('home', 'stilt_home', 'store')
    rooms = list(ROOMS[k]); anch = list(ANCH[k])
    if k == 'home' and b['storeys'] == 2: rooms += ['bedroom_upper', 'balcony']; anch += ['bed', 'bed', 'chair', 'lamp', 'stairs_interior']
    b['interior'] = dict(status='NOT MODELLED', cutaway='walls facing camera fade; roof lifts', rooms=rooms,
                         anchors=[dict(type=t, pos=None, facing=None, state='default') for t in anch])
    b['household'] = dict(id='HH_' + b['id'], capacity=(5 if b['storeys'] == 2 else 3) if k != 'store' else 2, shared_money=0, pantry={}, members=[]) if home else None
    b['business'] = dict(id='BIZ_' + b['id'], owner=None, jobs=[dict(role=r, holder=None) for r in JOBS[k]], hours=[6, 18], inventory={}, till=0) if k in JOBS else None
    b['state'] = dict(condition=1.0, lights_on=False, door_open=False)
BOATS = [dict(id=f'BOAT_{i+1:02d}', kind=k, mooring=m, owner_household=None, cargo={}, condition=1.0, job=dict(role='fisher', holder=None), crew_slots=c)
         for i, (k, m, c) in enumerate([('skiff', 'moor_A1', 1), ('skiff', 'moor_A2', 1), ('fishing_boat', 'moor_A3', 2), ('skiff', 'moor_B1', 1), ('fishing_boat', 'moor_B2', 2), ('skiff', 'moor_BW', 1)])]
FISHING_GROUNDS = [dict(id='FG_A', name='Harbour mouth', pos=[22, 22], methods=['shore', 'handline']), dict(id='FG_B', name='Reef beyond The Gate', pos=[44, 9], methods=['trap', 'rod']),
                   dict(id='FG_C', name='Open water south', pos=[10, 34], methods=['net'])]
SEA_LANES = [['moor_A3', [11, 13], [14.5, 17], [20, 20], 'FG_A'], ['FG_A', [28, 9], [35, 8.5], 'FG_B'], ['FG_A', [18, 30], 'FG_C']]

# ---------------- walk graph. kind: ground | deck | span (on a stair/bridge/arch) | water (mooring)
N = {}
def node(name, x, z, y=None, kind='ground'):
    N[name] = dict(x=x, y=ground_h(x, z) if y is None else y, z=z, kind=kind)
E = []
def edge(a, b, t='walk'): E.append((a, b, t))
def chain(names, t='walk'):
    for a, b in zip(names[:-1], names[1:]): edge(a, b, t)
# T1 quay
for n_, x, z in [('q_w_s', -6.5, 26), ('q_w_h01', -6.5, 24), ('q_w_bw', -6.5, 20.4), ('q_w_loft', -6.5, 17.5), ('q_w_bs', -6.5, 13.5), ('q_w_yard', -6.5, 8.5), ('q_corner', -6.5, 3),
                 ('q_n_office', -0.5, 2.5), ('q_n_lad', 3, 2.5), ('q_n_pierA', 5.25, 3.5), ('q_n_mkt', 9, 3.5), ('q_n_pierB', 14.25, 3.5), ('q_n_wh', 19.5, 2.5), ('q_n_s8', 22, 2),
                 ('s1_bot', -8.3, -3.7), ('s5_bot', -8.3, 13.5), ('lad_bot', 3, -4.5), ('s8_bot', 22.5, 2)]: node(n_, x, z)
chain(['q_w_s', 'q_w_h01', 'q_w_bw', 'q_w_loft', 'q_w_bs', 'q_w_yard', 'q_corner', 'q_n_office', 'q_n_lad', 'q_n_pierA', 'q_n_mkt', 'q_n_pierB', 'q_n_wh', 'q_n_s8', 's8_bot'])
edge('q_corner', 's1_bot'); edge('q_w_bs', 's5_bot'); edge('q_n_lad', 'lad_bot')
# decks, spit, moorings
node('pierA_mid', 5.25, 9, 1.3, 'deck'); node('pierA_end', 5.25, 13.3, 1.3, 'deck'); node('pierB_end', 14.25, 12.3, 1.3, 'deck'); node('bw_1', -2, 20.4, 1.5, 'deck'); node('bw_2', 2.7, 20.4, 1.5, 'deck'); node('bw_3', 7.4, 20.4, 1.5, 'deck')
node('slip', -2.5, 8.5, 0.6, 'deck'); node('sp_1', 4, 26); node('sp_2', 12.5, 25.8)
chain(['q_n_pierA', 'pierA_mid', 'pierA_end'], 'ramp'); edge('q_n_pierB', 'pierB_end', 'ramp'); chain(['q_w_bw', 'bw_1', 'bw_2', 'bw_3']); edge('q_w_yard', 'slip', 'ramp'); edge('q_w_s', 'sp_1', 'ramp'); edge('sp_1', 'sp_2')
for n_, x, z, via in [('moor_A1', 3.2, 9, 'pierA_mid'), ('moor_A2', 7.3, 9, 'pierA_mid'), ('moor_A3', 7.6, 12.5, 'pierA_end'), ('moor_B1', 12.2, 11, 'pierB_end'), ('moor_B2', 16.3, 11, 'pierB_end'), ('moor_BW', 9.5, 22.4, 'bw_3')]:
    node(n_, x, z, 0.4, 'water'); edge(via, n_, 'board')
# T2
for n_, x, z in [('s1_top', -14.5, -3.7), ('s5_top', -14.5, 13.5), ('p_w_carp', -15.5, 17), ('p_w_s5', -15.5, 13.5), ('p_w_eat', -15.5, 10.3), ('p_w_s4', -15.5, 6.9), ('p_w_store', -15.5, 3), ('p_s1', -15.5, -3.7),
                 ('plaza', -17, -8), ('p_s2', -11, -6.8), ('p_n_h06', -5.5, -7), ('p_n_h07', 0.5, -7), ('p_lad', 3, -6.5), ('p_n_h08', 6.5, -7), ('p_n_h09', 13, -7), ('lad_top', 3, -5.5), ('s4_bot', -17.2, 6.9), ('s2_bot', -11, -7.2)]: node(n_, x, z)
chain(['p_w_carp', 'p_w_s5', 'p_w_eat', 'p_w_s4', 'p_w_store', 'p_s1', 'plaza', 'p_s2', 'p_n_h06', 'p_n_h07', 'p_lad', 'p_n_h08', 'p_n_h09'])
edge('s1_top', 'p_s1'); edge('s5_top', 'p_w_s5'); edge('p_lad', 'lad_top'); edge('p_w_s4', 's4_bot'); edge('p_s2', 's2_bot')
# T3
for n_, x, z in [('r_w_h12', -24, 11.5), ('r_w_s4', -24, 6.9), ('r_w_h11', -24, 5.2), ('r_w_s6', -24, 1.25), ('r_w_h10', -24, -3), ('r_corner', -24, -13.7), ('r_n_h13', -17.5, -13.7), ('r_n_s2', -11, -13.7),
                 ('r_n_h15', -4.5, -13.7), ('r_n_s3', 2, -13.7), ('r_n_h16', 8.5, -13.7), ('br_a', 12.6, -15), ('s4_top', -23.5, 6.9), ('s2_top', -11, -13), ('s6_bot', -25.3, 1.25), ('s3_bot', 2, -14.2)]: node(n_, x, z)
chain(['r_w_h12', 'r_w_s4', 'r_w_h11', 'r_w_s6', 'r_w_h10', 'r_corner', 'r_n_h13', 'r_n_s2', 'r_n_h15', 'r_n_s3', 'r_n_h16', 'br_a'])
edge('s4_top', 'r_w_s4'); edge('s2_top', 'r_n_s2'); edge('r_w_s6', 's6_bot'); edge('r_n_s3', 's3_bot')
# T4
for n_, x, z in [('c_w_h17', -32, 5), ('c_w_s6', -32, 1.25), ('c_w_h18', -32, -4.5), ('c_corner', -32, -20.6), ('c_s7', -29.5, -20.6), ('c_hall', -21, -20.6), ('c_school', -10, -20.6), ('c_clinic', -1.5, -20.6), ('c_s3', 2, -20.6),
                 ('s6_top', -31.5, 1.25), ('s3_top', 2, -20), ('s7_bot', -29.5, -21.2)]: node(n_, x, z)
chain(['c_w_h17', 'c_w_s6', 'c_w_h18', 'c_corner', 'c_s7', 'c_hall', 'c_school', 'c_clinic', 'c_s3']); edge('s6_top', 'c_w_s6'); edge('s3_top', 'c_s3'); edge('c_s7', 's7_bot')
# T5
for n_, x, z in [('s7_top', -29.5, -27), ('k_s7', -29.5, -27.6), ('k_cistern', -25, -27.6), ('k_h19', -19.5, -27.6), ('k_west', -38, -27.6), ('k_tree', -39.5, -15), ('k_look', -39.5, -11)]: node(n_, x, z)
edge('s7_top', 'k_s7'); chain(['k_h19', 'k_cistern', 'k_s7', 'k_west', 'k_tree', 'k_look'])
# headland, arch, stack
for n_, x, z in [('s8_top', 31.2, 2), ('hd_mid', 33, -2), ('hd_br', 30.6, -11), ('hd_arch', 35, 3), ('st_beacon', 35, 16)]: node(n_, x, z)
node('ar_mid', 35, 8.5, 9.3, 'span')
chain(['s8_top', 'hd_mid', 'hd_br']); edge('hd_mid', 'hd_arch'); chain(['hd_arch', 'ar_mid', 'st_beacon'], 'archwalk')
# vertical links
for a, b in [('s1_bot', 's1_top'), ('s2_bot', 's2_top'), ('s3_bot', 's3_top'), ('s4_bot', 's4_top'), ('s5_bot', 's5_top'), ('s6_bot', 's6_top'), ('s7_bot', 's7_top'), ('s8_bot', 's8_top')]: edge(a, b, 'stair')
edge('lad_bot', 'lad_top', 'ladder'); edge('br_a', 'hd_br', 'bridge')
STAIR_STYLE = {'s1_bot': dict(name='Harbour Stair', width=2.6, stone=True), 's8_bot': dict(name='Lookout Stair', width=1.6), 's2_bot': dict(name='Plaza Stair', width=2.0),
               's3_bot': dict(name='Hall Stair', width=1.8), 's4_bot': dict(name='Store Steps', width=1.6), 's5_bot': dict(name='Back Stair', width=1.6), 's6_bot': dict(name='Shelf Steps', width=1.6), 's7_bot': dict(name='Crown Stair', width=1.6)}
# doors: connect each to the nearest same-level walkway node
for b in BUILDINGS:
    dn = 'door_' + b['id']; x, y, z = b['door']
    cands = [(math.hypot(n['x'] - x, n['z'] - z), k) for k, n in N.items() if n['kind'] in ('ground', 'deck') and abs(n['y'] - y) < 0.25 and not k.startswith('door_')]
    N[dn] = dict(x=x, y=y, z=z, kind='deck' if b['level'] == 'DECK' else 'ground', building=b['id']); b['access_node'] = min(cands)[1]; edge(dn, b['access_node'], 'door')
LAMPS = ['q_n_pierA', 'q_n_mkt', 'q_corner', 'q_w_loft', 'plaza', 'p_w_eat', 'p_n_h08', 'r_n_s2', 'r_w_h11', 'c_hall', 'c_school', 'k_s7', 'hd_mid', 'bw_2', 'pierB_end', 'st_beacon']

def to_json():
    return dict(schema='living-tides.layout', version='0.2', units='m', axes='+x east, +y up, +z south', status='TEMPORARY MASSING LAYOUT - awaiting owner approval',
                land=LAND, arch=ARCH, decks=[dict(id=d[0], y=d[1], rect=list(d[2:])) for d in DECKS], buildings=BUILDINGS, boats=BOATS, fishing_grounds=FISHING_GROUNDS, sea_lanes=SEA_LANES,
                nav=dict(nodes=N, edges=[dict(a=a, b=b, type=t) for a, b, t in E], stairs=STAIR_STYLE), lamps=LAMPS)
