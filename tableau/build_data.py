"""Tableau data for the DA2026 dashboard.

Every file is derived from dashboard-app/public/data/dashboard.json, the same file the web dashboard
reads, so both versions show the same numbers. Nothing is added: rows are only re-shaped (per month,
per hour, per hospital-day) and summed the same way the web dashboard sums them.
"""
import csv, json, os
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, '..', 'dashboard-app', 'public', 'data', 'dashboard.json')
OUT = os.path.join(ROOT, 'Data')
os.makedirs(OUT, exist_ok=True)
D = json.load(open(SRC))

CAT_S = {'Perkotaan': 'Perkotaan', 'Tepi Jalan (Lalu Lintas)': 'Tepi jalan', 'Industri': 'Industri',
         'Gambut / Karhutla': 'Gambut / karhutla', 'Latar Bersih': 'Latar bersih'}
ISPU_L = ['Baik', 'Sedang', 'Tidak Sehat', 'Sangat Tidak Sehat', 'Berbahaya']
BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
POLS = ['pm25', 'pm10', 'so2', 'co', 'o3', 'no2']
OUTC = {'resp_admissions_under5': 'ispa_balita', 'resp_admissions_over60': 'ispa_lansia', 'asthma_emergency_cases': 'darurat_asma',
        'copd_admissions': 'ppok', 'resp': 'pernapasan_umum', 'cvd': 'kardiovaskular', 'death': 'kematian'}
OUT_LBL = {'resp_admissions_under5': 'ISPA balita', 'resp_admissions_over60': 'ISPA lansia', 'asthma_emergency_cases': 'Darurat asma',
           'copd_admissions': 'PPOK', 'resp': 'Pernapasan umum', 'cvd': 'Kardiovaskular', 'death': 'Kematian'}
FULL = {'resp_admissions_under5': 'ISPA balita (<5 th)', 'resp_admissions_over60': 'ISPA lansia (>60 th)', 'asthma_emergency_cases': 'Darurat asma',
        'copd_admissions': 'PPOK', 'resp': 'Pernapasan umum (semua umur)', 'cvd': 'Kardiovaskular', 'death': 'Kematian'}
OUT_FULL2LBL = {FULL[k]: OUT_LBL[k] for k in FULL}
NDAYS = D['meta']['ndays']
T0 = date(2024, 1, 1)
DAYS = [T0 + timedelta(days=i) for i in range(NDAYS)]
ST = {s['station']: s for s in D['stations']}
HOSP_OF = {v['station']: h for h, v in D['health'].items()}


def write(name, rows, cols):
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(['' if r.get(c) is None else (r.get(c).replace('\n', ', ') if isinstance(r.get(c), str) else r.get(c)) for c in cols])
    print(f'{name}: {len(rows)} rows')


def musim(m):  # m = 1..12
    return 'Hujan' if (m >= 11 or m <= 4) else 'Kemarau'


def base(s):
    return {'stasiun': s['station'], 'kota': s['kota_kabupaten'], 'provinsi': s['provinsi'], 'pulau': s['island'],
            'tipe_lokasi': CAT_S[s['site_category']], 'lat': s['latitude_dd'], 'lon': s['longitude_dd'],
            'dipakai': 1 if s['used_in_analysis'] else 0}


