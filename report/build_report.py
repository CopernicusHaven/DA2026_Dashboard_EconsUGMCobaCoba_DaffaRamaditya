"""Laporan DA2026 (PDF) mengikuti template panitia: A4, Times New Roman 12, spasi 1,15, rata kanan-kiri,
latar halaman dari template resmi. Ubah identitas tim di bagian KONFIGURASI lalu jalankan ulang:
    python3 build_report.py
"""
import os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Image, Table,
                                TableStyle, KeepTogether, NextPageTemplate, CondPageBreak, Flowable)
from reportlab.platypus.tableofcontents import TableOfContents
from PIL import Image as PILImage

# ───────────── KONFIGURASI (isi sebelum dikumpulkan) ─────────────
TEAM = 'Econs UGM Coba-Coba'
LEADER = '[Nama Lengkap Ketua Tim]'
MEMBERS = ['[Nama Lengkap Anggota 1]', '[Nama Lengkap Anggota 2]']
INSTITUTION = '[NAMA INSTANSI PESERTA]'
DASHBOARD_URL = '[tautan dashboard]'
GITHUB_URL = '[tautan repository GitHub (opsional)]'
LEADER_FILE = 'NamaKetua'          # dipakai pada nama berkas
TITLE_LINES = ['MEMBACA UDARA INDONESIA MELALUI DATA:', 'KUALITAS UDARA DAN DAMPAKNYA TERHADAP', 'KESEHATAN DI LIMA PULAU, 2024–2026']
# ──────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(ROOT, 'figures')
TPL = os.path.join(ROOT, 'template')
OUT = os.path.join(ROOT, f"DA2026_Laporan_{re.sub(r'[^A-Za-z0-9]', '', TEAM)}_{LEADER_FILE}.pdf")

FD = '/System/Library/Fonts/Supplemental/'
pdfmetrics.registerFont(TTFont('TNR', FD + 'Times New Roman.ttf'))
pdfmetrics.registerFont(TTFont('TNR-B', FD + 'Times New Roman Bold.ttf'))
pdfmetrics.registerFont(TTFont('TNR-I', FD + 'Times New Roman Italic.ttf'))
pdfmetrics.registerFont(TTFont('TNR-BI', FD + 'Times New Roman Bold Italic.ttf'))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily('TNR', normal='TNR', bold='TNR-B', italic='TNR-I', boldItalic='TNR-BI')

PW, PH = A4
ML, MR, MT, MB = 85, 83, 112, 96          # margins measured from the template (pt)
TW = PW - ML - MR                          # text width

S_BODY = ParagraphStyle('body', fontName='TNR', fontSize=12, leading=13.8, alignment=TA_JUSTIFY, spaceAfter=6)
S_BULLET = ParagraphStyle('bullet', parent=S_BODY, leftIndent=18, bulletIndent=4, spaceAfter=3)
S_CH = ParagraphStyle('ch', fontName='TNR-B', fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=18)
S_H2 = ParagraphStyle('h2', fontName='TNR-B', fontSize=12, leading=14, spaceBefore=10, spaceAfter=6, leftIndent=28, firstLineIndent=-28)
S_H3 = ParagraphStyle('h3', fontName='TNR-B', fontSize=12, leading=14, spaceBefore=8, spaceAfter=5)
S_CAP = ParagraphStyle('cap', fontName='TNR', fontSize=11, leading=12.6, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
S_TH = ParagraphStyle('th', fontName='TNR-B', fontSize=10, leading=11.5, alignment=TA_CENTER)
S_TD = ParagraphStyle('td', fontName='TNR', fontSize=10, leading=11.5)
S_TDC = ParagraphStyle('tdc', parent=S_TD, alignment=TA_CENTER)
S_TDR = ParagraphStyle('tdr', parent=S_TD, alignment=2)
S_TOC0 = ParagraphStyle('toc0', fontName='TNR-B', fontSize=12, leading=16)
S_TOC1 = ParagraphStyle('toc1', fontName='TNR', fontSize=12, leading=15, leftIndent=24)
S_TOC2 = ParagraphStyle('toc2', fontName='TNR', fontSize=12, leading=15, leftIndent=48)
S_LIST = ParagraphStyle('lst', fontName='TNR', fontSize=12, leading=15, leftIndent=72, firstLineIndent=-72)

# ───────────── page furniture ─────────────
STATE = {'body_start': None, 'cur': None}   # body_start = page of BAB I found in the previous pass


def roman(n):
    vals = [(10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')]
    s = ''
    for v, r in vals:
        while n >= v:
            s += r; n -= v
    return s


def page_label(page):
    if STATE['body_start'] and page >= STATE['body_start']:
        return str(page - STATE['body_start'] + 1)
    return roman(page)          # cover = i (not printed)


def draw_bg(canv, doc):
    canv.saveState()
    canv.drawImage(os.path.join(TPL, 'bg_halaman.jpg'), 0, 0, PW, PH)
    canv.setFont('TNR', 11)
    canv.drawRightString(PW - MR, 42, page_label(doc.page))
    canv.restoreState()


def draw_cover(canv, doc):
    canv.saveState()
    canv.drawImage(os.path.join(TPL, 'bg_sampul.png'), 0, 0, PW, PH)
    y = PH - 115 - 11
    canv.setFont('TNR-B', 14)
    canv.drawCentredString(PW / 2, y, 'LAPORAN ANALISIS')
    for i, line in enumerate(TITLE_LINES):
        t = ('“' if i == 0 else '') + line + ('”' if i == len(TITLE_LINES) - 1 else '')
        canv.drawCentredString(PW / 2, y - 19 * (i + 1), t)
    logo = os.path.join(ROOT, 'logo_instansi.png')
    lp = logo if os.path.exists(logo) else os.path.join(TPL, 'logo_placeholder.png')
    iw, ih = PILImage.open(lp).size
    bw, bh = 216, 189
    s = min(bw / iw, bh / ih)
    bx, by = 190, PH - 203 - bh                       # logo box position in the template (pt)
    canv.drawImage(lp, bx + (bw - iw * s) / 2, by + (bh - ih * s) / 2, iw * s, ih * s, mask='auto')
    y = PH - 427 - 11
    canv.drawCentredString(PW / 2, y, 'Disusun Oleh:')
    canv.drawCentredString(PW / 2, y - 18.5, TEAM)
    canv.setFont('TNR', 14)
    for i, n in enumerate([LEADER] + MEMBERS):
        canv.drawString(211, y - 37 - 18.5 * i, f'{i + 1}.  {n}')
    canv.setFont('TNR-B', 14)
    y = PH - 583 - 11
    for i, t in enumerate([INSTITUTION, 'DASHBOARD ANALYSIS', 'GELAR RASA 2026', '2026']):
        canv.drawCentredString(PW / 2, y - 18.5 * i, t)
    canv.restoreState()


class Doc(BaseDocTemplate):
    def __init__(self, fn, **kw):
        super().__init__(fn, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                         title='Laporan Analisis DA Gelar Rasa 2026', author=TEAM, **kw)
        fr = Frame(ML, MB, TW, PH - MT - MB, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate('cover', [Frame(ML, MB, TW, PH - MT - MB)], onPage=draw_cover),
                               PageTemplate('front', [fr], onPage=draw_bg),
                               PageTemplate('body', [fr], onPage=draw_bg)])

    def beforeDocument(self):
        TOCREC.clear()
        if STATE['cur']:
            STATE['body_start'] = STATE['cur']
        STATE['cur'] = None

    def afterFlowable(self, f):
        if isinstance(f, Marker) and f.kind == 'body' and STATE['cur'] is None:
            STATE['cur'] = self.page
        if isinstance(f, Paragraph) and hasattr(f, '_toc'):
            lvl, text = f._toc
            key = 'k%d' % id(f)
            self.canv.bookmarkPage(key)
            self.notify('TOCEntry', (lvl, text, self.page, key))
            TOCREC.append(('toc', lvl, text, page_label(self.page)))
        if hasattr(f, '_lst'):
            kind, text = f._lst
            self.notify(kind, (0, text, self.page, None))
            TOCREC.append((kind, 0, text, page_label(self.page)))


class Marker(Flowable):
    def __init__(self, kind):
        super().__init__(); self.kind = kind
    def wrap(self, *a):
        return 0, 0
    def draw(self):
        pass


class ListOf(TableOfContents):
    """List of tables / figures: same mechanics as the table of contents, own notification kind."""
    def __init__(self, kind):
        super().__init__(); self.kind = kind
        self.levelStyles = [S_LIST]
        self.dotsMinLevel = 0
        self.formatter = page_label

    def notify(self, kind, stuff):
        if kind == self.kind:
            self.addEntry(*stuff)


# ───────────── content helpers ─────────────
story = []
BLOCKS = []          # same content as plain data, for the Word version (build_docx.py)
TOCREC = []          # (kind, level, text, page label) from the final layout pass
CH = {'n': 0}
FIGN = {'n': 0}
TABN = {'n': 0}


def P(t, style=S_BODY):
    story.append(Paragraph(t, style))
    BLOCKS.append({'t': 'p', 'text': t})


def BL(items):
    for t in items:
        story.append(Paragraph(t, S_BULLET, bulletText='•'))
    story.append(Spacer(1, 3))
    BLOCKS.append({'t': 'bullets', 'items': items})


def NL(items, start=1):
    for i, t in enumerate(items):
        story.append(Paragraph(t, S_BULLET, bulletText=f'{start + i}.'))
    story.append(Spacer(1, 3))
    BLOCKS.append({'t': 'numbers', 'items': items, 'start': start})


def CHAPTER(num, title):
    story.append(NextPageTemplate('body'))
    story.append(PageBreak())
    if num == 'I':
        story.append(Marker('body'))
    CH['n'] = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}[num]
    FIGN['n'] = 0; TABN['n'] = 0
    p = Paragraph(f'BAB {num}<br/>{title}', S_CH)
    p._toc = (0, f'BAB {num} {title}')
    story.append(p)
    BLOCKS.append({'t': 'chapter', 'num': num, 'title': title})


def H2(num, title):
    p = Paragraph(f'{num}<font color="white">_</font>{title}'.replace('<font color="white">_</font>', '&nbsp;&nbsp;&nbsp;&nbsp;'), S_H2)
    p._toc = (1, f'{num}&nbsp;&nbsp;{title}')
    story.append(CondPageBreak(60))
    story.append(p)
    BLOCKS.append({'t': 'h2', 'num': num, 'title': title})


def H3(num, title):
    p = Paragraph(f'{num}&nbsp;&nbsp;{title}', S_H3)
    p._toc = (2, f'{num}&nbsp;&nbsp;{title}')
    story.append(CondPageBreak(60))
    story.append(p)


def SECTION(title):           # unnumbered front/back matter heading
    story.append(PageBreak())
    p = Paragraph(title, S_CH)
    p._toc = (0, title)
    story.append(p)
    BLOCKS.append({'t': 'section', 'title': title})


def compact(path, maxw=1700, q=82):
    """JPEG copy of a figure (smaller PDF), cached next to the figures."""
    d = os.path.join(FIG, '_jpg'); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, os.path.splitext(os.path.basename(path))[0] + '.jpg')
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(path):
        im = PILImage.open(path).convert('RGB')
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), PILImage.LANCZOS)
        im.save(out, 'JPEG', quality=q, optimize=True)
    return out


