"""Builds the Tableau workbook (DA2026 dashboard) from the CSV files in Data/.

Run build_data.py first. The workbook mirrors the web dashboard: same pages, same charts, same
formulas (station mean = sum of valid hourly values / valid hours, at least 10 days, etc.).
Filters are workbook parameters (Pulau, Tipe Lokasi, Musim, Tahun), so one choice applies to
every page, as in the web version.
"""
import csv, os, re, shutil, uuid, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'Data')
NAME = 'DA2026_Dashboard_EconsUGMCobaCoba_NamaKetua'
FONT = 'Helvetica Neue'

# ───────────────────────── helpers ─────────────────────────
def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace("'", '&apos;').replace('"', '&quot;').replace('\n', '&#10;'))


def sid():
    return '{' + str(uuid.uuid4()).upper() + '}'


DERIV = {'none': 'None', 'sum': 'Sum', 'avg': 'Avg', 'max': 'Max', 'min': 'Min', 'usr': 'User', 'cnt': 'Count',
         'ctd': 'CountD', 'attr': 'Attr', 'tmn': 'Month-Trunc', 'tdy': 'Day-Trunc'}
KIND = {'nk': 'nominal', 'ok': 'ordinal', 'qk': 'quantitative'}

ISL = ['Sumatera', 'Jawa', 'Kalimantan', 'Sulawesi', 'Papua']
CATS = ['Perkotaan', 'Tepi jalan', 'Industri', 'Gambut / karhutla', 'Latar bersih']
SER = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
C_ISL = dict(zip(ISL, SER))
C_CAT = dict(zip(CATS, SER))
ISPU = ['Baik', 'Sedang', 'Tidak Sehat', 'Sangat Tidak Sehat', 'Berbahaya']
C_ISPU = dict(zip(ISPU, ['#2a78d6', '#c9ccd4', '#f0a3a0', '#e34948', '#9e2323']))
C_REL = {'Baik': SER[0], 'Perlu standardisasi': SER[3], 'Buruk - perlu kalibrasi/perawatan': SER[1], 'Kritis - ganti/perbaiki': '#d03b3b'}
KASUS = ['ISPA balita', 'ISPA lansia', 'Darurat asma', 'PPOK', 'Pernapasan umum', 'Kardiovaskular', 'Kematian']
KCOL = ['ispa_balita', 'ispa_lansia', 'darurat_asma', 'ppok', 'pernapasan_umum', 'kardiovaskular', 'kematian']
C_KASUS = dict(zip(KASUS, [SER[1], SER[0], SER[2], SER[3], SER[6], SER[4], SER[7]]))
POLS = [('PM2.5', 'pm25'), ('PM10', 'pm10'), ('SO₂', 'so2'), ('CO', 'co'), ('O₃', 'o3'), ('NO₂', 'no2')]

INT_DIMS = {'tahun', 'bulan', 'jam', 'dipakai', 'puncak_kabut', 'peringkat', 'kumulatif', 'jeda', 'year', 'n', 'kabut_asap'}
MEASURE_INTS = {'urutan', 'n_stasiun', 'n_days', 'n_hospitals', 'n_stasiun_andal', 'n_provinsi_tercakup', 'n_hospitals_with_haze'}
CAPTION = {
    'stasiun': 'Stasiun', 'kota': 'Kota/Kabupaten', 'provinsi': 'Provinsi', 'pulau': 'Pulau', 'tipe_lokasi': 'Tipe Lokasi',
    'lat': 'Lintang', 'lon': 'Bujur', 'tahun': 'Tahun', 'bulan': 'Bulan', 'jam': 'Jam (WIB)', 'polutan': 'Polutan',
    'jenis_hari': 'Jenis Hari', 'nilai': 'Nilai', 'rumah_sakit': 'Rumah Sakit', 'nama_rumah_sakit': 'Nama Rumah Sakit',
    'tanggal': 'Tanggal', 'keandalan': 'Keandalan Alat', 'skor_prioritas': 'Skor Prioritas', 'komponen': 'Komponen',
    'faktor': 'Faktor', 'importance': 'Penurunan R²', 'share_pct': 'Porsi Kepentingan (%)', 'kasus': 'Jenis Kasus',
    'pasangan': 'Pasangan Stasiun', 'jarak_km': 'Jarak (km)', 'pm25': 'PM2.5', 'pm10': 'PM10', 'no2': 'NO₂', 'co': 'CO', 'so2': 'SO₂', 'o3': 'O₃',
    'traffic_intensity_per_h': 'Lalu Lintas (kendaraan/jam)', 'distance_to_road_m': 'Jarak ke Jalan Raya (m)', 'selisih_pct': 'Selisih PM2.5 (%)',
    'pct_increase_per10': 'Kenaikan Kasus per 10 µg/m³ (%)', 'jeda': 'Hari Jeda', 'band': 'Kategori ISPU', 'RR': 'Risiko Relatif',
    'attributable': 'Kasus Akibat PM2.5', 'pct_increase': 'Kenaikan Saat Kabut Asap (%)', 'start': 'Mulai', 'end': 'Selesai', 'days': 'Lama (hari)',
    'pm25_peak_daily': 'PM2.5 Harian Tertinggi', 'critical_score': 'Skor', 'pm25_mean': 'PM2.5', 'days_ispu_tidak_sehat_plus': 'Hari Tidak Sehat ke Atas',
    'pm25_tahunan': 'PM2.5 (15)', 'pm10_tahunan': 'PM10 (40)', 'no2_tahunan': 'NO₂ (50)', 'o3_tahunan': 'O₃ (35)', 'IKU': 'IKU', 'IKU_kategori': 'Kategori IKU',
    'kelengkapan_pct': 'Data (%)', 'n_stasiun': 'Stasiun', 'pct_hari_lewat_bm24jam_pm25': '% Hari > BM 24 Jam', 'kemarau_vs_hujan_pm25_pct': 'Kemarau vs Hujan (%)',
    'hari_kabut_asap_per_stasiun': 'Hari Kabut per Stasiun', 'n_stasiun_andal': 'Andal', 'n_provinsi_tercakup': 'Provinsi',
    'jarak_tetangga_median_km': 'Median Jarak Tetangga (km)', 'celah_terlebar_km': 'Celah Terlebar (km)', 'hari_kabut_asap': 'Hari Kabut',
    'scope': 'Cakupan', 'group': 'Kelompok', 'RR_per10': 'RR per 10 µg/m³', 'n_hospitals': 'Jumlah RS', 'z_diff': 'Uji Beda (z)',
    'pm25_2024': '2024', 'pm25_2025': '2025', 'pm25_2026': '2026', 'tren': 'Tren 2024 ke 2026', 'r_rata2': 'Spearman r Rata-Rata',
    'pollutant': 'Polutan', 'factor': 'Faktor Cuaca', 'peringkat': 'Peringkat', 'musim': 'Musim', 'periode': 'Periode',
}
FMT = {'pm25_tahunan': 'n#,##0.0', 'pm10_tahunan': 'n#,##0.0', 'no2_tahunan': 'n#,##0.0', 'o3_tahunan': 'n#,##0.0', 'IKU': 'n#,##0.0',
       'kelengkapan_pct': 'n#,##0', 'critical_score': 'n#,##0', 'pm25_mean': 'n#,##0.0', 'days_ispu_tidak_sehat_plus': 'n#,##0',
       'pm25': 'n#,##0.0', 'no2': 'n#,##0.0', 'co': 'n#,##0', 'pct_hari_lewat_bm24jam_pm25': 'n#,##0.0', 'kemarau_vs_hujan_pm25_pct': 'n+#,##0;-#,##0',
       'hari_kabut_asap_per_stasiun': 'n#,##0', 'jarak_tetangga_median_km': 'n#,##0', 'celah_terlebar_km': 'n#,##0', 'hari_kabut_asap': 'n#,##0',
       'pct_increase_per10': 'n+#,##0.0;-#,##0.0', 'RR_per10': 'n#,##0.000', 'z_diff': 'n#,##0.00', 'RR': 'n#,##0.00', 'attributable': 'n#,##0',
       'pct_increase': 'n+#,##0.0;-#,##0.0', 'share_pct': 'n#,##0.0', 'jarak_km': 'n#,##0', 'selisih_pct': 'n+#,##0.0;-#,##0.0',
       'skor_prioritas': 'n#,##0.0', 'nilai': 'n#,##0.0', 'r_rata2': 'n#,##0.00', 'importance': 'n#,##0.000'}