# 1. station x month: hourly sums/hours (station means), daily sums/days (monthly trend), ISPU day counts,
#    haze days, highest daily PM2.5 and the paired hospital's monthly case totals
rows = []
for code, s in ST.items():
    d = D['daily'].get(code, {})
    h = D['health'].get(HOSP_OF.get(code), {})
    acc = {}
    for i, day in enumerate(DAYS):
        k = (day.year, day.month)
        a = acc.setdefault(k, {'c': [0] * 5, 'haze': 0, 'pmmax': None, 'hari_rs': 0,
                               **{f'{x}_{p}': 0.0 for p in POLS for x in ('hs', 'ds')}, **{f'{x}_{p}': 0 for p in POLS for x in ('hn', 'dn', 'vd')},
                               **{v: 0 for v in OUTC.values()}})
        for p in POLS:
            hs, hn, dv = (d.get('hs_' + p) or [None] * NDAYS)[i], (d.get('hn_' + p) or [0] * NDAYS)[i], (d.get(p) or [None] * NDAYS)[i]
            if hn and hn > 0 and hs is not None:
                a['hs_' + p] += hs; a['hn_' + p] += hn; a['vd_' + p] += 1
            if dv is not None:
                a['ds_' + p] += dv; a['dn_' + p] += 1
        c = (d.get('cat') or [None] * NDAYS)[i]
        if c is not None:
            a['c'][c] += 1
        a['haze'] += (d.get('haze') or [0] * NDAYS)[i] or 0
        pv = (d.get('pm25') or [None] * NDAYS)[i]
        if pv is not None and (a['pmmax'] is None or pv > a['pmmax']):
            a['pmmax'] = pv
        if h:
            any_rs = False
            for o, col in OUTC.items():
                v = h[o][i]
                if v is not None:
                    a[col] += v; any_rs = True
            a['hari_rs'] += 1 if any_rs else 0
    for (y, m), a in sorted(acc.items()):
        r = base(s)
        r.update({'tahun': y, 'bulan': m, 'nama_bulan': BULAN[m - 1], 'periode': f'{y}-{m:02d}-01', 'musim': musim(m),
                  'puncak_kabut': 1 if 8 <= m <= 10 else 0, 'rumah_sakit': HOSP_OF.get(code, ''),
                  'hari_baik': a['c'][0], 'hari_sedang': a['c'][1], 'hari_tidak_sehat': a['c'][2], 'hari_sangat_tidak_sehat': a['c'][3],
                  'hari_berbahaya': a['c'][4], 'hari_kabut_asap': a['haze'], 'pm25_harian_maks': a['pmmax'], 'hari_rs': a['hari_rs']})
        for p in POLS:
            for x in ('hs', 'hn', 'vd', 'ds', 'dn'):
                r[f'{x}_{p}'] = round(a[f'{x}_{p}'], 4) if x in ('hs', 'ds') else a[f'{x}_{p}']
        for col in OUTC.values():
            r[col] = a[col] if h else None
        rows.append(r)
cols_b = ['stasiun', 'kota', 'provinsi', 'pulau', 'tipe_lokasi', 'lat', 'lon', 'dipakai', 'rumah_sakit', 'tahun', 'bulan', 'nama_bulan', 'periode', 'musim',
          'puncak_kabut'] + [f'{x}_{p}' for p in POLS for x in ('hs', 'hn', 'vd', 'ds', 'dn')] + \
         ['hari_baik', 'hari_sedang', 'hari_tidak_sehat', 'hari_sangat_tidak_sehat', 'hari_berbahaya', 'hari_kabut_asap', 'pm25_harian_maks', 'hari_rs'] + list(OUTC.values())
write('stasiun_bulanan.csv', rows, cols_b)

# 2. station profile (static results, same as the station list and network page)
rows = []
for code, s in ST.items():
    r = base(s)
    r.update({'nama_sensor': s.get('nama_sensor'), 'karakteristik_wilayah': s.get('karakteristik_wilayah'), 'lalu_lintas_per_jam': s.get('traffic_intensity_per_h'),
              'jarak_jalan_m': s.get('distance_to_road_m'), 'kelengkapan_pm25_pct': s.get('completeness_pm25_pct'), 'keandalan': s.get('reliability'),
              'aksi_alat': s.get('aksi_alat'), 'skor_prioritas': s.get('priority_score'), 'stasiun_terdekat': s.get('nearest_station'),
              'jarak_terdekat_km': s.get('nn_distance_km'), 'tren': s.get('trend_overall'), 'perubahan_2024_2026_pct': s.get('chg_2024_2026_pct'),
              'pm25_2024': s.get('pm25_2024_jan_14okt'), 'pm25_2025': s.get('pm25_2025_jan_14okt'), 'pm25_2026': s.get('pm25_2026_jan_14okt'),
              'rumah_sakit': HOSP_OF.get(code, ''), 'nama_rumah_sakit': s.get('nama_rumah_sakit')})
    rows.append(r)