def img(path, w=None, maxh=None):
    path = compact(path)
    iw, ih = PILImage.open(path).size
    w = w or TW
    h = w * ih / iw
    if maxh and h > maxh:
        w, h = w * maxh / h, maxh
    return Image(path, width=w, height=h)


def FIGURE(paths, caption, w=None, maxh=330, lead=None):
    FIGN['n'] += 1
    num = f'{CH["n"]}.{FIGN["n"]}'
    if isinstance(paths, str):
        body = img(os.path.join(FIG, paths), w or TW * 0.94, maxh)
    else:
        cw = (TW - 10) / len(paths)
        ims = [img(os.path.join(FIG, p), cw, maxh) for p in paths]
        body = Table([ims], colWidths=[cw + 5] * len(paths))
        body.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                  ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    cap = Paragraph(f'<b>Gambar {num}</b> {caption}', S_CAP)
    cap._lst = ('FigEntry', f'Gambar {num}&nbsp;&nbsp;{caption}')
    story.append(KeepTogether((lead or []) + [body, cap]))
    BLOCKS.append({'t': 'figure', 'num': num, 'caption': caption, 'paths': [paths] if isinstance(paths, str) else paths,
                   'w': (w / TW) if w else (0.94 if isinstance(paths, str) else 1.0), 'maxh': maxh})
    return f'Gambar {num}'