class DS:
    def __init__(self, key, caption, file, latlon=False):
        self.key, self.caption, self.file = key, caption, file
        self.name = 'federated.' + key
        with open(os.path.join(DATA, file), encoding='utf-8') as f:
            r = csv.reader(f)
            head = next(r)
            sample = list(r)
        self.rows = sample
        self.cols = []
        for i, h in enumerate(head):
            vals = [row[i] for row in sample if i < len(row) and row[i] != '']
            if h in ('tanggal', 'periode', 'start', 'end'):
                dt = 'date'
            elif vals and all(re.fullmatch(r'-?\d+', v) for v in vals):
                dt = 'integer'
            elif vals and all(re.fullmatch(r'-?\d+(\.\d+)?([eE]-?\d+)?', v) for v in vals):
                dt = 'real'
            elif not vals:
                dt = 'real'
            else:
                dt = 'string'
            self.cols.append((h, dt))
        self.types = dict(self.cols)
        self.latlon = latlon
        self.calcs = {}
        self.n = 0

    def calc(self, caption, formula, dt='real', role='measure', typ='quantitative', fmt=None):
        self.n += 1
        cid = f'Calculation_{self.key}{self.n:03d}'
        self.calcs[cid] = dict(caption=caption, formula=formula, dt=dt, role=role, typ=typ, fmt=fmt)
        return cid

    def r(self, deriv, field, kind):
        return f'[{self.name}].[{deriv}:{field}:{kind}]'

    def col_xml(self, name, dt):
        if name in self.calcs:
            c = self.calcs[name]
            fmt = f" default-format='{esc(c['fmt'])}'" if c['fmt'] else ''
            return (f"<column caption='{esc(c['caption'])}' datatype='{c['dt']}'{fmt} name='[{name}]' role='{c['role']}' type='{c['typ']}'>"
                    f"<calculation class='tableau' formula='{esc(c['formula'])}' /></column>")
        cap = CAPTION.get(name)
        capx = f" caption='{esc(cap)}'" if cap else ''
        fmt = f" default-format='{esc(FMT[name])}'" if name in FMT and dt in ('real', 'integer') else ''
        sem = ''
        if self.latlon and name == 'lat':
            sem = " semantic-role='[Geographical].[Latitude]'"
        if self.latlon and name == 'lon':
            sem = " semantic-role='[Geographical].[Longitude]'"
        if dt == 'string':
            role, typ = 'dimension', 'nominal'
        elif dt == 'date':
            role, typ = 'dimension', 'ordinal'
        elif name in INT_DIMS and dt == 'integer':
            role, typ = 'dimension', 'ordinal'
        else:
            role, typ = 'measure', 'quantitative'
        alias = ''
        if name == 'bulan' and role == 'dimension':
            m = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
            alias = '<aliases>' + ''.join(f"<alias key='{i + 1}' value='{v}' />" for i, v in enumerate(m)) + '</aliases>'
        if alias:
            return f"<column{capx} datatype='{dt}'{fmt} name='[{name}]' role='{role}'{sem} type='{typ}'>{alias}</column>"
        return f"<column{capx} datatype='{dt}'{fmt} name='[{name}]' role='{role}'{sem} type='{typ}' />"

    def all_cols_xml(self):
        return ''.join(self.col_xml(n, dt) for n, dt in self.cols) + ''.join(self.col_xml(c, None) for c in self.calcs)

    def xml(self):
        # Tableau Public only accepts extracts: each data source reads its own .hyper file (built from the CSV)
        return (f"<datasource caption='{esc(self.caption)}' inline='true' name='{self.name}' version='18.1'>"
                f"<connection class='federated'><named-connections>"
                f"<named-connection caption='{esc(self.caption)}' name='hyper.{self.key}'>"
                f"<connection authentication='auth-none' author-locale='en_US' class='hyper' dbname='Data/Extracts/{self.hyper}' "
                f"default-settings='yes' port='' sslmode='' username='tableau_internal_user' />"
                f"</named-connection></named-connections>"
                f"<relation connection='hyper.{self.key}' name='Extract' table='[Extract].[Extract]' type='table' />"
                f"</connection><aliases enabled='yes' />{self.all_cols_xml()}"
                f"</datasource>")

    @property
    def hyper(self):
        return self.file.replace('.csv', '.hyper')

    def make_hyper(self, folder):
        from datetime import date
        from tableauhyperapi import (HyperProcess, Telemetry, Connection, CreateMode, TableDefinition, SqlType,
                                     TableName, Inserter, NULLABLE)
        ST = {'string': SqlType.text(), 'integer': SqlType.big_int(), 'real': SqlType.double(), 'date': SqlType.date()}
        conv = {'string': str, 'integer': int, 'real': float, 'date': lambda v: date.fromisoformat(v)}
        path = os.path.join(folder, self.hyper)
        table = TableDefinition(TableName('Extract', 'Extract'), [TableDefinition.Column(n, ST[dt], NULLABLE) for n, dt in self.cols])
        with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
            with Connection(hp.endpoint, path, CreateMode.CREATE_AND_REPLACE) as con:
                con.catalog.create_schema('Extract')
                con.catalog.create_table(table)
                with Inserter(con, table) as ins:
                    for row in self.rows:
                        ins.add_row([None if (i >= len(row) or row[i] == '') else conv[dt](row[i]) for i, (_, dt) in enumerate(self.cols)])
                    ins.execute()
                n = con.execute_scalar_query(f'SELECT COUNT(*) FROM "Extract"."Extract"')
        assert n == len(self.rows), (self.file, n, len(self.rows))
        return n


# ───────────────────────── parameters ─────────────────────────
PARAMS = []


def param(pid, caption, values, default=None, dt='string'):
    PARAMS.append((pid, caption, values, default if default is not None else values[0], dt))
    return f'[Parameters].[{pid}]'