write('stasiun.csv', rows, list(rows[0].keys()))

# 3. priority score components, weighted as on the network page (missing components re-weighted)
W = {'polusi': 0.25, 'kabut_asap': 0.20, 'beban_kesehatan': 0.20, 'defisit_data': 0.20, 'keterisolasian': 0.15}
WL = {'polusi': 'Polusi (25%)', 'kabut_asap': 'Kabut asap (20%)', 'beban_kesehatan': 'Beban kesehatan (20%)', 'defisit_data': 'Defisit data (20%)', 'keterisolasian': 'Keterisolasian (15%)'}
rows = []
for code, s in ST.items():
    if s.get('priority_score') is None:
        continue
    ks = [k for k in W if s.get('komp_' + k) is not None]
    ws = sum(W[k] for k in ks)
    for k in W:
        v = s.get('komp_' + k)
        rows.append({**base(s), 'komponen': WL[k], 'urutan': list(W).index(k) + 1, 'nilai': None if v is None else round(v * W[k] / ws * 100, 4),
                     'skor_prioritas': s['priority_score']})
write('prioritas.csv', rows, ['stasiun', 'pulau', 'tipe_lokasi', 'dipakai', 'komponen', 'urutan', 'nilai', 'skor_prioritas'])

# 4. hourly profiles (whole period, as on the critical-time page)
rows = []
SER = {'pm25': ('PM2.5', 'Semua hari'), 'no2': ('NO₂', 'Semua hari'), 'co': ('CO', 'Semua hari'), 'o3': ('O₃', 'Semua hari'),
       'pm25_wd': ('PM2.5', 'Hari kerja'), 'pm25_we': ('PM2.5', 'Akhir pekan'), 'no2_wd': ('NO₂', 'Hari kerja'), 'no2_we': ('NO₂', 'Akhir pekan')}
for code, prof in D['diurnal'].items():
    s = ST[code]
    for key, (pol, jh) in SER.items():
        arr = prof.get(key)
        if not arr:
            continue
        for hr, v in enumerate(arr):
            rows.append({**base(s), 'jam': hr, 'polutan': pol, 'jenis_hari': jh, 'nilai': v})
write('pola_jam.csv', rows, ['stasiun', 'pulau', 'tipe_lokasi', 'dipakai', 'jam', 'polutan', 'jenis_hari', 'nilai'])

# 5. hospital x day: paired station's daily PM2.5 and the seven case counts
rows = []
for hid, h in sorted(D['health'].items()):
    code = h['station']; s = ST[code]; d = D['daily'].get(code, {})
    pm = d.get('pm25') or [None] * NDAYS
    for i, day in enumerate(DAYS):
        r = {**base(s), 'rumah_sakit': hid, 'nama_rumah_sakit': s.get('nama_rumah_sakit'), 'tanggal': day.isoformat(), 'tahun': day.year, 'bulan': day.month,
             'musim': musim(day.month), 'kabut_asap': (d.get('haze') or [0] * NDAYS)[i] or 0,
             'pm25': pm[i] if s['used_in_analysis'] else None}
        for o, col in OUTC.items():
            r[col] = h[o][i]
            w = [h[o][j] for j in range(max(0, i - 6), i + 1) if h[o][j] is not None]
            r[col + '_7h'] = round(sum(w) / len(w), 4) if len(w) >= 4 else None
        rows.append(r)
write('rs_harian.csv', rows, ['rumah_sakit', 'nama_rumah_sakit', 'stasiun', 'kota', 'pulau', 'tipe_lokasi', 'dipakai', 'tanggal', 'tahun', 'bulan', 'musim', 'kabut_asap', 'pm25'] + list(OUTC.values()) + [c + '_7h' for c in OUTC.values()])