def TABLE(caption, head, rows, widths, align=None):
    TABN['n'] += 1
    num = f'{CH["n"]}.{TABN["n"]}'
    cap = Paragraph(f'<b>Tabel {num}</b> {caption}', ParagraphStyle('tc', parent=S_CAP, spaceBefore=6, spaceAfter=4))
    cap._lst = ('TabEntry', f'Tabel {num}&nbsp;&nbsp;{caption}')
    align = align or ['L'] * len(head)
    st = {'L': S_TD, 'C': S_TDC, 'R': S_TDR}
    data = [[Paragraph(h, S_TH) for h in head]] + [[Paragraph(str(c), st[a]) for c, a in zip(r, align)] for r in rows]
    t = Table(data, colWidths=[w * TW for w in widths], repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#8a8f99')),
                           ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f3e3')),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
    story.append(KeepTogether([cap, t]))
    story.append(Spacer(1, 8))
    BLOCKS.append({'t': 'table', 'num': num, 'caption': caption, 'head': head, 'rows': [[str(c) for c in r] for r in rows], 'widths': widths, 'align': align})
    return f'Tabel {num}'


def VIS(num, title, fig, caption, analisis, interpretasi, maxh=190):
    h = Paragraph(f'3.3.{num}&nbsp;&nbsp;Visualisasi {num}: {title}', S_H3)
    h._toc = (2, f'3.3.{num}&nbsp;&nbsp;Visualisasi {num}: {title}')
    BLOCKS.append({'t': 'h3', 'num': f'3.3.{num}', 'title': f'Visualisasi {num}: {title}'})
    FIGURE(fig, caption, maxh=min(maxh, 215), lead=[h])
    P(f'<b>Analisis.</b> {analisis}')
    P(f'<b>Interpretasi.</b> {interpretasi}')


u = lambda s: s.replace('NO2', 'NO<sub>2</sub>').replace('SO2', 'SO<sub>2</sub>').replace('O3', 'O<sub>3</sub>')

# ═════════════════════════ COVER + FRONT MATTER ═════════════════════════
story.append(NextPageTemplate('front'))
story.append(Spacer(1, 1))
story.append(PageBreak())
story.append(Paragraph('DAFTAR ISI', S_CH))
toc = TableOfContents()
toc.levelStyles = [S_TOC0, S_TOC1, S_TOC2]
toc.dotsMinLevel = 0
toc.formatter = page_label
story.append(toc)
story.append(PageBreak())
story.append(Paragraph('DAFTAR TABEL', S_CH))
story.append(ListOf('TabEntry'))
story.append(PageBreak())
story.append(Paragraph('DAFTAR GAMBAR', S_CH))
story.append(ListOf('FigEntry'))

# ═════════════════════════ BAB I ═════════════════════════
CHAPTER('I', 'PENGANTAR PROYEK')
H2('1.1', 'Konteks Permasalahan')
P('Pencemaran udara, terutama partikel halus PM2.5, adalah salah satu risiko lingkungan terbesar bagi kesehatan. '
  'Partikel berdiameter kurang dari 2,5 µm dapat masuk jauh ke saluran pernapasan, sehingga Organisasi Kesehatan Dunia '
  'menetapkan pedoman rata-rata tahunan PM2.5 hanya 5 µg/m³ (World Health Organization, 2021). Indonesia menetapkan baku '
  'mutu tahunan 15 µg/m³ dan baku mutu 24 jam 55 µg/m³ melalui PP Nomor 22 Tahun 2021, serta mengomunikasikan mutu udara '
  'harian kepada masyarakat melalui Indeks Standar Pencemar Udara (ISPU) sesuai Permen LHK Nomor 14 Tahun 2020.')
P('Proyek ini menganalisis dataset sintetis dari panitia Gelar Rasa 2026 yang mencakup rekaman polutan dan cuaca per jam '
  'dari 27 stasiun pemantau kualitas udara (AQMS) di lima pulau besar, kasus kesehatan harian dari 27 rumah sakit rujukan, '
  'serta tabel master dan metadata, untuk periode 1 Januari 2024 sampai 14 Oktober 2026. Data tersebut menunjukkan bahwa '
  'masalahnya nyata. Rata-rata PM2.5 dari 26 stasiun yang datanya layak adalah <b>40,9 µg/m³</b>, hampir tiga kali baku mutu '
  'tahunan, dan 23 stasiun melampaui baku mutu tersebut. Sebanyak <b>17,6%</b> hari-stasiun berkategori ISPU Tidak Sehat '
  'atau lebih buruk, dan tercatat <b>2.322</b> hari-stasiun kabut asap. Pada periode yang sama, 27 rumah sakit mencatat '
  '<b>186.167</b> rawat inap ISPA pada balita.')
P('Masalah ini tidak seragam. Sebagian wilayah tercemar sepanjang tahun karena aktivitas perkotaan dan industri, sedangkan '
  'wilayah lain tercemar secara musiman karena kebakaran hutan dan lahan gambut. Karena itu, pengambil keputusan memerlukan '
  'alat yang dapat menunjukkan <i>kapan</i>, <i>di mana</i>, <i>mengapa</i>, dan <i>seberapa besar dampaknya</i> secara '
  'bersamaan, sesuai tema "From Roots to Clarity: Revealing Meaningful Insight Through Data".')
H2('1.2', 'Pokok Permasalahan')
P('Pertanyaan analisis yang dijawab melalui dashboard adalah sebagai berikut.')
NL(['Bagaimana kondisi kualitas udara antarstasiun dan antarpulau dibandingkan dengan baku mutu nasional dan pedoman WHO, '
    'serta bagaimana kecenderungannya selama 2024–2026?',
    'Kapan dan di mana pencemaran paling kritis bila ditinjau menurut jam, hari kerja dan akhir pekan, musim, dan episode '
    'kabut asap, serta bagaimana perbedaannya antara kawasan perkotaan, industri, dan latar bersih?',
    'Faktor apa yang paling memengaruhi variasi konsentrasi polutan: suhu, kelembapan, kecepatan dan arah angin, intensitas '
    'lalu lintas, jarak ke jalan raya, atau tipe lokasi?',
    'Seberapa besar kenaikan PM2.5 berhubungan dengan kasus ISPA, asma, PPOK, kardiovaskular, dan kematian, berapa lama efek '
    'jedanya, dan kelompok mana yang lebih rentan, balita atau lansia?',
    'Apakah jaringan pemantauan saat ini memadai, dan wilayah mana yang perlu diprioritaskan untuk penambahan titik pantau?'])
H2('1.3', 'Sasaran Proyek')
P('Setiap pertanyaan dijawab oleh satu halaman dashboard dengan sasaran berikut.')
NL(['<b>Kondisi Udara:</b> memeringkat stasiun dan pulau terhadap baku mutu dan pedoman WHO, menghitung IKU, dan '
    'menandai stasiun yang memburuk.',
    '<b>Waktu Kritis:</b> menemukan jam puncak, bulan kritis, episode kabut asap, dan wilayah dengan skor kritis tertinggi.',
    '<b>Penyebab:</b> mengukur kontribusi setiap faktor dengan model Random Forest dan korelasi, lalu menentukan faktor utama.',
    '<b>Kesehatan:</b> mengestimasi kenaikan kasus per 10 µg/m³ PM2.5, efek jeda 0–7 hari, risiko per kategori ISPU, dan '
    'perbedaan kerentanan balita dan lansia.',
    '<b>Jaringan:</b> menilai keandalan alat, celah antarstasiun, dan skor prioritas penambahan titik pantau.'])
P('Seluruhnya disajikan dalam satu dashboard web interaktif yang dapat dibuka tanpa login, dengan filter yang berlaku di '
  'semua halaman dan halaman Petunjuk Pengukuran yang menjelaskan setiap satuan dan definisi.')

# ═════════════════════════ BAB II ═════════════════════════
CHAPTER('II', 'RANCANGAN PELAKSANAAN')
H2('2.1', 'Karakteristik Dataset')
P('Dataset terdiri atas 33 berkas yang saling terhubung melalui kode stasiun, sensor, dan rumah sakit '
  '(<i>station</i>, <i>location_id</i>, <i>sensor_id</i>, <i>hospital_id</i>). Ringkasannya disajikan pada Tabel 2.1.')
TABLE('Karakteristik dataset', ['Kelompok', 'Berkas', 'Variabel dan tipe data', 'Ukuran'], [
    ['Data udara', '27 berkas [KODE]_[Lokasi]_AQMS.csv',
     u('PM2.5, PM10, SO2, CO, O3, NO2 (numerik, µg/m³ atau ppm), suhu, kelembapan, kecepatan dan arah angin (numerik), qc_flag (kategorik), timestamp (waktu)'),
     '24.432 jam per stasiun, 655.808 jam terekam'],
    ['Data kesehatan', 'HLT-01_health_outcomes_daily.csv',
     'ISPA balita, ISPA lansia, darurat asma, PPOK, pernapasan umum, kardiovaskular, kematian (cacah), suhu, titik embun, kelembapan',
     '27.491 baris (27 RS × ±1.018 hari)'],
    ['Tabel master', 'sites.csv, sensors.csv, hospitals.csv',
     'Lokasi, tipe lokasi, intensitas lalu lintas, jarak ke jalan raya, alat ukur, satuan logger, kapasitas tempat tidur', '27 baris per tabel'],
    ['Metadata', 'metadata_sensors.csv, metadata_dates.csv', 'Spesifikasi instrumen, periode dan resolusi rekaman', '16 dan 27 baris'],
], [0.15, 0.25, 0.42, 0.18])
P('Kondisi awal data menunjukkan beberapa hal yang memengaruhi analisis. Tiga stasiun (BJB-01, MDN-01, PSW-01) mengekspor '
  'polutan dalam ppm, bukan µg/m³. Stasiun JMB-02 berstatus rusak dengan hanya 0,5% baris valid. Sebanyak 17 stasiun '
  'mengalami pergeseran jam (<i>clock drift</i>), PLB-01 mencampur resolusi 15 menit dan 1 jam, dan MDN-01 kehilangan 3.632 '
  'jam. Distribusi PM2.5 harian sangat menceng ke kanan (median 31,0 µg/m³, rata-rata 39,9 µg/m³, maksimum 1.127,6 µg/m³), '
  'sehingga rata-rata stasiun dihitung dari data per jam dan kategori ISPU dipakai untuk membaca hari ekstrem.')
H2('2.2', 'Perangkat yang Digunakan')
P('Pengolahan dan analisis data memakai <b>Python 3.13</b> dengan pandas dan NumPy (pengolahan), SciPy (uji statistik), '
  'statsmodels (regresi quasi-Poisson dan model jeda), scikit-learn (Random Forest dan <i>permutation importance</i>), serta '
  'matplotlib (grafik eksplorasi). Python dipilih karena seluruh proses dapat direproduksi dari data mentah, setiap langkah '
  'pembersihan tercatat otomatis, dan model deret waktu kesehatan-lingkungan tidak tersedia di alat spreadsheet.')
P('Dashboard dibangun sebagai aplikasi web dengan <b>React 19</b> (antarmuka), <b>Vite 8</b> (build), <b>ECharts 6</b> '
  '(grafik interaktif), <b>Leaflet 1.9</b> dengan peta dasar Google Maps dan cadangan Esri (peta), serta Framer Motion '
  '(transisi). Kombinasi ini dipilih karena memberi kendali penuh atas tata letak, interaksi, dan alur cerita. Hasil build '
  'berupa situs statis sehingga dapat dibuka juri tanpa login, dan dashboard membaca berkas hasil analisis yang sama dengan '
  'laporan sehingga angka di keduanya identik.')
H2('2.3', 'Preprocessing Data')
P('Tiga prinsip dipegang selama pembersihan: berkas asli tidak pernah diubah, tidak ada data yang ditambahkan (jam kosong '
  'tidak diimputasi dan tidak dipinjam dari stasiun lain), dan setiap tindakan dicatat beserta jumlah nilai yang terdampak. '
  'Masalah utama dan penanganannya dirangkum pada Tabel 2.2.')
TABLE('Masalah kualitas data dan penanganannya', ['Masalah', 'Stasiun', 'Skala', 'Penanganan dan dampak'], [
    ['Satuan ppm', 'BJB-01, MDN-01, PSW-01', '3 stasiun × 6 polutan', 'Dikonversi ke µg/m³ dengan satu rumus (Tabel 2.3)'],
    ['Pergeseran jam (<i>clock drift</i>)', '17 stasiun', '423.529 baris', 'Dibulatkan ke jam terdekat agar setiap jam terhitung sekali'],
    ['Resolusi campuran 15 menit', 'PLB-01', '15.933 baris', 'Dirata-rata per jam bila minimal 3 dari 4 nilai valid'],
    ['Sensor rusak, kode galat, tahun 1970', 'JMB-02', '24.432 baris', 'Dikeluarkan dari analisis, RS-XXX-27 tidak dimodelkan'],
    ['Nilai sentinel (−9999, 999, dan lainnya)', 'JMB-02, SM2-01, MER-01', '80.385 nilai', 'Dijadikan kosong'],
    ['Sensor macet (nilai identik berjam-jam)', 'BJB-01', '7.329 jam', 'Nilai identik ≥6 jam berturut-turut dijadikan kosong'],
    ['qc_flag selain VALID', 'Semua', '171.439 nilai', 'Polutan hanya memakai VALID'],
    ['Di luar batas fisik dan lonjakan tunggal', 'MER-01, JMB-02, KTG-01/02', '±60 ribu nilai', 'Dijadikan kosong'],
    ['Tanggal di luar periode, resp &lt; balita + lansia', 'HLT-01', '5 baris, 92 baris', 'Dibuang, dan ditandai tanpa diubah'],
], [0.27, 0.2, 0.16, 0.37])
P('Konversi satuan ditentukan peserta sesuai jawaban panitia pada sesi tanya jawab. Seluruh nilai ppm dikonversi pada 25 °C '
  'dan 1 atm dengan rumus µg/m³ = ppm × M × 1000 ÷ 24,45 (Seinfeld &amp; Pandis, 2016). Gas memakai massa molekulnya, '
  'sedangkan PM yang tidak memiliki massa molekul dibaca sebagai fraksi massa terhadap udara kering (M = 28,97 g/mol).')
TABLE('Faktor konversi ppm ke µg/m³', ['Parameter', 'Basis ppm', 'M (g/mol)', 'Faktor per ppm'], [
    [u('SO2'), 'Volume', '64,066', '2.620,3'], ['CO', 'Volume', '28,010', '1.145,6'], [u('O3'), 'Volume', '47,998', '1.963,1'],
    [u('NO2'), 'Volume', '46,006', '1.881,6'], ['PM2.5, PM10', 'Massa terhadap udara', '28,970', '1.184,9'],
], [0.22, 0.34, 0.2, 0.24], ['L', 'L', 'R', 'R'])
P(u('Setelah dikonversi, gas di PSW-01 setara dengan stasiun berpola serupa (SO2 7,5 dibanding 7,0 µg/m³, NO2 20,7 dibanding '
  '19,8 µg/m³), sedangkan konversi sederhana ×1000 menghasilkan nilai 1,8–2,5 kali lebih rendah. Hasil akhirnya adalah '
  '655.808 jam terekam, dengan PM2.5 valid 91,7% di luar JMB-02. Turunan yang dibentuk meliputi rata-rata harian (minimal 18 '
  'dari 24 jam valid), ISPU harian, penanda baku mutu 24 jam, episode kabut asap (minimal 3 hari berturut-turut dengan PM2.5 '
  'di atas 55,4 µg/m³ dan dua kali median musim hujan stasiun itu), PM2.5 berjeda 0–7 hari untuk tiap rumah sakit, serta IKU '
  'tahunan dari NO2 dan SO2 (Permen LHK Nomor 27 Tahun 2021).'))
H2('2.4', 'Prosedur Perancangan Visualisasi')
P('Dashboard disusun mengikuti alur dari gambaran besar ke akar masalah, ke dampak, lalu ke solusi. Halaman Ringkasan memuat '
  'kartu indikator dan peta, lalu setiap pertanyaan analisis mendapat satu halaman: Kondisi, Waktu Kritis, Penyebab, '
  'Kesehatan, dan Jaringan. Halaman Petunjuk Pengukuran memuat seluruh satuan, rumus, dan definisi. Jenis grafik dipilih '
  'sesuai kebutuhan analisis seperti pada Tabel 2.4.')
TABLE('Pemilihan jenis grafik', ['Kebutuhan analisis', 'Jenis grafik', 'Alasan'], [
    ['Perbandingan antarstasiun dan pulau', 'Batang horizontal berurut', 'Mudah membandingkan panjang dan membaca nama stasiun'],
    ['Komposisi kategori ISPU', 'Batang 100% bertumpuk', 'Menunjukkan porsi hari tiap kategori dalam satu batang'],
    ['Sebaran wilayah', 'Peta titik', 'Warna menunjukkan kategori, ukuran menunjukkan besaran'],
    ['Tren dan pola waktu', 'Garis bulanan dan per jam', 'Menampilkan perubahan berurutan dan jam puncak'],
    ['Pola bulanan per stasiun', '<i>Heatmap</i> stasiun × bulan', 'Musim kabut terlihat sebagai blok warna'],
    ['Episode kabut asap', 'Linimasa (<i>Gantt</i>)', 'Menunjukkan awal, lama, dan stasiun setiap episode'],
    ['Hubungan antarvariabel', 'Diagram pencar dan batang kepentingan', 'Menunjukkan arah dan kekuatan hubungan'],
    ['Efek kesehatan', 'Batang per jeda dan per kategori', 'Membandingkan besar efek antarhari dan antarkategori'],
], [0.31, 0.29, 0.4])
P('Tata letak dibuat konsisten di semua halaman. Bilah navigasi melayang di bagian atas, baris filter berada di bawahnya, '
  'diikuti empat kartu indikator berisi judul dan angka, lalu satu kartu untuk setiap grafik, tabel, atau peta. Panel daftar '
  'stasiun berada di sisi kiri pada layar lebar dan pindah ke bawah pada layar kecil. Warna mengikuti tiga aturan: palet ISPU '
  'yang sama di semua grafik (biru Baik, abu-abu Sedang, merah bertingkat Tidak Sehat sampai Berbahaya), satu warna tetap '
  'untuk setiap pulau dan setiap tipe lokasi, serta teks hitam pada mode terang dan putih pada mode gelap dengan satu jenis '
  'huruf, Helvetica. Garis baku mutu dan pedoman WHO ditampilkan sebagai garis putus-putus dengan keterangan di bawah grafik.')
P('Fitur interaktif yang disiapkan adalah filter Pulau, Tipe Lokasi, Musim, dan Tahun (termasuk rentang tanggal) yang '
  'berlaku di semua halaman, panel stasiun untuk memeringkat dan membandingkan hingga enam stasiun, panel detail stasiun yang '
  'terbuka dari peta, grafik, atau tabel, pemilih polutan, jenis kasus, rumah sakit, dan tahun pada grafik tertentu, '
  'tooltip, zoom peta, tabel yang dapat diurutkan, mode terang dan gelap, serta tampilan yang menyesuaikan ponsel dan tablet.')

# ═════════════════════════ BAB III ═════════════════════════
CHAPTER('III', 'HASIL DAN ANALISIS')
H2('3.1', 'Exploratory Data Analysis')
P('Eksplorasi awal dilakukan pada 23.862 hari-stasiun yang memiliki rata-rata PM2.5 harian valid dari 26 stasiun. '
  'Statistik deskriptif setiap polutan disajikan pada Tabel 3.1.')
TABLE('Statistik deskriptif polutan harian (µg/m³)', ['Polutan', 'Rata-rata', 'Median', 'Persentil 95', 'Maksimum'], [
    ['PM2.5', '39,9', '31,0', '97,0', '1.127,6'], ['PM10', '58,1', '45,8', '138,5', '1.391,0'],
    [u('NO2'), '25,9', '20,2', '60,6', '66,6'], [u('SO2'), '9,9', '7,3', '22,7', '34,0'],
    ['CO', '624,8', '360,9', '1.794,1', '7.606,6'], [u('O3'), '20,4', '13,9', '36,4', '41,5'],
], [0.24, 0.19, 0.19, 0.19, 0.19], ['L', 'R', 'R', 'R', 'R'])
P(u('Tiga temuan eksplorasi menentukan isi dashboard. Pertama, PM2.5 dan PM10 memiliki ekor kanan yang panjang (kemencengan '
  'PM2.5 10,1). Rata-rata lebih tinggi dari median dan nilai ekstrem hanya muncul di Sumatera dan Kalimantan (Gambar 3.1), '
  'sehingga dashboard menampilkan kategori ISPU, filter musim, dan halaman khusus episode kabut asap, bukan hanya rata-rata. '
  'Kedua, sebaran per pulau sangat berbeda. Papua dan Sulawesi hampir seluruhnya di bawah baku mutu 24 jam, Jawa tinggi tetapi '
  'stabil, sedangkan Kalimantan memiliki median sedang dengan lonjakan sampai di atas 1.000 µg/m³. Karena itu, pulau menjadi '
  'filter utama dan warna tetap di semua grafik.'))
FIGURE('eda_pm25_distribusi.png', 'Distribusi PM2.5 harian per pulau (skala logaritma)', maxh=170)
P(u('Ketiga, korelasi Spearman antarvariabel harian (Gambar 3.2) menunjukkan PM2.5 hampir identik dengan PM10 (ρ = 0,99), '
  'sedangkan CO, NO2, dan SO2 saling berkorelasi kuat (ρ 0,77–0,85) karena ketiganya tinggi di stasiun yang sama, terutama '
  'Jakarta. Korelasi gabungan ini terutama mencerminkan perbedaan antarstasiun, bukan pengaruh cuaca. Oleh sebab itu, faktor '
  'penyebab dianalisis dengan korelasi di dalam setiap stasiun, perbandingan antarstasiun pada musim hujan, dan model Random '
  'Forest, lalu hasilnya ditampilkan di halaman Penyebab.'))
FIGURE('eda_korelasi.png', 'Korelasi Spearman antara polutan dan cuaca harian', w=TW * 0.5, maxh=210)

H2('3.2', 'Gambaran Umum dan Fitur Utama Dashboard')
P('Dashboard dibuka dengan halaman pembuka berisi logo Gelar Rasa, judul "Membaca udara [pulau] melalui data", tombol '
  'Buka dashboard, dan tautan Petunjuk Pengukuran (Gambar 3.3 kiri). Setelah dibuka, setiap halaman memiliki susunan yang sama '
  '(Gambar 3.4).')
FIGURE(['opening.png', 'drawer.png'], 'Halaman pembuka (kiri) dan panel detail stasiun KTG-01 (kanan)', maxh=170)
FIGURE('ringkasan_top.png', 'Tampilan halaman Ringkasan pada layar laptop', maxh=235)
NL(['<b>Bilah navigasi</b> di bagian atas berisi logo (kembali ke halaman pembuka), enam halaman analisis, halaman '
    'Petunjuk Pengukuran, dan sakelar mode terang/gelap. Bilah ini tersembunyi saat pengguna menggulir melewati kartu '
    'indikator dan muncul kembali saat menggulir ke atas. Pada ponsel, menu berpindah ke tombol Menu.',
    '<b>Baris filter</b> berisi Pulau, Tipe Lokasi, Musim, dan Tahun. Pilihan berlaku di semua halaman sehingga pengguna dapat '
    'mengikuti satu wilayah dari kondisi sampai dampak kesehatan.',
    '<b>Kartu indikator</b> menampilkan empat angka utama setiap halaman, misalnya rata-rata PM2.5, hari tidak sehat, hari kabut '
    'asap, dan kasus ISPA balita pada Ringkasan. Angkanya berubah mengikuti filter.',
    '<b>Panel stasiun</b> memeringkat 26 stasiun dari yang tertinggi atau terbersih. Kotak centang dipakai untuk membandingkan '
    'hingga enam stasiun, dan klik nama stasiun membuka panel detail berisi PM2.5 harian, kategori ISPU, pola per jam, '
    'lokasi, alat, dan rumah sakit pasangan.',
    '<b>Kartu grafik</b> berisi satu grafik, tabel, atau peta dengan judul, tooltip, dan pengendali seperti pemilih polutan. '
    'Tidak ada teks di atas grafik selain keterangan garis acuan di bawahnya.',
    '<b>Petunjuk Pengukuran</b> menjelaskan satuan, konversi, pengolahan data, ISPU, IKU, baku mutu, dan setiap metode.'])
P('Tangkapan layar lengkap ketujuh halaman disajikan pada Lampiran 3.')

H2('3.3', 'Telaah dan Penafsiran Visualisasi')
VIS(1, 'Peta PM2.5 per Stasiun', 'ringkasan__peta.png', 'Peta rata-rata PM2.5 per stasiun (halaman Ringkasan)',
    'Titik terbesar dan berwarna merah berkumpul di Sumatera bagian selatan (Palembang, Pesawaran), Kalimantan (Palangka Raya, '
    'Sampit, Samarinda, Banjarbaru), serta pesisir utara Jakarta. Titik biru (kategori Baik) hanya ada di Aceh Besar, '
    'Poso, dan Bogor. Seluruh 26 stasiun rata-rata 40,9 µg/m³ dan 23 di antaranya melampaui baku mutu tahunan 15 µg/m³.',
    'Pencemaran terkonsentrasi di dua jenis wilayah, yaitu kota besar dengan industri dan lalu lintas padat serta wilayah '
    'gambut yang rawan terbakar. Peta ini menjadi titik masuk: pengguna melihat sebarannya, lalu mengklik titik untuk membuka '
    'detail stasiun.')
VIS(2, 'PM2.5 per Pulau', 'ringkasan__pm2_5_per_pulau.png', 'Rata-rata PM2.5 per pulau',
    'Kalimantan memiliki rata-rata tertinggi (57,1 µg/m³), diikuti Sumatera (41,3), Jawa (37,9), Sulawesi (24,0), dan Papua '
    '(17,2). Kelima pulau berada di atas baku mutu tahunan 15 µg/m³.',
    'Tidak ada pulau yang memenuhi baku mutu, sehingga masalahnya bersifat nasional. Kalimantan dan Sumatera tinggi karena '
    'kabut asap musiman, sedangkan Jawa tinggi karena sumber perkotaan dan industri yang menetap.')
VIS(3, 'Kategori ISPU per Pulau', 'ringkasan__kategori_ispu_per_pulau.png', 'Porsi hari menurut kategori ISPU per pulau',
    'Dari seluruh hari-stasiun, 17,8% Baik, 64,6% Sedang, 16,6% Tidak Sehat, 0,6% Sangat Tidak Sehat, dan 0,4% Berbahaya. '
    'Kalimantan hanya memiliki 1,4% hari Baik dan merupakan satu-satunya pulau dengan hari Berbahaya (1,8%). Sulawesi memiliki '
    'porsi hari Baik tertinggi (50,0%).',
    'Kategori Tidak Sehat ke atas di Kalimantan dan Sumatera terjadi pada musim kemarau, sedangkan di Jawa tersebar sepanjang '
    'tahun. Perbedaan ini menentukan jenis tindakan, yaitu kesiapsiagaan musiman di wilayah gambut dan pengendalian emisi rutin '
    'di wilayah perkotaan.')
VIS(4, 'Peringkat Stasiun', 'kondisi__peringkat_stasiun.png', 'Peringkat stasiun menurut rata-rata PM2.5 dengan garis baku mutu dan WHO',
    'SM2-01 (Samarinda) tertinggi dengan 78,8 µg/m³, diikuti PLB-01 (65,2), KTG-01 (61,2), KTG-02 (60,8), PSW-01 (60,1), dan '
    'JKT-02 (60,1). Hanya IDP-01 (9,3), PLU-01 (11,3), dan BGR-01 (13,2) yang berada di bawah 15 µg/m³, dan tidak ada stasiun '
    'yang memenuhi pedoman WHO 5 µg/m³.',
    'Stasiun teratas terbagi dua: stasiun industri dan perkotaan yang tinggi sepanjang tahun (SM2-01, JKT-02) dan stasiun '
    'gambut yang tinggi karena kabut asap (PLB-01, KTG-01/02). Pemilih polutan memungkinkan perbandingan yang sama untuk PM10, '
    + u('SO2, CO, O3, dan NO2.'))
VIS(5, 'Baku Mutu dan IKU', 'kondisi__baku_mutu_dan_iku.png', 'Tabel rata-rata tahunan, baku mutu, dan IKU per stasiun (2025)',
    u('Pada setiap tahun 2024–2026, hanya 3 stasiun yang memenuhi baku mutu tahunan PM2.5. Tiga stasiun Jakarta melampaui baku '
      'mutu NO2 tahunan (50 µg/m³) dan sedikit melampaui O3 (35 µg/m³) setiap tahun. IKU berkategori Kurang di JKT-01 dan JKT-03 '
      'serta Sangat Kurang di JKT-02, sedangkan 21 stasiun berkategori Baik.'),
    'IKU hanya memakai gas, sehingga wilayah kabut asap tetap berkategori Baik walaupun PM2.5-nya tinggi. Karena itu, IKU '
    'perlu dibaca bersama ISPU. Titik merah pada tabel membantu pengguna langsung melihat parameter yang melanggar.')
VIS(6, 'Tren Bulanan', 'kondisi__tren_bulanan.png', 'Tren rata-rata PM2.5 bulanan per pulau, 2024–2026',
    'Garis Jawa, Sulawesi, dan Papua datar sepanjang periode. Kalimantan dan Sumatera melonjak setiap Agustus–Oktober, dan '
    'lonjakannya membesar: rata-rata bulanan Kalimantan mencapai 113,7 µg/m³ pada September 2025 dan 437,2 µg/m³ pada Oktober '
    '2026. Sebanyak 12 dari 26 stasiun memburuk lebih dari 10% dari 2024 ke 2026, seluruhnya di Sumatera dan Kalimantan.',
    'Kenaikan hampir seluruhnya berasal dari musim kabut asap, karena tingkat dasar musim hujan stabil. Pengecualiannya adalah '
    'SM2-01 yang tingkat dasarnya naik sekitar 23% per tahun, sehingga perlu penelusuran sumber emisi lokal.')
VIS(7, 'Pola per Jam', 'kritis__pola_per_jam.png', 'Rata-rata PM2.5 per jam menurut tipe lokasi',
    u('Semua tipe lokasi memiliki dua puncak, sekitar pukul 07.00 dan 18.00 WIB. NO2 di tepi jalan naik dari 36,8 menjadi 49,1 '
      'µg/m³ pada jam puncak. Rata-rata hari kerja dan akhir pekan hampir sama (PM2.5 33,5 dibanding 33,4 µg/m³, NO2 25,7 '
      'dibanding 25,7 µg/m³).'),
    'Puncak pagi dan sore sejalan dengan jam berangkat dan pulang kerja. Karena akhir pekan tidak lebih bersih, pengendalian '
    'lalu lintas perlu berlaku tujuh hari seminggu pada jam puncak, bukan hanya pada hari kerja.')
VIS(8, 'Pola per Bulan', 'kritis__pola_per_bulan.png', 'Rata-rata PM2.5 per stasiun dan bulan',
    'Blok warna gelap muncul pada Agustus–Oktober di KTG-01, KTG-02, PKN-01, STG-01, PLB-01, dan stasiun Sumatera lainnya. '
    'Di stasiun gambut, PM2.5 musim kemarau naik 177% dibanding musim hujan, sedangkan di tepi jalan Jakarta dan Bogor hanya 4%.',
    'Bulan kritis adalah Agustus–Oktober dan hanya berlaku untuk wilayah gambut. Informasi ini menjadi dasar jadwal '
    'kesiapsiagaan kabut asap, yaitu persiapan sejak Juli sebelum puncak.')
VIS(9, 'Episode Kabut Asap', 'kritis__episode_kabut_asap.png', 'Linimasa episode kabut asap per stasiun',
    'Terdapat 84 episode: 38 pada 2024, 30 pada 2025, dan 16 pada 2026. Jumlahnya turun tetapi episodenya makin panjang. '
    'Episode di KTG-01 dan KTG-02 pada 2026 berlangsung 106 hari tanpa putus (1 Juli–14 Oktober), dengan PM2.5 harian '
    'tertinggi 1.128 µg/m³ (kategori Berbahaya).',
    'Kabut asap bergeser dari banyak episode pendek menjadi sedikit episode yang sangat panjang dan pekat. Di KTG-01/02, CO ikut '
    'naik 150% saat episode, konsisten dengan kebakaran di dekat stasiun. Di Batam dan Pekanbaru, PM2.5 naik tanpa kenaikan CO, '
    'konsisten dengan asap kiriman dari wilayah lain.')
VIS(10, 'Tingkat Kepentingan Faktor', 'faktor__tingkat_kepentingan_faktor.png', 'Kepentingan faktor dalam model Random Forest PM2.5 harian',
    'Musim (bulan) menyumbang 41,7% kepentingan, diikuti tipe lokasi (21,4%), pulau (10,1%), intensitas lalu lintas (8,5%), dan '
    'jarak ke jalan raya (8,0%). Kelembapan, suhu, kecepatan angin, dan arah angin masing-masing di bawah 4%, dan hari dalam '
    'minggu 0%. Model menjelaskan 87% variasi PM2.5 harian pada data uji 2026 (R² = 0,87).',
    'Variasi PM2.5 terutama ditentukan oleh kapan (musim kabut) dan di mana (tipe lokasi), bukan oleh cuaca harian. Cuaca hanya '
    + u('kuat memengaruhi O3, yang naik saat suhu tinggi di seluruh 26 stasiun. Arah angin berpengaruh lebih dari 10% hanya di '
      'tiga stasiun.'))
VIS(11, 'Lalu Lintas dan Polutan', 'faktor__lalu_lintas_dan_polutan.png', 'Hubungan intensitas lalu lintas dan PM2.5 musim hujan antarstasiun',
    'Di luar musim kabut, stasiun dengan lalu lintas lebih padat memiliki PM2.5 lebih tinggi (Spearman ρ = 0,75, p &lt; 0,001). '
    'Kenaikan lalu lintas 10% berkaitan dengan kenaikan PM2.5 sekitar 4,8%. Jarak ke jalan raya berkorelasi negatif (ρ = −0,65), '
    'tetapi tidak bermakna setelah lalu lintas dikontrol.',
    'Lalu lintas adalah sumber utama perbedaan PM2.5 antarstasiun pada musim hujan, sehingga pengendalian kendaraan adalah '
    'tindakan yang paling relevan untuk wilayah perkotaan. Ukuran titik (jarak ke jalan) membantu memisahkan stasiun tepi '
    'jalan dari stasiun latar.')
VIS(12, 'Efek per Hari Jeda', 'kesehatan__efek_per_hari_jeda.png', 'Kenaikan kasus ISPA balita per 10 µg/m³ PM2.5 menurut hari jeda',
    'Setiap kenaikan PM2.5 sebesar 10 µg/m³ meningkatkan rawat inap ISPA balita 13,6% pada hari yang sama (jeda 0). Efek pada '
    'jeda 1–7 hari kecil dan tidak bermakna, sehingga efek kumulatif tujuh hari (13,8%) hampir sama dengan jeda 0. Pola serupa '
    'terlihat pada ISPA lansia (13,8%), PPOK (13,4%), kematian (6,5%), dan kardiovaskular (4,9%).',
    'Dampak polusi pada kesehatan muncul pada hari yang sama, sehingga peringatan dini harus disampaikan pada hari itu juga, '
    'bukan keesokan harinya. Saat kabut asap, kasus ISPA balita rata-rata naik 155% dibanding hari biasa.')
VIS(13, 'Risiko per Kategori ISPU', 'kesehatan__risiko_per_kategori_ispu.png', 'Risiko relatif kasus menurut kategori ISPU dibanding hari Baik',
    'Risiko ISPA balita naik bertahap: 1,15 kali pada hari Sedang, 2,08 kali pada Tidak Sehat, 3,38 kali pada Sangat Tidak '
    'Sehat, dan 3,93 kali pada Berbahaya. Kematian dan kardiovaskular hampir datar sampai Sangat Tidak Sehat, lalu melonjak '
    'sekitar 7,4 kali pada kategori Berbahaya.',
    'Balita sedikit lebih sensitif daripada lansia (13,7% dibanding 13,2% per 10 µg/m³, z = 2,9), tetapi lansia menyumbang kasus '
    'lebih banyak. Secara keseluruhan, sekitar 42.708 kasus ISPA balita (26,0%) tidak akan terjadi bila PM2.5 berada pada '
    'kategori Baik.')
VIS(14, 'Peta Jaringan Pemantauan', 'jaringan__peta.png', 'Sebaran stasiun menurut keandalan alat dan celah antarstasiun',
    'Hanya 21 dari 27 stasiun yang andal, dan stasiun memantau 21 provinsi. Celah terlebar berada di Papua (SRG-01 ke MER-01, '
    '1.319 km), Sumatera bagian utara (PKU-01 ke MDN-01, 453 km), Kalimantan (KTG-01 ke SM2-01, 409 km), Jawa (BGR-01 ke '
    'YKY-01, 394 km), dan Sulawesi (MRS-01 ke PLU-01, 378 km). Sebaliknya, lima stasiun Jawa berkumpul di Jakarta–Bogor.',
    'Jaringan belum memadai. Wilayah yang luas tidak terpantau, sementara wilayah lain memiliki stasiun yang berdekatan. '
    'Garis merah putus-putus pada peta langsung menunjukkan lokasi yang paling membutuhkan titik pantau baru.')
VIS(15, 'Skor Prioritas Stasiun', 'jaringan__skor_prioritas_stasiun.png', 'Skor prioritas penguatan pemantauan per stasiun',
    'KTG-02 memiliki skor tertinggi (68), diikuti PSW-01 (63), KTG-01 (61), PLB-01 (57), dan BTM-01 (56). Skor disusun dari '
    'polusi (25%), kabut asap (20%), beban kesehatan per 100 tempat tidur (20%), defisit data (20%), dan keterisolasian (15%).',
    'Prioritas tertinggi ada di wilayah yang tercemar berat, sering berkabut asap, dan beban rumah sakitnya tinggi. Komponen '
    'yang kosong tidak diisi, dan bobotnya dibagi ulang ke komponen yang tersedia sehingga tidak ada data yang ditambahkan.',
    maxh=260)

# ═════════════════════════ BAB IV ═════════════════════════
CHAPTER('IV', 'PENUTUP')
H2('4.1', 'Kesimpulan')
NL(['<b>Kondisi kualitas udara.</b> Rata-rata PM2.5 26 stasiun adalah 40,9 µg/m³ dan 23 stasiun melampaui baku mutu tahunan. '
    'Kalimantan paling tercemar (57,1 µg/m³) dan Papua paling bersih (17,2 µg/m³). '
    + u('Jakarta juga melampaui baku mutu NO2 dan O3 tahunan dengan IKU Kurang sampai Sangat Kurang. Sebanyak 12 stasiun '
        'memburuk dari 2024 ke 2026, seluruhnya di Sumatera dan Kalimantan.'),
    '<b>Waktu dan wilayah kritis.</b> Terdapat dua jenis masalah, yaitu pencemaran kronis perkotaan dan industri di Jakarta '
    'dengan puncak pukul 07.00 dan 18.00 WIB setiap hari, serta pencemaran musiman akibat karhutla di Sumatera dan Kalimantan '
    'pada Agustus–Oktober yang makin panjang dan pekat, dengan puncak 1.128 µg/m³ di Palangka Raya pada 2026.',
    '<b>Faktor penyebab.</b> Musim dan tipe lokasi paling menentukan variasi PM2.5 (63% kepentingan gabungan), dan di luar '
    + u('musim kabut intensitas lalu lintas menjelaskan perbedaan antarstasiun (ρ = 0,75). Cuaca hanya kuat memengaruhi O3.'),
    '<b>Dampak kesehatan.</b> Setiap kenaikan 10 µg/m³ PM2.5 meningkatkan ISPA balita dan lansia sekitar 13–14% dan kematian '
    'sekitar 6–7% pada hari yang sama. Balita sedikit lebih sensitif, sedangkan lansia menyumbang kasus lebih banyak.',
    '<b>Jaringan pemantauan.</b> Jaringan belum memadai karena 6 dari 27 stasiun tidak andal dan terdapat celah 378–1.319 km. '
    'KTG-02, PSW-01, dan KTG-01 adalah prioritas utama penguatan.'])
H2('4.2', 'Saran')
NL(['<b>Peringatan dini pada hari yang sama.</b> Peringatan ISPU perlu disampaikan pada hari paparan, dengan prioritas '
    'perlindungan balita dan kesiapan rawat inap lansia ketika ISPU mencapai Tidak Sehat.',
    '<b>Kesiapsiagaan kabut asap mulai Juli</b> di sembilan stasiun dengan sedikitnya 200 hari kabut asap, yaitu KTG-02, KTG-01, '
    'PKU-01, PKN-01, JMB-01, BTM-01, PSW-01, STG-01, dan BJB-01, termasuk tambahan kapasitas rumah sakit saat episode.',
    '<b>Pengendalian lalu lintas</b> pukul 07.00–08.00 dan 18.00–19.00 WIB setiap hari, terutama di Jakarta.',
    '<b>Perbaikan alat</b> dengan mengganti JMB-02, memulihkan MER-01, mengkalibrasi BJB-01 dan MDN-01, serta menyeragamkan '
    'ekspor logger ke µg/m³ per jam.',
    '<b>Penambahan titik pantau</b> pada celah terlebar di Papua, Sumatera bagian utara, Kalimantan, Jawa bagian tengah, dan '
    'Sulawesi, serta penelusuran sumber emisi di Samarinda (SM2-01).',
    '<b>Pengembangan dashboard</b> dengan data pemantauan waktu nyata agar peringatan terkirim otomatis.'])

# ═════════════════════════ DAFTAR PUSTAKA + LAMPIRAN ═════════════════════════
story.append(NextPageTemplate('front'))
SECTION('DAFTAR PUSTAKA')
S_REF = ParagraphStyle('ref', parent=S_BODY, alignment=TA_LEFT, leftIndent=28, firstLineIndent=-28, spaceAfter=8)
REFS = [
    'Bhaskaran, K., Gasparrini, A., Hajat, S., Smeeth, L., &amp; Armstrong, B. (2013). Time series regression studies in environmental epidemiology. <i>International Journal of Epidemiology, 42</i>(4), 1187–1195. https://doi.org/10.1093/ije/dyt092',
    'Breiman, L. (2001). Random forests. <i>Machine Learning, 45</i>(1), 5–32. https://doi.org/10.1023/A:1010933404324',
    'Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. <i>Computing in Science &amp; Engineering, 9</i>(3), 90–95. https://doi.org/10.1109/MCSE.2007.55',
    'Kementerian Lingkungan Hidup dan Kehutanan. (2020). <i>Peraturan Menteri Lingkungan Hidup dan Kehutanan Nomor P.14/MENLHK/SETJEN/KUM.1/7/2020 tentang Indeks Standar Pencemar Udara</i>.',
    'Kementerian Lingkungan Hidup dan Kehutanan. (2021). <i>Peraturan Menteri Lingkungan Hidup dan Kehutanan Nomor 27 Tahun 2021 tentang Indeks Kualitas Lingkungan Hidup</i>.',
    'Li, D., Mei, H., Shen, Y., Su, S., Zhang, W., Wang, J., Zu, M., &amp; Chen, W. (2018). ECharts: A declarative framework for rapid construction of web-based visualization. <i>Visual Informatics, 2</i>(2), 136–146. https://doi.org/10.1016/j.visinf.2018.04.011',
    'Mann, H. B. (1945). Nonparametric tests against trend. <i>Econometrica, 13</i>(3), 245–259. https://doi.org/10.2307/1907187',
    'McKinney, W. (2010). Data structures for statistical computing in Python. In S. van der Walt &amp; J. Millman (Eds.), <i>Proceedings of the 9th Python in Science Conference</i> (pp. 56–61). https://doi.org/10.25080/Majora-92bf1922-00a',
    'Panitia Gelar Rasa 2026. (2026). <i>Booklet case study Dashboard Analysis Gelar Rasa 2026</i>.',
    'Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., &amp; Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. <i>Journal of Machine Learning Research, 12</i>, 2825–2830.',
    'Pemerintah Republik Indonesia. (2021). <i>Peraturan Pemerintah Nomor 22 Tahun 2021 tentang Penyelenggaraan Perlindungan dan Pengelolaan Lingkungan Hidup</i>.',
    'Schwartz, J. (2000). The distributed lag between air pollution and daily deaths. <i>Epidemiology, 11</i>(3), 320–326. https://doi.org/10.1097/00001648-200005000-00016',
    'Seabold, S., &amp; Perktold, J. (2010). Statsmodels: Econometric and statistical modeling with Python. In S. van der Walt &amp; J. Millman (Eds.), <i>Proceedings of the 9th Python in Science Conference</i> (pp. 92–96). https://doi.org/10.25080/Majora-92bf1922-011',
    'Seinfeld, J. H., &amp; Pandis, S. N. (2016). <i>Atmospheric chemistry and physics: From air pollution to climate change</i> (3rd ed.). Wiley.',
    'World Health Organization. (2021). <i>WHO global air quality guidelines: Particulate matter (PM2.5 and PM10), ozone, nitrogen dioxide, sulfur dioxide and carbon monoxide</i>. https://www.who.int/publications/i/item/9789240034228',
]
for r in REFS:
    story.append(Paragraph(r, S_REF))
BLOCKS.append({'t': 'refs', 'items': REFS})

SECTION('LAMPIRAN')
BLOCKS.append({'t': 'p', 'text': '<b>Lampiran 1. Tautan Hasil Pengerjaan Dashboard</b>'})
BLOCKS.append({'t': 'p', 'text': f'Dashboard dapat dibuka tanpa login dan tanpa meminta akses melalui tautan berikut: {DASHBOARD_URL}'})
BLOCKS.append({'t': 'p', 'text': '<b>Lampiran 2. Tautan Repository GitHub</b>'})
BLOCKS.append({'t': 'p', 'text': f'Kode preprocessing, analisis, dan dashboard: {GITHUB_URL}'})
BLOCKS.append({'t': 'p', 'text': '<b>Lampiran 3. Tangkapan Layar Halaman Dashboard</b>'})
story.append(Paragraph('<b>Lampiran 1. Tautan Hasil Pengerjaan Dashboard</b>', S_BODY))
story.append(Paragraph(f'Dashboard dapat dibuka tanpa login dan tanpa meminta akses melalui tautan berikut: {DASHBOARD_URL}', S_BODY))
story.append(Spacer(1, 6))
story.append(Paragraph('<b>Lampiran 2. Tautan Repository GitHub</b>', S_BODY))
story.append(Paragraph(f'Kode preprocessing, analisis, dan dashboard: {GITHUB_URL}', S_BODY))
story.append(Spacer(1, 6))
story.append(Paragraph('<b>Lampiran 3. Tangkapan Layar Halaman Dashboard</b>', S_BODY))
for p, t in [('ringkasan', 'Ringkasan'), ('kondisi', 'Kondisi'), ('kritis', 'Waktu Kritis'), ('faktor', 'Penyebab'),
             ('kesehatan', 'Kesehatan'), ('jaringan', 'Jaringan'), ('petunjuk', 'Petunjuk Pengukuran')]:
    src = os.path.join(FIG, f'page_{p}.png')
    iw, ih = PILImage.open(src).size
    if ih / iw > 1.6:      # tall page: show top and bottom halves side by side so the text stays readable
        im = PILImage.open(src); half = ih // 2 + 40
        parts = []
        for k, (a0, a1) in enumerate([(0, half), (ih - half, ih)]):
            fn = os.path.join(FIG, f'page_{p}_{k}.png'); im.crop((0, a0, iw, a1)).save(fn); parts.append(fn)
        for k, part in enumerate(parts):
            story.append(KeepTogether([img(part, TW, PH - MT - MB - 40),
                                       Paragraph(f'Halaman {t} ({"bagian atas" if k == 0 else "bagian bawah"})', S_CAP)]))
            BLOCKS.append({'t': 'plainfig', 'path': part, 'caption': f'Halaman {t} ({"bagian atas" if k == 0 else "bagian bawah"})'})
    else:
        story.append(KeepTogether([img(src, TW, PH - MT - MB - 40), Paragraph(f'Halaman {t}', S_CAP)]))
        BLOCKS.append({'t': 'plainfig', 'path': src, 'caption': f'Halaman {t}'})

doc = Doc(OUT)
doc.multiBuild(story)
import json
json.dump({'config': {'team': TEAM, 'leader': LEADER, 'members': MEMBERS, 'institution': INSTITUTION, 'title_lines': TITLE_LINES,
                      'leader_file': LEADER_FILE, 'dashboard_url': DASHBOARD_URL, 'github_url': GITHUB_URL},
           'blocks': BLOCKS, 'toc': TOCREC}, open(os.path.join(ROOT, 'content.json'), 'w'), ensure_ascii=False, indent=0)
print(OUT)
print('body starts at absolute page', STATE['body_start'])