P_PULAU = param('p_pulau', 'Pulau', ['Semua pulau'] + ISL)
P_TIPE = param('p_tipe', 'Tipe Lokasi', ['Semua tipe lokasi'] + CATS)
P_MUSIM = param('p_musim', 'Musim', ['Semua musim', 'Hujan (Nov–Apr)', 'Kemarau (Mei–Okt)', 'Puncak kabut (Agu–Okt)'])
P_TAHUN = param('p_tahun', 'Tahun', ['Semua tahun', '2024', '2025', '2026'])
P_POL = param('p_pol', 'Polutan', [p for p, _ in POLS])
P_JAM = param('p_jam', 'Polutan per Jam', ['PM2.5', 'NO₂', 'CO', 'O₃'])
P_PEKAN = param('p_pekan', 'Polutan Hari Kerja', ['NO₂', 'PM2.5'])
P_LALIN = param('p_lalin', 'Polutan Lalu Lintas', ['PM2.5', 'PM10', 'NO₂', 'CO'])
P_THBM = param('p_thbm', 'Tahun Baku Mutu', ['2024', '2025', '2026'], default='2025')
P_KASUS = param('p_kasus', 'Jenis Kasus', KASUS)
RS_LABELS = []
with open(os.path.join(DATA, 'stasiun.csv'), encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['rumah_sakit']:
            RS_LABELS.append((r['rumah_sakit'], f"{r['rumah_sakit']} ({r['stasiun']})"))
RS_LABELS.sort()
P_RS = param('p_rs', 'Rumah Sakit', [l for _, l in RS_LABELS], default=next(l for h, l in RS_LABELS if h == 'RS-XXX-04'))
P_BM15 = param('p_bm15', 'Baku Mutu Tahunan PM2.5', [15.0], dt='real')
P_BM55 = param('p_bm55', 'Baku Mutu 24 Jam PM2.5', [55.0], dt='real')
P_RR1 = param('p_rr1', 'Risiko Relatif 1', [1.0], dt='real')


def params_cols_xml(only=None):
    out = []
    for pid, cap, vals, default, dt in PARAMS:
        if only is not None and pid not in only:
            continue
        if dt == 'string':
            mem = ''.join(f"<member value='{esc(chr(34) + v + chr(34))}' />" for v in vals)
            dv = esc('"' + default + '"')
            out.append(f"<column caption='{esc(cap)}' datatype='string' name='[{pid}]' param-domain-type='list' role='measure' type='nominal' value='{dv}'>"
                       f"<calculation class='tableau' formula='{dv}' /><members>{mem}</members></column>")
        else:
            out.append(f"<column caption='{esc(cap)}' datatype='real' name='[{pid}]' param-domain-type='any' role='measure' type='quantitative' value='{default}'>"
                       f"<calculation class='tableau' formula='{default}' /></column>")
    return ''.join(out)


def params_xml():
    return f"<datasource hasconnection='false' inline='true' name='Parameters' version='18.1'><aliases enabled='yes' />{params_cols_xml()}</datasource>"


# shared filter conditions (Tableau formula text)
def f_pulau(col='[pulau]'):
    return f'({P_PULAU} = "Semua pulau" OR {col} = {P_PULAU})'


def f_tipe(col='[tipe_lokasi]'):
    return f'({P_TIPE} = "Semua tipe lokasi" OR {col} = {P_TIPE})'


def f_musim(col='[bulan]'):
    return (f'({P_MUSIM} = "Semua musim" OR ({P_MUSIM} = "Hujan (Nov–Apr)" AND ({col} >= 11 OR {col} <= 4)) '
            f'OR ({P_MUSIM} = "Kemarau (Mei–Okt)" AND {col} >= 5 AND {col} <= 10) OR ({P_MUSIM} = "Puncak kabut (Agu–Okt)" AND {col} >= 8 AND {col} <= 10))')


def f_tahun(col='[tahun]'):
    return f'({P_TAHUN} = "Semua tahun" OR STR({col}) = {P_TAHUN})'


def AND(*xs):
    return ' AND '.join(xs)


# ───────────────────────── data sources ─────────────────────────
SB = DS('sb', 'Stasiun Bulanan', 'stasiun_bulanan.csv', latlon=True)
ST = DS('st', 'Profil Stasiun', 'stasiun.csv', latlon=True)
PR = DS('pr', 'Skor Prioritas', 'prioritas.csv')
PJ = DS('pj', 'Pola per Jam', 'pola_jam.csv')
RS = DS('rs', 'Rumah Sakit Harian', 'rs_harian.csv')
TH = DS('th', 'Baku Mutu Tahunan', 'tahunan.csv')
KR = DS('kr', 'Wilayah Kritis', 'kritis.csv')
KW = DS('kw', 'Karakteristik Kawasan', 'kawasan.csv')
EP = DS('ep', 'Episode Kabut Asap', 'episode.csv')
KF = DS('kf', 'Kepentingan Faktor', 'kepentingan_faktor.csv')
KC = DS('kc', 'Korelasi Cuaca', 'korelasi_cuaca.csv')
LL = DS('ll', 'Lalu Lintas', 'lalu_lintas.csv')
AA = DS('aa', 'Arah Angin', 'arah_angin.csv')
JD = DS('jd', 'Efek Jeda', 'jeda.csv')
RI = DS('ri', 'Risiko per ISPU', 'risiko_ispu.csv')
RT = DS('rt', 'Balita dan Lansia', 'rentan.csv')
KK = DS('kk', 'Kasus Saat Kabut', 'kabut_kesehatan.csv')
AT = DS('at', 'Kasus Akibat PM2.5', 'atribusi.csv')
CE = DS('ce', 'Celah Jaringan', 'celah.csv')
CK = DS('ck', 'Cakupan per Pulau', 'cakupan.csv')
ALL_DS = [SB, ST, PR, PJ, RS, TH, KR, KW, EP, KF, KC, LL, AA, JD, RI, RT, KK, AT, CE, CK]

# ───────────────────────── worksheets ─────────────────────────
SHEETS = []   # xml strings
SHEET_NAMES = []


def inst_xml(ref):
    m = re.fullmatch(r'\[([^\]]+)\]\.\[(\w+):(.+):(nk|ok|qk)\]', ref)
    if not m:
        return None, None
    ds, d, f, k = m.groups()
    return ds, f"<column-instance column='[{f}]' derivation='{DERIV[d]}' name='[{d}:{f}:{k}]' pivot='key' type='{KIND[k]}' />"


def title_xml(title, sub=None, align=None):
    a = f" fontalignment='{align}'" if align is not None else ''
    t = f"<run bold='true' fontcolor='#000000' fontname='{FONT}' fontsize='13'{a}>{esc(title)}</run>"
    if sub:
        t += f"<run fontcolor='#000000'{a}>Æ&#10;</run><run fontcolor='#000000' fontname='{FONT}' fontsize='9'{a}>{esc(sub)}</run>"
    return f"<layout-options><title><formatted-text>{t}</formatted-text></title></layout-options>"


def worksheet(name, ds, rows=None, cols=None, mark='Automatic', color=None, size=None, text=None, lod=(), tooltip=(),
              filt=None, sort=None, palette=None, axis=None, title=None, sub=None, mnames=None, refs=(), mark_color=None,
              kpi=False, fmt=None, uses_params=True, hide_row_label=True, mapsheet=False, size_value=None, label_fmt=None):
    """filt: calc id of a boolean filter (row-level). sort: (dim_ref, 'ASC'|'DESC', using_ref).
    palette: (field_ref, {value: color}) . axis: {measure_ref: (scope, title)} . mnames: list of measure refs."""
    rows = rows or []
    cols = cols or []
    refs_used = set(rows) | set(cols)
    for x in (color, size, text):
        if x:
            refs_used.add(x)
    refs_used |= set(lod) | set(tooltip)
    if sort:
        refs_used |= {sort[0], sort[2]}
    if mnames:
        refs_used |= set(mnames)
    for a, v in refs:
        refs_used |= {a, v} - {None}
    fref = None
    if filt:
        fref = ds.r('none', filt, 'nk')
        refs_used.add(fref)
    insts = []
    for r_ in sorted(refs_used):
        dsn, x = inst_xml(r_)
        if x and dsn == ds.name:
            insts.append(x)
    deps = f"<datasource-dependencies datasource='{ds.name}'>{ds.all_cols_xml()}{''.join(insts)}</datasource-dependencies>"
    pdeps = f"<datasource-dependencies datasource='Parameters'>{params_cols_xml()}</datasource-dependencies>" if uses_params else ''
    dss = f"<datasource caption='{esc(ds.caption)}' name='{ds.name}' />" + ("<datasource name='Parameters' />" if uses_params else '')
    view = f"<view><datasources>{dss}</datasources>"
    if mapsheet:
        view += "<mapsources><mapsource name='Tableau' /></mapsources>"
    view += pdeps + deps
    if sort:
        view += f"<computed-sort column='{sort[0]}' direction='{sort[1]}' using='{sort[2]}' />"
    filters, slices = [], []
    if fref:
        lvl = '[' + fref.rsplit('].[', 1)[1]
        filters.append(f"<filter class='categorical' column='{fref}'><groupfilter function='member' level='{lvl}' member='true' "
                       f"user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' /></filter>")
        slices.append(f'<column>{fref}</column>')
    if mnames:
        mn = f'[{ds.name}].[:Measure Names]'
        g = ''.join(f"<groupfilter function='member' level='[:Measure Names]' member='{esc(chr(34) + m + chr(34))}' />" for m in mnames)
        filters.append(f"<filter class='categorical' column='{mn}'><groupfilter function='union' user:op='manual'>{g}</groupfilter></filter>")
        slices.append(f'<column>{mn}</column>')
    view += ''.join(filters)
    if slices:
        view += '<slices>' + ''.join(slices) + '</slices>'
    view += "<aggregation value='true' /></view>"

    st = []
    if palette:
        f, mp = palette
        maps = ''.join(f"<map to='{c}'><bucket>{esc(chr(34) + k + chr(34))}</bucket></map>" for k, c in mp.items())
        st.append(f"<style-rule element='mark'><encoding attr='color' field='{f}' type='palette'>{maps}</encoding></style-rule>")
    ax = ''
    for m, (scope, t) in (axis or {}).items():
        ax += f"<format attr='title' class='0' field='{m}' scope='{scope}' value='{esc(t)}' />"
    if ax:
        st.append(f"<style-rule element='axis'>{ax}</style-rule>")
    if hide_row_label:
        st.append("<style-rule element='worksheet'><format attr='display-field-labels' scope='rows' value='false' />"
                  "<format attr='display-field-labels' scope='cols' value='false' /></style-rule>")
    st.append(f"<style-rule element='all'><format attr='font-family' value='{FONT}' /><format attr='color' value='#000000' /></style-rule>")
    cell = []
    if kpi:
        cell.append("<format attr='text-align' value='center' />")
    for i, (a, v) in enumerate(refs):
        st.append(f"<style-rule element='refline'><format attr='stroke-size' id='refline{i}' value='1.5' /><format attr='stroke-color' id='refline{i}' value='#000000' /></style-rule>")
    for k, v in (fmt or {}).items():
        cell.append(f"<format attr='text-format' field='{k}' value='{esc(v)}' />")
    if cell:
        st.append("<style-rule element='cell'>" + ''.join(cell) + '</style-rule>')
    style = '<style>' + ''.join(st) + '</style>'

    enc = ''
    if color:
        enc += f"<color column='{color}' />"
    if size:
        enc += f"<size column='{size}' />"
    if text:
        enc += f"<text column='{text}' />"
    for l_ in lod:
        enc += f"<lod column='{l_}' />"
    for t_ in tooltip:
        enc += f"<tooltip column='{t_}' />"
    pane_style = ''
    pst = []
    if mark_color:
        pst.append(f"<format attr='mark-color' value='{mark_color}' />")
    if size_value:
        pst.append(f"<format attr='size' value='{size_value}' />")
    if kpi:
        pst.append("<format attr='mark-labels-show' value='true' />")
    if pst:
        pane_style = "<style><style-rule element='mark'>" + ''.join(pst) + '</style-rule></style>'
    rl = ''.join(f"<reference-line axis-column='{a}' enable-instant-analytics='false' formula='average' id='refline{i}' label-type='none' "
                 f"scope='per-table' value-column='{v}' z-order='{i + 1}' />" for i, (a, v) in enumerate(refs))
    lab = ''
    if kpi and text:
        lab = (f"<customized-label><formatted-text><run fontalignment='1' fontcolor='#000000' fontname='{FONT}' fontsize='26'>"
               f"<![CDATA[<{text}>]]></run></formatted-text></customized-label>")
    pane = (f"<panes><pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view>"
            f"<mark class='{mark}' /><encodings>{enc}</encodings>{rl}{lab}{pane_style}</pane></panes>")

    def shelf(items):
        if not items:
            return ''
        if len(items) == 1:
            return items[0]
        if all(':qk]' in i or 'Multiple Values' in i for i in items):
            return '(' + ' + '.join(items) + ')'
        return '(' + ' / '.join(items) + ')'
    table = f"<table>{view}{style}{pane}<rows>{shelf(rows)}</rows><cols>{shelf(cols)}</cols></table>"
    t = title_xml(title or name, sub, align=1 if kpi else None)
    SHEETS.append(f"<worksheet name='{esc(name)}'>{t}{table}<simple-id uuid='{sid()}' /></worksheet>")
    SHEET_NAMES.append(name)
    return name


# ─── station x month (main source) ───
F_SB = SB.calc('Filter Udara', AND(f_pulau(), f_tipe(), f_musim(), f_tahun(), '[dipakai] = 1'), 'boolean', 'dimension', 'nominal')
F_SB_ALL = SB.calc('Filter Semua RS', AND(f_pulau(), f_tipe(), f_musim(), f_tahun()), 'boolean', 'dimension', 'nominal')
ST_MEAN = '{INCLUDE [stasiun] : IF SUM([vd_pm25]) >= 10 THEN SUM([hs_pm25]) / SUM([hn_pm25]) END}'
C_PM25ST = SB.calc('PM2.5 Rata-Rata Stasiun', ST_MEAN, fmt='n#,##0.0')
C_PM25RAW = SB.calc('PM2.5 Rata-Rata', 'IF SUM([vd_pm25]) >= 10 THEN SUM([hs_pm25]) / SUM([hn_pm25]) END', fmt='n#,##0.0')
C_KELAS = SB.calc('Kategori PM2.5', (f'IF ISNULL([{C_PM25RAW}]) THEN NULL ELSEIF [{C_PM25RAW}] <= 15.5 THEN "Baik" ELSEIF [{C_PM25RAW}] <= 55.4 THEN "Sedang" '
                                     f'ELSEIF [{C_PM25RAW}] <= 150.4 THEN "Tidak Sehat" ELSEIF [{C_PM25RAW}] <= 250.4 THEN "Sangat Tidak Sehat" ELSE "Berbahaya" END'),
                  'string', 'dimension', 'nominal')
TOT = 'SUM([hari_baik]) + SUM([hari_sedang]) + SUM([hari_tidak_sehat]) + SUM([hari_sangat_tidak_sehat]) + SUM([hari_berbahaya])'
C_TS = SB.calc('Hari Tidak Sehat', f'(SUM([hari_tidak_sehat]) + SUM([hari_sangat_tidak_sehat]) + SUM([hari_berbahaya])) / ({TOT})', fmt='p0.0%')
C_SHARE = [SB.calc(lbl, f'SUM([{col}]) / ({TOT})', fmt='p0.0%') for lbl, col in
           zip(ISPU, ['hari_baik', 'hari_sedang', 'hari_tidak_sehat', 'hari_sangat_tidak_sehat', 'hari_berbahaya'])]


def pcase(prefix):
    return f'CASE {P_POL} ' + ' '.join(f'WHEN "{l}" THEN [{prefix}_{c}]' for l, c in POLS) + ' END'


C_HS, C_HN, C_VD, C_DS, C_DN = [SB.calc(f'{p} Terpilih', pcase(p)) for p in ('hs', 'hn', 'vd', 'ds', 'dn')]
C_POLST = SB.calc('Rata-Rata Stasiun (Polutan Terpilih)', f'{{INCLUDE [stasiun] : IF SUM([{C_VD}]) >= 10 THEN SUM([{C_HS}]) / SUM([{C_HN}]) END}}', fmt='n#,##0.0')
C_POLRAW = SB.calc('Rata-Rata (Polutan Terpilih)', f'IF SUM([{C_VD}]) >= 10 THEN SUM([{C_HS}]) / SUM([{C_HN}]) END', fmt='n#,##0.0')
C_TREND = SB.calc('Rata-Rata Bulanan', f'SUM([{C_DS}]) / SUM([{C_DN}])', fmt='n#,##0.0')
C_BM = SB.calc('Baku Mutu Tahunan', f'CASE {P_POL} WHEN "PM2.5" THEN 15 WHEN "PM10" THEN 40 WHEN "SO₂" THEN 45 WHEN "NO₂" THEN 50 WHEN "O₃" THEN 35 END')
C_WHO = SB.calc('Pedoman WHO Tahunan', f'CASE {P_POL} WHEN "PM2.5" THEN 5 WHEN "PM10" THEN 15 WHEN "NO₂" THEN 10 END')
C_BM24 = SB.calc('Baku Mutu 24 Jam', f'CASE {P_POL} WHEN "PM2.5" THEN 55 WHEN "PM10" THEN 75 WHEN "SO₂" THEN 75 WHEN "NO₂" THEN 65 END')
C_OVER = SB.calc('Melampaui Baku Mutu',
                 'STR(SUM({INCLUDE [stasiun] : IF SUM([vd_pm25]) >= 10 AND SUM([hs_pm25]) / SUM([hn_pm25]) > 15 THEN 1 ELSE 0 END})) + " / " + '
                 'STR(SUM({INCLUDE [stasiun] : IF SUM([vd_pm25]) >= 10 THEN 1 ELSE 0 END}))', 'string', 'measure', 'nominal')
C_TOPISL = SB.calc('Pulau Paling Tercemar',
                   'MID(MAX({INCLUDE [pulau] : STR(INT(10000 + ROUND(AVG({INCLUDE [stasiun] : IF SUM([vd_pm25]) >= 10 THEN SUM([hs_pm25]) / SUM([hn_pm25]) END}) * 10, 0))) + MIN([pulau])}), 6)',
                   'string', 'measure', 'nominal')

# ─── Ringkasan ───
K_SB = dict(uses_params=True, kpi=True, mark='Text')
worksheet('KPI Rata-Rata PM2.5', SB, text=SB.r('avg', C_PM25ST, 'qk'), filt=F_SB, title='Rata-Rata PM2.5', fmt={SB.r('avg', C_PM25ST, 'qk'): 'n#,##0.0" µg/m³"'}, **K_SB)
worksheet('KPI Hari Tidak Sehat', SB, text=SB.r('usr', C_TS, 'qk'), filt=F_SB, title='Hari Tidak Sehat', **K_SB)
worksheet('KPI Hari Kabut Asap', SB, text=SB.r('sum', 'hari_kabut_asap', 'qk'), filt=F_SB, title='Hari Kabut Asap', fmt={SB.r('sum', 'hari_kabut_asap', 'qk'): 'n#,##0'}, **K_SB)
worksheet('KPI Kasus ISPA Balita', SB, text=SB.r('sum', 'ispa_balita', 'qk'), filt=F_SB_ALL, title='Kasus ISPA Balita', fmt={SB.r('sum', 'ispa_balita', 'qk'): 'n#,##0'}, **K_SB)
kelas = SB.r('usr', C_KELAS, 'nk')
worksheet('Peta PM2.5', SB, rows=[SB.r('avg', 'lat', 'qk')], cols=[SB.r('avg', 'lon', 'qk')], mark='Circle', color=kelas, size=SB.r('usr', C_PM25RAW, 'qk'),
          lod=[SB.r('none', 'stasiun', 'nk'), SB.r('none', 'kota', 'nk')], filt=F_SB, palette=(kelas, C_ISPU), mapsheet=True, title='Peta PM2.5 per Stasiun',
          sub='Warna = kategori ISPU dari rata-rata PM2.5 stasiun, ukuran = PM2.5 rata-rata')
pul = SB.r('none', 'pulau', 'nk')
worksheet('PM2.5 per Pulau', SB, rows=[pul], cols=[SB.r('avg', C_PM25ST, 'qk')], mark='Bar', color=pul, filt=F_SB, palette=(pul, C_ISL),
          sort=(pul, 'DESC', SB.r('avg', C_PM25ST, 'qk')), axis={SB.r('avg', C_PM25ST, 'qk'): ('cols', 'PM2.5 rata-rata (µg/m³)')},
          refs=[(SB.r('avg', C_PM25ST, 'qk'), P_BM15)], sub='Garis: baku mutu tahunan PM2.5 (15 µg/m³)')
mn_ref = f'[{SB.name}].[:Measure Names]'
share_refs = [SB.r('usr', c, 'qk') for c in C_SHARE]
pal_ispu_m = (mn_ref, {r: C_ISPU[l] for r, l in zip(share_refs, ISPU)})
worksheet('Kategori ISPU per Pulau', SB, rows=[pul], cols=[f'[{SB.name}].[Multiple Values]'], mark='Bar', color=mn_ref, filt=F_SB, mnames=share_refs,
          palette=pal_ispu_m, axis={f'[{SB.name}].[Multiple Values]': ('cols', 'Porsi hari (%)')}, sort=(pul, 'DESC', SB.r('usr', C_SHARE[2], 'qk')))

# ─── Kondisi ───
stn = SB.r('none', 'stasiun', 'nk')
worksheet('KPI Melampaui Baku Mutu', SB, text=SB.r('usr', C_OVER, 'nk'), filt=F_SB, title='Melampaui Baku Mutu', **K_SB)
worksheet('KPI Pulau Paling Tercemar', SB, text=SB.r('usr', C_TOPISL, 'nk'), filt=F_SB, title='Pulau Paling Tercemar', **K_SB)
worksheet('KPI Rata-Rata Polutan', SB, text=SB.r('avg', C_POLST, 'qk'), filt=F_SB, title='Rata-Rata Polutan Terpilih', fmt={SB.r('avg', C_POLST, 'qk'): 'n#,##0.0" µg/m³"'}, **K_SB)
worksheet('Peringkat Stasiun', SB, rows=[stn], cols=[SB.r('usr', C_POLRAW, 'qk')], mark='Bar', color=pul, filt=F_SB, palette=(pul, C_ISL),
          lod=[SB.r('avg', C_BM, 'qk'), SB.r('avg', C_WHO, 'qk')], sort=(stn, 'DESC', SB.r('usr', C_POLRAW, 'qk')),
          refs=[(SB.r('usr', C_POLRAW, 'qk'), SB.r('avg', C_BM, 'qk')), (SB.r('usr', C_POLRAW, 'qk'), SB.r('avg', C_WHO, 'qk'))],
          axis={SB.r('usr', C_POLRAW, 'qk'): ('cols', 'Rata-rata polutan terpilih (µg/m³)')}, sub='Garis: baku mutu tahunan dan pedoman WHO 2021 untuk polutan terpilih')
worksheet('Kategori ISPU per Stasiun', SB, rows=[stn], cols=[f'[{SB.name}].[Multiple Values]'], mark='Bar', color=mn_ref, filt=F_SB, mnames=share_refs,
          palette=pal_ispu_m, axis={f'[{SB.name}].[Multiple Values]': ('cols', 'Porsi hari (%)')}, sort=(stn, 'DESC', SB.r('usr', C_SHARE[0], 'qk')))
worksheet('Tren Bulanan', SB, rows=[SB.r('usr', C_TREND, 'qk')], cols=[SB.r('tmn', 'periode', 'qk')], mark='Line', color=pul, filt=F_SB, palette=(pul, C_ISL),
          lod=[SB.r('avg', C_BM24, 'qk')], refs=[(SB.r('usr', C_TREND, 'qk'), SB.r('avg', C_BM24, 'qk'))],
          axis={SB.r('usr', C_TREND, 'qk'): ('rows', 'Rata-rata bulanan (µg/m³)'), SB.r('tmn', 'periode', 'qk'): ('cols', 'Bulan')},
          sub='Garis: baku mutu 24 jam untuk polutan terpilih')
worksheet('Pola per Bulan', SB, rows=[stn], cols=[SB.r('none', 'bulan', 'ok')], mark='Square', color=SB.r('usr', C_POLRAW, 'qk'), filt=F_SB,
          sort=(stn, 'DESC', SB.r('usr', C_POLRAW, 'qk')), sub='Rata-rata polutan terpilih per stasiun dan bulan (µg/m³)')

# profile source
F_ST = ST.calc('Filter Stasiun', AND(f_pulau(), f_tipe(), '[dipakai] = 1'), 'boolean', 'dimension', 'nominal')
F_ST_ALL = ST.calc('Filter Jaringan', AND(f_pulau(), f_tipe()), 'boolean', 'dimension', 'nominal')
C_WORSE = ST.calc('Stasiun Memburuk', 'STR(SUM(IF [tren] = "Memburuk" THEN 1 ELSE 0 END)) + " / " + STR(COUNT([stasiun]))', 'string', 'measure', 'nominal')
C_ANDAL = ST.calc('Stasiun Andal', 'STR(SUM(IF [keandalan] = "Baik" THEN 1 ELSE 0 END)) + " / " + STR(COUNT([stasiun]))', 'string', 'measure', 'nominal')
C_PTOP = ST.calc('Prioritas Utama', 'MID(MAX(STR(INT(100000 + ROUND([skor_prioritas] * 100, 0))) + [stasiun]), 7)', 'string', 'measure', 'nominal')
worksheet('KPI Stasiun Memburuk', ST, text=ST.r('usr', C_WORSE, 'nk'), filt=F_ST, title='Stasiun Memburuk', **K_SB)
stn2 = ST.r('none', 'stasiun', 'nk')
yrs = [ST.r('avg', 'pm25_2024', 'qk'), ST.r('avg', 'pm25_2025', 'qk'), ST.r('avg', 'pm25_2026', 'qk')]
mn_st = f'[{ST.name}].[:Measure Names]'
worksheet('Perbandingan 2024–2026', ST, rows=[stn2], cols=[f'[{ST.name}].[Multiple Values]'], mark='Circle', color=mn_st, filt=F_ST, mnames=yrs,
          palette=(mn_st, dict(zip(yrs, ['#9ec5f4', '#3987e5', '#0d366b']))), sort=(stn2, 'DESC', yrs[2]),
          axis={f'[{ST.name}].[Multiple Values]': ('cols', 'PM2.5 rata-rata 1 Jan–14 Okt (µg/m³)')})

# annual standards + IKU
F_TH = TH.calc('Filter Tahunan', AND(f_pulau(), f_tipe(), f'STR([tahun]) = {P_THBM}'), 'boolean', 'dimension', 'nominal')
th_m = [TH.r('avg', c, 'qk') for c in ('pm25_tahunan', 'pm10_tahunan', 'no2_tahunan', 'o3_tahunan', 'IKU', 'kelengkapan_pct')]
worksheet('Baku Mutu dan IKU', TH, rows=[TH.r('none', 'stasiun', 'nk'), TH.r('none', 'IKU_kategori', 'nk')], cols=[f'[{TH.name}].[:Measure Names]'],
          mark='Text', text=f'[{TH.name}].[Multiple Values]', filt=F_TH, mnames=th_m, sort=(TH.r('none', 'stasiun', 'nk'), 'DESC', th_m[0]),
          hide_row_label=False, sub='Rata-rata tahunan (µg/m³). Angka dalam kurung pada judul kolom = baku mutu tahunan.')

# ─── Waktu kritis ───
F_JAM = PJ.calc('Filter Pola Jam', AND(f_pulau(), f_tipe(), '[dipakai] = 1', f'[polutan] = {P_JAM}', '[jenis_hari] = "Semua hari"'), 'boolean', 'dimension', 'nominal')
F_PEKAN = PJ.calc('Filter Hari Kerja', AND(f_pulau(), f_tipe(), '[dipakai] = 1', f'[polutan] = {P_PEKAN}', '[jenis_hari] <> "Semua hari"'), 'boolean', 'dimension', 'nominal')
tl = PJ.r('none', 'tipe_lokasi', 'nk')
jh = PJ.r('none', 'jenis_hari', 'nk')
worksheet('Pola per Jam', PJ, rows=[PJ.r('avg', 'nilai', 'qk')], cols=[PJ.r('none', 'jam', 'ok')], mark='Line', color=tl, filt=F_JAM, palette=(tl, C_CAT),
          axis={PJ.r('avg', 'nilai', 'qk'): ('rows', 'Rata-rata (µg/m³)')}, hide_row_label=False, sub='Rata-rata tiap jam (WIB) per tipe lokasi, hari tanpa kabut asap')
worksheet('Hari Kerja dan Akhir Pekan', PJ, rows=[PJ.r('avg', 'nilai', 'qk')], cols=[PJ.r('none', 'jam', 'ok')], mark='Line', color=jh, filt=F_PEKAN,
          palette=(jh, {'Hari kerja': SER[0], 'Akhir pekan': SER[1]}), axis={PJ.r('avg', 'nilai', 'qk'): ('rows', 'Rata-rata (µg/m³)')}, hide_row_label=False)
F_EP = EP.calc('Filter Episode', AND(f_pulau(), f_tipe(), f_tahun('[tahun]')), 'boolean', 'dimension', 'nominal')
worksheet('KPI Episode Kabut Asap', EP, text=EP.r('ctd', 'haze_episode_id', 'qk'), filt=F_EP, title='Episode Kabut Asap', **K_SB)
worksheet('KPI PM2.5 Harian Tertinggi', EP, text=EP.r('max', 'pm25_peak_daily', 'qk'), filt=F_EP, title='PM2.5 Harian Tertinggi',
          fmt={EP.r('max', 'pm25_peak_daily', 'qk'): 'n#,##0" µg/m³"'}, **K_SB)
eps = EP.r('none', 'stasiun', 'nk')
epp = EP.r('none', 'pulau', 'nk')
worksheet('Episode Kabut Asap', EP, rows=[eps], cols=[EP.r('tdy', 'start', 'qk')], mark='GanttBar', size=EP.r('sum', 'days', 'qk'), color=epp, filt=F_EP,
          palette=(epp, C_ISL), lod=[EP.r('none', 'haze_episode_id', 'nk')], tooltip=[EP.r('max', 'pm25_peak_daily', 'qk')],
          axis={EP.r('tdy', 'start', 'qk'): ('cols', 'Tanggal')}, sub='Setiap batang = satu episode, panjang = lama episode (hari)')
F_KR = KR.calc('Filter Wilayah Kritis', AND(f_pulau(), f_tipe()), 'boolean', 'dimension', 'nominal')
kr_m = [KR.r('avg', c, 'qk') for c in ('critical_score', 'pm25_mean', 'days_ispu_tidak_sehat_plus')]
worksheet('Peringkat Wilayah Kritis', KR, rows=[KR.r('none', 'peringkat', 'ok'), KR.r('none', 'stasiun', 'nk'), KR.r('none', 'provinsi', 'nk')],
          cols=[f'[{KR.name}].[:Measure Names]'], mark='Text', text=f'[{KR.name}].[Multiple Values]', filt=F_KR, mnames=kr_m, hide_row_label=False)
F_KW = KW.calc('Filter Kawasan', f_tipe(), 'boolean', 'dimension', 'nominal')
kw_m = [KW.r('avg', c, 'qk') for c in ('n_stasiun', 'pm25', 'no2', 'co', 'pct_hari_lewat_bm24jam_pm25', 'kemarau_vs_hujan_pm25_pct', 'hari_kabut_asap_per_stasiun')]
worksheet('Karakteristik Kawasan', KW, rows=[KW.r('none', 'tipe_lokasi', 'nk')], cols=[f'[{KW.name}].[:Measure Names]'], mark='Text',
          text=f'[{KW.name}].[Multiple Values]', filt=F_KW, mnames=kw_m, sort=(KW.r('none', 'tipe_lokasi', 'nk'), 'DESC', kw_m[1]), hide_row_label=False)

# ─── Penyebab ───
kfr = KF.r('none', 'faktor', 'nk')
worksheet('Tingkat Kepentingan Faktor', KF, rows=[kfr], cols=[KF.r('sum', 'share_pct', 'qk')], mark='Bar', mark_color=SER[0], uses_params=False,
          sort=(kfr, 'DESC', KF.r('sum', 'share_pct', 'qk')), axis={KF.r('sum', 'share_pct', 'qk'): ('cols', 'Porsi kepentingan (%)')},
          sub='Penurunan R² model Random Forest saat faktor diacak, dalam persen dari total')
worksheet('Korelasi dengan Cuaca', KC, rows=[KC.r('none', 'pollutant', 'nk')], cols=[KC.r('none', 'factor', 'nk')], mark='Square',
          color=KC.r('avg', 'r_rata2', 'qk'), uses_params=False, hide_row_label=False, sub='Spearman r rata-rata antarjam per stasiun (−1 sampai 1)')
F_LL = LL.calc('Filter Lalu Lintas', AND(f_pulau(), f_tipe()), 'boolean', 'dimension', 'nominal')
C_LL = LL.calc('Polutan Lalu Lintas', f'CASE {P_LALIN} WHEN "PM2.5" THEN [pm25] WHEN "PM10" THEN [pm10] WHEN "NO₂" THEN [no2] WHEN "CO" THEN [co] END', fmt='n#,##0.0')
llt = LL.r('none', 'tipe_lokasi', 'nk')
worksheet('Lalu Lintas dan Polutan', LL, rows=[LL.r('avg', C_LL, 'qk')], cols=[LL.r('avg', 'traffic_intensity_per_h', 'qk')], mark='Circle', color=llt,
          size=LL.r('avg', 'distance_to_road_m', 'qk'), lod=[LL.r('none', 'stasiun', 'nk')], filt=F_LL, palette=(llt, C_CAT),
          axis={LL.r('avg', C_LL, 'qk'): ('rows', 'Rata-rata musim hujan (µg/m³)'), LL.r('avg', 'traffic_intensity_per_h', 'qk'): ('cols', 'Lalu lintas (kendaraan/jam)')},
          sub='Ukuran titik = jarak ke jalan raya (m)')
F_AA = AA.calc('Filter Arah Angin', AND(f_pulau(), f_tipe()), 'boolean', 'dimension', 'nominal')
C_WIND = AA.calc('Pengaruh Arah Angin', 'STR(SUM(IF [sector_ratio] >= 1.1 THEN 1 ELSE 0 END)) + " / " + STR(COUNT([sector_ratio]))', 'string', 'measure', 'nominal')
worksheet('KPI Pengaruh Arah Angin', AA, text=AA.r('usr', C_WIND, 'nk'), filt=F_AA, title='Pengaruh Arah Angin', **K_SB)
aas = AA.r('none', 'stasiun', 'nk')
aat = AA.r('none', 'tipe_lokasi', 'nk')
worksheet('Pengaruh Arah Angin', AA, rows=[aas], cols=[AA.r('avg', 'selisih_pct', 'qk')], mark='Bar', color=aat, filt=F_AA, palette=(aat, C_CAT),
          sort=(aas, 'DESC', AA.r('avg', 'selisih_pct', 'qk')), axis={AA.r('avg', 'selisih_pct', 'qk'): ('cols', 'PM2.5 arah terkotor dibanding terbersih (%)')})

# ─── Kesehatan ───
F_RS = RS.calc('Filter Rumah Sakit', AND(f'([rumah_sakit] + " (" + [stasiun] + ")") = {P_RS}', f_musim(), f_tahun()), 'boolean', 'dimension', 'nominal')
C_K = RS.calc('Kasus Harian', f'CASE {P_KASUS} ' + ' '.join(f'WHEN "{l}" THEN [{c}]' for l, c in zip(KASUS, KCOL)) + ' END', fmt='n#,##0')
C_K7 = RS.calc('Kasus Rata-Rata 7 Hari', f'CASE {P_KASUS} ' + ' '.join(f'WHEN "{l}" THEN [{c}_7h]' for l, c in zip(KASUS, KCOL)) + ' END', fmt='n#,##0.0')
rs_m = [RS.r('avg', 'pm25', 'qk'), RS.r('sum', C_K, 'qk'), RS.r('sum', C_K7, 'qk')]
worksheet('Paparan dan Kasus Harian', RS, rows=rs_m, cols=[RS.r('tdy', 'tanggal', 'qk')], mark='Line', filt=F_RS, color=f'[{RS.name}].[:Measure Names]',
          palette=(f'[{RS.name}].[:Measure Names]', dict(zip(rs_m, [SER[0], '#c9ccd4', SER[1]]))),
          axis={rs_m[0]: ('rows', 'PM2.5 harian (µg/m³)'), rs_m[1]: ('rows', 'Kasus harian'), rs_m[2]: ('rows', 'Rata-rata 7 hari'), RS.r('tdy', 'tanggal', 'qk'): ('cols', 'Tanggal')},
          sub='Rumah sakit terpilih dan PM2.5 stasiun pasangannya')
F_JD = JD.calc('Filter Jeda', f'[kasus] = {P_KASUS} AND [kumulatif] = 0', 'boolean', 'dimension', 'nominal')
F_JD0 = JD.calc('Filter Jeda 0', f'[kasus] = {P_KASUS} AND [jeda] = 0', 'boolean', 'dimension', 'nominal')
F_JDC = JD.calc('Filter Kumulatif', f'[kasus] = {P_KASUS} AND [kumulatif] = 1', 'boolean', 'dimension', 'nominal')
pct_fmt = 'n+#,##0.0"%";-#,##0.0"%"'
worksheet('KPI Kenaikan per 10', JD, text=JD.r('avg', 'pct_increase_per10', 'qk'), filt=F_JD0, title='Kenaikan per 10 µg/m³',
          fmt={JD.r('avg', 'pct_increase_per10', 'qk'): pct_fmt}, **K_SB)
worksheet('KPI Efek Kumulatif', JD, text=JD.r('avg', 'pct_increase_per10', 'qk'), filt=F_JDC, title='Efek Kumulatif 7 Hari',
          fmt={JD.r('avg', 'pct_increase_per10', 'qk'): pct_fmt}, **K_SB)
worksheet('Efek per Hari Jeda', JD, rows=[JD.r('avg', 'pct_increase_per10', 'qk')], cols=[JD.r('none', 'jeda', 'ok')], mark='Bar', mark_color=SER[1], filt=F_JD,
          axis={JD.r('avg', 'pct_increase_per10', 'qk'): ('rows', 'Kenaikan kasus per 10 µg/m³ (%)')}, hide_row_label=False,
          sub='Hari jeda setelah paparan (0 = hari yang sama)')
F_KK = KK.calc('Filter Kabut', f'[kasus] = {P_KASUS}', 'boolean', 'dimension', 'nominal')
worksheet('KPI Saat Kabut Asap', KK, text=KK.r('avg', 'pct_increase', 'qk'), filt=F_KK, title='Saat Kabut Asap', fmt={KK.r('avg', 'pct_increase', 'qk'): 'n+#,##0"%";-#,##0"%"'}, **K_SB)
kkk = KK.r('none', 'kasus', 'nk')
worksheet('Kasus Saat Kabut Asap', KK, rows=[kkk], cols=[KK.r('avg', 'pct_increase', 'qk')], mark='Bar', color=kkk, uses_params=False, palette=(kkk, C_KASUS),
          sort=(kkk, 'DESC', KK.r('avg', 'pct_increase', 'qk')), axis={KK.r('avg', 'pct_increase', 'qk'): ('cols', 'Kenaikan kasus saat kabut asap (%)')})
F_RI = RI.calc('Filter Risiko', f'[kasus] = {P_KASUS} OR [kasus] = "ISPA balita" OR [kasus] = "ISPA lansia" OR [kasus] = "Kardiovaskular" OR [kasus] = "Kematian"',
               'boolean', 'dimension', 'nominal')
rib = RI.r('none', 'band', 'nk')
rik = RI.r('none', 'kasus', 'nk')
worksheet('Risiko per Kategori ISPU', RI, rows=[RI.r('avg', 'RR', 'qk')], cols=[rib, rik], mark='Bar', color=rik, filt=F_RI, palette=(rik, C_KASUS),
          sort=(rib, 'ASC', RI.r('min', 'urutan', 'qk')), refs=[(RI.r('avg', 'RR', 'qk'), P_RR1)],
          axis={RI.r('avg', 'RR', 'qk'): ('rows', 'Risiko relatif terhadap hari Baik')}, sub='Garis: risiko relatif 1 (sama dengan hari Baik)')
F_AT = AT.calc('Filter Atribusi', AND(f'[kasus] = {P_KASUS}', '[pulau] <> "Total"', f_pulau()), 'boolean', 'dimension', 'nominal')
F_AT0 = AT.calc('Filter Atribusi Total', AND(f'[kasus] = {P_KASUS}', '[pulau] = "Total"'), 'boolean', 'dimension', 'nominal')
worksheet('KPI Kasus Akibat PM2.5', AT, text=AT.r('sum', 'attributable', 'qk'), filt=F_AT0, title='Kasus Akibat PM2.5', fmt={AT.r('sum', 'attributable', 'qk'): 'n#,##0'}, **K_SB)
atp = AT.r('none', 'pulau', 'nk')
worksheet('Kasus Akibat PM2.5', AT, rows=[atp], cols=[AT.r('sum', 'attributable', 'qk')], mark='Bar', color=atp, filt=F_AT, palette=(atp, C_ISL),
          sort=(atp, 'DESC', AT.r('sum', 'attributable', 'qk')), axis={AT.r('sum', 'attributable', 'qk'): ('cols', 'Kasus akibat PM2.5')})
rt_m = [RT.r('avg', c, 'qk') for c in ('pct_increase_per10', 'RR_per10', 'n_hospitals', 'z_diff')]
worksheet('Balita dan Lansia', RT, rows=[RT.r('none', 'scope', 'nk'), RT.r('none', 'group', 'nk')], cols=[f'[{RT.name}].[:Measure Names]'], mark='Text',
          text=f'[{RT.name}].[Multiple Values]', mnames=rt_m, uses_params=False, hide_row_label=False, sub='|z| ≥ 1,96 berarti balita dan lansia berbeda bermakna')

# ─── Jaringan ───
worksheet('KPI Stasiun Andal', ST, text=ST.r('usr', C_ANDAL, 'nk'), filt=F_ST_ALL, title='Stasiun Andal', **K_SB)
worksheet('KPI Prioritas Utama', ST, text=ST.r('usr', C_PTOP, 'nk'), filt=F_ST_ALL, title='Prioritas Utama', **K_SB)
F_CE = CE.calc('Filter Celah', f_pulau(), 'boolean', 'dimension', 'nominal')
worksheet('KPI Celah Terlebar', CE, text=CE.r('max', 'jarak_km', 'qk'), filt=F_CE, title='Celah Terlebar', fmt={CE.r('max', 'jarak_km', 'qk'): 'n#,##0" km"'}, **K_SB)
F_CK = CK.calc('Filter Cakupan', f_pulau(), 'boolean', 'dimension', 'nominal')
worksheet('KPI Provinsi Terpantau', CK, text=CK.r('sum', 'n_provinsi_tercakup', 'qk'), filt=F_CK, title='Provinsi Terpantau', **K_SB)
rel = ST.r('none', 'keandalan', 'nk')
worksheet('Peta Jaringan', ST, rows=[ST.r('avg', 'lat', 'qk')], cols=[ST.r('avg', 'lon', 'qk')], mark='Circle', color=rel, lod=[stn2, ST.r('none', 'kota', 'nk')],
          filt=F_ST_ALL, palette=(rel, C_REL), mapsheet=True, size_value='1.6', title='Sebaran Stasiun', sub='Warna = keandalan alat')
C_WIDE = CE.calc('Kelas Celah', 'IF [jarak_km] >= 300 THEN "Celah ≥300 km" ELSE "Celah <300 km" END', 'string', 'dimension', 'nominal')
cep = CE.r('none', 'pasangan', 'nk')
cew = CE.r('none', C_WIDE, 'nk')
worksheet('Celah Jaringan', CE, rows=[cep], cols=[CE.r('sum', 'jarak_km', 'qk')], mark='Bar', color=cew, filt=F_CE,
          palette=(cew, {'Celah ≥300 km': '#d03b3b', 'Celah <300 km': '#c9ccd4'}), sort=(cep, 'DESC', CE.r('sum', 'jarak_km', 'qk')),
          axis={CE.r('sum', 'jarak_km', 'qk'): ('cols', 'Jarak antarstasiun bertetangga (km)')}, sub='Jaringan terpendek antarstasiun dalam satu pulau')
F_PR = PR.calc('Filter Prioritas', AND(f_pulau(), f_tipe()), 'boolean', 'dimension', 'nominal')
prs = PR.r('none', 'stasiun', 'nk')
prk = PR.r('none', 'komponen', 'nk')
KOMP = ['Polusi (25%)', 'Kabut asap (20%)', 'Beban kesehatan (20%)', 'Defisit data (20%)', 'Keterisolasian (15%)']
worksheet('Skor Prioritas Stasiun', PR, rows=[prs], cols=[PR.r('sum', 'nilai', 'qk')], mark='Bar', color=prk, filt=F_PR, palette=(prk, dict(zip(KOMP, SER))),
          sort=(prs, 'DESC', PR.r('sum', 'nilai', 'qk')), axis={PR.r('sum', 'nilai', 'qk'): ('cols', 'Skor prioritas (0–100)')})
ck_m = [CK.r('avg', c, 'qk') for c in ('n_stasiun', 'n_stasiun_andal', 'n_provinsi_tercakup', 'jarak_tetangga_median_km', 'celah_terlebar_km', 'pm25_mean', 'hari_kabut_asap')]
worksheet('Cakupan per Pulau', CK, rows=[CK.r('none', 'pulau', 'nk')], cols=[f'[{CK.name}].[:Measure Names]'], mark='Text', text=f'[{CK.name}].[Multiple Values]',
          filt=F_CK, mnames=ck_m, hide_row_label=False)

# ───────────────────────── dashboards ─────────────────────────
W = 1200
DASH = []
WINDOWS = []
STATIC = {}
with open(os.path.join(DATA, 'kepentingan_faktor.csv'), encoding='utf-8') as f:
    top = max(csv.DictReader(f), key=lambda r: float(r['importance']))
    STATIC['faktor'] = top['faktor'].replace(' (bulan)', '')
with open(os.path.join(DATA, 'faktor_lokasi.csv'), encoding='utf-8') as f:
    rho = next(r for r in csv.DictReader(f) if r['pollutant'] == 'pm25' and r['factor'] == 'traffic_intensity_per_h')
    STATIC['rho'] = f"{float(rho['spearman_r']):.2f}".replace('.', ',')
import json
META = json.load(open(os.path.join(ROOT, '..', 'dashboard-app', 'public', 'data', 'dashboard.json')))['meta']
STATIC['r2'] = f"{META['rf_r2']:.2f}".replace('.', ',')


class Dash:
    def __init__(self, name, height):
        self.name, self.h = name, height
        self.z = []
        self.id = 10
        self.sheets = []

    def _id(self):
        self.id += 1
        return self.id

    def u(self, x, y, w, h):  # pixels to 100000 units
        return (round(x / W * 100000), round(y / self.h * 100000), round(w / W * 100000), round(h / self.h * 100000))

    def style(self, bg='#ffffff', border='#e7e9ee', pad=10):
        s = (f"<zone-style><format attr='border-color' value='{border}' /><format attr='border-style' value='{'solid' if border else 'none'}' />"
             f"<format attr='border-width' value='{1 if border else 0}' /><format attr='margin' value='0' /><format attr='padding' value='{pad}' />")
        if bg:
            s += f"<format attr='background-color' value='{bg}' />"
        return s + '</zone-style>'

    def sheet(self, name, x, y, w, h, title=True, pad=10):
        X, Y, Wd, H = self.u(x, y, w, h)
        st = '' if title else " show-title='false'"
        self.z.append(f"<zone h='{H}' id='{self._id()}' name='{esc(name)}'{st} w='{Wd}' x='{X}' y='{Y}'>{self.style(pad=pad)}</zone>")
        self.sheets.append(name)

    def text(self, runs, x, y, w, h, bg=None, border=None, pad=4):
        X, Y, Wd, H = self.u(x, y, w, h)
        self.z.append(f"<zone h='{H}' id='{self._id()}' type-v2='text' w='{Wd}' x='{X}' y='{Y}'><formatted-text>{runs}</formatted-text>"
                      f"{self.style(bg=bg, border=border, pad=pad)}</zone>")

    def image(self, path, x, y, w, h):
        X, Y, Wd, H = self.u(x, y, w, h)
        self.z.append(f"<zone h='{H}' id='{self._id()}' is-scaled='1' param='{esc(path)}' type-v2='bitmap' w='{Wd}' x='{X}' y='{Y}' />")

    def ctrl(self, p, x, y, w, h=52):
        X, Y, Wd, H = self.u(x, y, w, h)
        self.z.append(f"<zone h='{H}' id='{self._id()}' mode='compact' param='{p}' type-v2='paramctrl' w='{Wd}' x='{X}' y='{Y}'>{self.style(bg=None, border=None, pad=2)}</zone>")

    def xml(self):
        root = f"<zone h='100000' id='4' type-v2='layout-basic' w='100000' x='0' y='0' />"
        return (f"<dashboard name='{esc(self.name)}'><style /><size maxheight='{self.h}' maxwidth='{W}' minheight='{self.h}' minwidth='{W}' sizing-mode='fixed' />"
                f"<datasources><datasource name='Parameters' /></datasources>"
                f"<datasource-dependencies datasource='Parameters'>{params_cols_xml()}</datasource-dependencies>"
                f"<zones>{root}{''.join(self.z)}</zones><simple-id uuid='{sid()}' /></dashboard>")


def run(t, size=11, bold=False, align=None, color='#000000'):
    b = " bold='true'" if bold else ''
    a = f" fontalignment='{align}'" if align is not None else ''
    return f"<run{b} fontcolor='{color}' fontname='{FONT}' fontsize='{size}'{a}>{esc(t)}</run>"


BR = "<run>Æ&#10;</run>"
M = 24      # page margin
G = 16      # gap


def header(d, title, ctrls):
    d.image('Images/logo_gelar_rasa.png', M, 16, 128, 44)
    d.text(run(title, 20, True), M + 150, 18, 700, 40)
    d.text(run('Gelar Rasa 2026, Dashboard Analysis', 9, align=2), W - M - 360, 26, 360, 24)
    y = 76
    allc = [(P_PULAU, 'Pulau'), (P_TIPE, 'Tipe Lokasi'), (P_MUSIM, 'Musim'), (P_TAHUN, 'Tahun')] + ctrls
    n = len(allc)
    cw = (W - 2 * M - (n - 1) * 12) / n
    for i, (p, _) in enumerate(allc):
        d.ctrl(p, M + i * (cw + 12), y, cw)
    return y + 52 + G


def kpis(d, y, items):
    """items: list of sheet names or ('static', label, value[, unit])"""
    kw = (W - 2 * M - 3 * G) / 4
    for i, it in enumerate(items):
        x = M + i * (kw + G)
        if isinstance(it, tuple):
            _, lbl, val, *unit = it
            r = run(lbl, 13, True, 1) + BR + run(val, 26, False, 1)
            if unit:
                r += run(' ' + unit[0], 11, False, 1)
            d.text(r, x, y, kw, 104, bg='#ffffff', border='#e7e9ee', pad=12)
        else:
            d.sheet(it, x, y, kw, 104)
    return y + 104 + G


def grid(d, y, rows):
    """rows: list of (height, [sheet names]) laid out side by side"""
    for h, names in rows:
        n = len(names)
        cw = (W - 2 * M - (n - 1) * G) / n
        for i, nm in enumerate(names):
            d.sheet(nm, M + i * (cw + G), y, cw, h)
        y += h + G
    return y


def footer(d, y):
    d.text(run('Econs UGM Coba-Coba, 2026.', 9, align=1), M, y, W - 2 * M, 28)
    return y + 40


def make(name, title, ctrls, kp, rows):
    est = 76 + 52 + G + (104 + G if kp else 0) + sum(h + G for h, _ in rows) + 40
    d = Dash(name, int(est))
    y = header(d, title, ctrls)
    if kp:
        y = kpis(d, y, kp)
    y = grid(d, y, rows)
    footer(d, y)
    DASH.append(d)
    return d


make('Ringkasan', 'Ringkasan', [], ['KPI Rata-Rata PM2.5', 'KPI Hari Tidak Sehat', 'KPI Hari Kabut Asap', 'KPI Kasus ISPA Balita'],
     [(480, ['Peta PM2.5']), (380, ['PM2.5 per Pulau', 'Kategori ISPU per Pulau'])])
make('Kondisi', 'Kondisi Udara', [(P_POL, 'Polutan'), (P_THBM, 'Tahun Baku Mutu')],
     ['KPI Melampaui Baku Mutu', 'KPI Pulau Paling Tercemar', 'KPI Stasiun Memburuk', 'KPI Rata-Rata Polutan'],
     [(640, ['Peringkat Stasiun', 'Kategori ISPU per Stasiun']), (420, ['Tren Bulanan']), (640, ['Baku Mutu dan IKU', 'Perbandingan 2024–2026'])])
make('Waktu Kritis', 'Waktu dan Wilayah Kritis', [(P_JAM, 'Polutan per Jam'), (P_PEKAN, 'Polutan Hari Kerja'), (P_POL, 'Polutan Pola Bulan')],
     [('static', 'Jam Puncak', '07.00', 'dan 18.00 WIB'), 'KPI Episode Kabut Asap', 'KPI PM2.5 Harian Tertinggi', ('static', 'Bulan Kritis', 'Agu–Okt')],
     [(400, ['Pola per Jam', 'Hari Kerja dan Akhir Pekan']), (620, ['Pola per Bulan', 'Episode Kabut Asap']), (620, ['Peringkat Wilayah Kritis', 'Karakteristik Kawasan'])])
make('Penyebab', 'Faktor Penyebab', [(P_LALIN, 'Polutan Lalu Lintas')],
     [('static', 'Faktor Utama', STATIC['faktor']), ('static', 'Akurasi Model (R²)', STATIC['r2']), ('static', 'Korelasi Lalu Lintas', STATIC['rho']), 'KPI Pengaruh Arah Angin'],
     [(420, ['Tingkat Kepentingan Faktor', 'Korelasi dengan Cuaca']), (560, ['Lalu Lintas dan Polutan', 'Pengaruh Arah Angin'])])
make('Kesehatan', 'Dampak Kesehatan', [(P_KASUS, 'Jenis Kasus'), (P_RS, 'Rumah Sakit')],
     ['KPI Kenaikan per 10', 'KPI Efek Kumulatif', 'KPI Saat Kabut Asap', 'KPI Kasus Akibat PM2.5'],
     [(520, ['Paparan dan Kasus Harian']), (400, ['Efek per Hari Jeda', 'Kasus Saat Kabut Asap']), (420, ['Risiko per Kategori ISPU', 'Kasus Akibat PM2.5']),
      (320, ['Balita dan Lansia'])])
make('Jaringan', 'Jaringan Pemantauan', [], ['KPI Stasiun Andal', 'KPI Celah Terlebar', 'KPI Prioritas Utama', 'KPI Provinsi Terpantau'],
     [(500, ['Peta Jaringan']), (620, ['Skor Prioritas Stasiun', 'Celah Jaringan']), (300, ['Cakupan per Pulau'])])

# measurement guide: text blocks (same content as the web guide)
GUIDE = [
    ('Satuan', [('µg/m³', 'Mikrogram polutan per meter kubik udara. Seluruh konsentrasi polutan (PM2.5, PM10, SO₂, CO, O₃, NO₂) dinyatakan dalam satuan ini.'),
                ('Hari-Stasiun', 'Satu stasiun pada satu hari. Contoh: 2 stasiun × 3 hari = 6 hari-stasiun.'),
                ('Kelengkapan Data (%)', 'Jumlah jam dengan data valid dibagi jumlah seluruh jam pada periode tersebut, dikali 100.'),
                ('Musim', 'Musim hujan November–April, musim kemarau Mei–Oktober, dan puncak kabut asap Agustus–Oktober.')]),
    ('Konversi Satuan', [('Rumus', 'µg/m³ = ppm × M × 1000 ÷ 24,45, pada suhu 25 °C dan tekanan 1 atm. Digunakan untuk stasiun yang mencatat dalam ppm (BJB-01, MDN-01, PSW-01).'),
                         ('M', 'Massa molar. Gas memakai massa molekulnya (ppm volume). PM tidak memiliki massa molekul, sehingga dibaca sebagai fraksi massa terhadap udara kering (M = 28,97).')]),
    ('Pengolahan Data', [('Per Jam', 'Data 15 menit dirata-ratakan menjadi data per jam apabila minimal 3 dari 4 nilai valid.'),
                         ('Harian', 'Nilai harian dihitung apabila minimal 18 dari 24 jam valid.'),
                         ('Rata-Rata Stasiun', 'Jumlah nilai jam valid ÷ jumlah jam valid pada filter aktif (minimal 10 hari).'),
                         ('CO dan O₃ 8 Jam', 'Rata-rata bergerak 8 jam (minimal 6 jam valid), lalu diambil nilai maksimum hariannya.'),
                         ('Tanpa Data Pengganti', 'Jam atau hari tanpa data dibiarkan kosong, tidak diisi dengan perkiraan, dan tidak diambil dari stasiun lain.')]),
    ('Indeks Kualitas Udara', [('ISPU Harian', 'Permen LHK 14/2020. Batas PM2.5 24 jam: Baik 0–15,5, Sedang 15,5–55,4, Tidak Sehat 55,4–150,4, Sangat Tidak Sehat 150,4–250,4, Berbahaya >250,4 µg/m³.'),
                               ('IKU', 'Permen LHK 27/2021, dari rata-rata tahunan NO₂ dan SO₂: Ieu = ((NO₂ ÷ 40) + (SO₂ ÷ 20)) ÷ 2, IKU = 100 − (50 ÷ 0,9) × (Ieu − 0,1), dibatasi 0–100.'),
                               ('Baku Mutu Tahunan', 'PP 22/2021: PM2.5 15, PM10 40, SO₂ 45, NO₂ 50, O₃ 35 µg/m³. Pedoman WHO 2021: PM2.5 5, PM10 15, NO₂ 10 µg/m³.'),
                               ('Baku Mutu 24 Jam', 'PM2.5 55, PM10 75, SO₂ 75, NO₂ 65 µg/m³.')]),
    ('Waktu dan Wilayah Kritis', [('Episode Kabut Asap', 'Minimal 3 hari berturut-turut dengan PM2.5 harian >55,4 µg/m³ dan >2× median PM2.5 musim hujan stasiun itu.'),
                                  ('Pola per Jam', 'Rata-rata tiap jam (WIB) pada hari tanpa kabut asap.'),
                                  ('Skor Wilayah Kritis', '0–100: rata-rata peringkat persentil dari PM2.5 rata-rata, % hari di atas baku mutu 24 jam, persentil ke-98 PM2.5 harian, dan jumlah hari ISPU Tidak Sehat ke atas.'),
                                  ('Tren 2024 ke 2026', 'Rata-rata 1 Januari–14 Oktober tiap tahun. Naik lebih dari 10% berarti memburuk, turun lebih dari 10% berarti membaik, selain itu stabil.')]),
    ('Faktor Penyebab', [('Spearman ρ', 'Kekuatan hubungan berbasis peringkat, bernilai −1 sampai 1. Antarstasiun memakai rata-rata musim hujan.'),
                         ('R² dan Kepentingan Faktor', 'R² = porsi variasi PM2.5 harian yang dijelaskan model Random Forest (data latih 2024–2025, data uji 2026). Kepentingan = penurunan R² ketika faktor itu diacak.'),
                         ('Arah Angin', 'PM2.5 saat angin bertiup dari sektor terkotor dibandingkan dengan sektor terbersih (8 arah). Dianggap berpengaruh bila selisihnya ≥10%.')]),
    ('Dampak Kesehatan', [('% per +10 µg/m³', 'Kenaikan kasus harian bila PM2.5 naik 10 µg/m³, dari model quasi-Poisson dengan kontrol tren waktu, suhu, kelembapan, hari, dan rumah sakit.'),
                          ('Hari Jeda', 'Jeda hari setelah paparan. Jeda 0 berarti hari yang sama. Jeda 0–7 dimodelkan bersama.'),
                          ('Risiko Relatif (RR)', 'Perbandingan jumlah kasus terhadap hari berkategori Baik (rata-rata PM2.5 3 hari).'),
                          ('Kasus Akibat PM2.5', 'Jumlah kasus × (1 − 1 ÷ RR kategori hari itu).'),
                          ('Uji Beda (z)', 'Membandingkan balita dengan lansia. Nilai |z| ≥1,96 berarti berbeda bermakna (taraf 5%).')]),
    ('Jaringan Pemantauan', [('Celah', 'Jarak garis lurus (km) antarstasiun bertetangga pada jaringan terpendek dalam satu pulau. Celah ≥300 km ditandai merah.'),
                             ('Keandalan Alat', 'Kritis: rusak atau kelengkapan <50%. Buruk: kelengkapan <75% atau sensor macet. Perlu standardisasi: beroperasi tidak menentu atau perlu konversi satuan. Selain itu: Baik.'),
                             ('Skor Prioritas', 'Rata-rata berbobot: polusi 25%, kabut asap 20%, beban kesehatan 20%, defisit data 20%, keterisolasian 15%. Komponen kosong tidak diisi, bobotnya dibagi ulang.')]),
]
heights = [24 + 22 * len(items) * 2 + 20 for _, items in GUIDE]
gh = 76 + sum(h + G for h in heights) + 40
d = Dash('Petunjuk Pengukuran', int(gh))
d.image('Images/logo_gelar_rasa.png', M, 16, 128, 44)
d.text(run('Petunjuk Pengukuran', 20, True), M + 150, 18, 700, 40)
y = 76
for (t, items), h in zip(GUIDE, heights):
    r = run(t, 14, True) + BR
    for k, v in items:
        r += BR + run(k, 11, True) + BR + run(v, 11)
    d.text(r, M, y, W - 2 * M, h, bg='#ffffff', border='#e7e9ee', pad=14)
    y += h + G
footer(d, y)
DASH.append(d)

# ───────────────────────── windows + workbook ─────────────────────────
used = {s for dd in DASH for s in dd.sheets}
win = []
for dd in DASH:
    vps = ''.join(f"<viewpoint name='{esc(s)}'><zoom type='entire-view' /></viewpoint>" for s in dict.fromkeys(dd.sheets))
    win.append(f"<window class='dashboard' maximized='{'true' if dd.name == 'Ringkasan' else 'false'}' name='{esc(dd.name)}'><viewpoints>{vps}</viewpoints>"
               f"<active id='-1' /><simple-id uuid='{sid()}' /></window>")
for s in SHEET_NAMES:
    hid = " hidden='true'" if s in used else ''
    win.append(f"<window class='worksheet'{hid} name='{esc(s)}'><cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' />"
               f"<card type='marks' /></strip></edge><edge name='top'><strip size='2147483647'><card type='columns' /></strip>"
               f"<strip size='2147483647'><card type='rows' /></strip><strip size='31'><card type='title' /></strip></edge></cards>"
               f"<viewpoint><zoom type='entire-view' /></viewpoint><simple-id uuid='{sid()}' /></window>")

wb = ("<?xml version='1.0' encoding='utf-8' ?>\n"
      "<workbook locale='id_ID' source-build='2026.2.0 (20262.25.0912.0000)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>"
      "<document-format-change-manifest><SheetIdentifierTracking /><SortTagCleanup /><WindowsPersistSimpleIdentifiers /></document-format-change-manifest>"
      "<preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>"
      "<datasources>" + params_xml() + ''.join(d_.xml() for d_ in ALL_DS) + "</datasources>"
      "<worksheets>" + ''.join(SHEETS) + "</worksheets>"
      "<dashboards>" + ''.join(dd.xml() for dd in DASH) + "</dashboards>"
      "<windows source-height='30'>" + ''.join(win) + "</windows>"
      "</workbook>")

EXT = os.path.join(DATA, 'Extracts')
os.makedirs(EXT, exist_ok=True)
for d_ in ALL_DS:
    d_.make_hyper(EXT)
print('extracts:', ', '.join(f'{d_.hyper}' for d_ in ALL_DS))
twb = os.path.join(ROOT, NAME + '.twb')
open(twb, 'w', encoding='utf-8').write(wb)
# packaged workbook: workbook + data + logo in one file
img = os.path.join(ROOT, 'Images')
os.makedirs(img, exist_ok=True)
shutil.copy(os.path.join(ROOT, '..', 'dashboard-app', 'public', 'logo_gelar_rasa.png'), os.path.join(img, 'logo_gelar_rasa.png'))
twbx = os.path.join(ROOT, NAME + '.twbx')
with zipfile.ZipFile(twbx, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(twb, NAME + '.twb')
    for d_ in ALL_DS:
        z.write(os.path.join(EXT, d_.hyper), 'Data/Extracts/' + d_.hyper)
    z.write(os.path.join(img, 'logo_gelar_rasa.png'), 'Images/logo_gelar_rasa.png')
print(f'{len(SHEET_NAMES)} worksheets, {len(DASH)} dashboards, {len(ALL_DS)} data sources')
print(twb)
print(twbx)