# 6. result tables, copied as they are
def dump(name, key, rename=None, extra=None):
    src = D[key]
    rs = []
    for x in src:
        r = dict(x)
        if 'site_category' in r and r['site_category'] in CAT_S:
            r['site_category'] = CAT_S[r['site_category']]
        if extra:
            r.update(extra(x))
        rs.append(r)
    cols = list(dict.fromkeys(k for r in rs for k in r))
    if rename:
        rs = [{rename.get(k, k): v for k, v in r.items()} for r in rs]
        cols = [rename.get(c, c) for c in cols]
    write(name, rs, cols)


dump('tahunan.csv', 'annual', {'station': 'stasiun', 'year': 'tahun', 'island': 'pulau', 'site_category': 'tipe_lokasi'})
dump('kritis.csv', 'critical', {'station': 'stasiun', 'island': 'pulau', 'site_category': 'tipe_lokasi'},
     extra=lambda x: {'peringkat': D['critical'].index(x) + 1})
dump('kawasan.csv', 'catprof', {'site_category': 'tipe_lokasi'})
dump('episode.csv', 'episodes', {'station': 'stasiun', 'island': 'pulau', 'site_category': 'tipe_lokasi', 'year': 'tahun'})
dump('kepentingan_faktor.csv', 'importance', {'group': 'faktor'})
PNAME = {'pm25': 'PM2.5', 'pm10': 'PM10', 'so2': 'SO₂', 'co': 'CO', 'o3': 'O₃', 'no2': 'NO₂'}
FNAME = {'temperature_c': 'Suhu', 'humidity_pct': 'Kelembapan', 'wind_speed_ms': 'Kecepatan angin'}
dump('korelasi_cuaca.csv', 'meteo', extra=lambda x: {'pollutant': PNAME.get(x['pollutant'], x['pollutant']), 'factor': FNAME.get(x['factor'], x['factor'])})
dump('lalu_lintas.csv', 'wet', {'station': 'stasiun', 'island': 'pulau', 'site_category': 'tipe_lokasi'})
dump('faktor_lokasi.csv', 'sitefac')
dump('arah_angin.csv', 'wind', {'station': 'stasiun', 'site_category': 'tipe_lokasi'},
     extra=lambda x: {'pulau': ST[x['station']]['island'], 'selisih_pct': None if x.get('sector_ratio') is None else round((x['sector_ratio'] - 1) * 100, 4)})
dump('jeda.csv', 'dlm', extra=lambda x: {'kasus': OUT_LBL[x['outcome']], 'kumulatif': 1 if not str(x['lag']).isdigit() else 0, 'jeda': int(x['lag']) if str(x['lag']).isdigit() else None})
dump('risiko_ispu.csv', 'band', extra=lambda x: {'kasus': OUT_FULL2LBL.get(x['outcome'], x['outcome']), 'urutan': ['Baik', 'Sedang', 'Tidak Sehat', 'Sangat Tidak Sehat', 'Berbahaya'].index(next(k for k in ['Sangat Tidak Sehat', 'Tidak Sehat', 'Berbahaya', 'Sedang', 'Baik'] if x['band'].startswith(k))) + 1})
dump('rentan.csv', 'vuln')
dump('kabut_kesehatan.csv', 'hazehealth', extra=lambda x: {'kasus': OUT_FULL2LBL.get(x['outcome'], x['outcome'])})
dump('atribusi.csv', 'attr', {'island': 'pulau'}, extra=lambda x: {'kasus': OUT_FULL2LBL.get(x['outcome'], x['outcome'])})
dump('celah.csv', 'gaps', {'island': 'pulau'}, extra=lambda x: {'pasangan': f"{x['station_a']}–{x['station_b']}"})
dump('cakupan.csv', 'coverage', {'island': 'pulau'})
dump('konversi.csv', 'conversion')
print('done')
