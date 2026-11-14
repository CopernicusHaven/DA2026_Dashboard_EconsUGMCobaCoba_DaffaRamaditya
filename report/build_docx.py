"""Versi Word (.docx) laporan DA2026 yang dapat disunting. Isi diambil dari content.json yang ditulis
build_report.py, jadi teks, tabel, dan gambar sama persis dengan PDF.
    python3 build_report.py   # PDF + content.json
    python3 build_docx.py     # DOCX
Daftar isi, daftar tabel, dan daftar gambar adalah field Word: klik kanan > Update Field (Word) untuk
memperbarui nomor halaman setelah menyunting.
"""
import copy, html, json, os, re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image as PILImage

ROOT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(ROOT, 'figures')
TPL = os.path.join(ROOT, 'template')
C = json.load(open(os.path.join(ROOT, 'content.json'), encoding='utf-8'))
CFG = C['config']
OUT = os.path.join(ROOT, f"DA2026_Laporan_{re.sub(r'[^A-Za-z0-9]', '', CFG['team'])}_{CFG['leader_file']}.docx")

ML, MR, MT, MB = 85, 83, 112, 96            # same margins as the PDF (pt)
TW = 595.28 - ML - MR                        # text width (pt)
FONT = 'Times New Roman'
BLACK = RGBColor(0, 0, 0)

doc = Document()


# ───────────── styles ─────────────
def set_font(style_or_run, size=None, bold=None, italic=None):
    f = style_or_run.font
    f.name = FONT
    f.color.rgb = BLACK
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    rpr = style_or_run.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for k in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        rf.set(qn(k), FONT)
    for k in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        if rf.get(qn(k)) is not None:
            del rf.attrib[qn(k)]


st = doc.styles
normal = st['Normal']
set_font(normal, 12)
pf = normal.paragraph_format
pf.line_spacing = 1.15; pf.space_after = Pt(6); pf.space_before = Pt(0); pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

for name, size, align, before, after in [('Heading 1', 12, WD_ALIGN_PARAGRAPH.CENTER, 0, 18), ('Heading 2', 12, WD_ALIGN_PARAGRAPH.LEFT, 10, 6),
                                         ('Heading 3', 12, WD_ALIGN_PARAGRAPH.LEFT, 8, 5)]:
    h = st[name]
    set_font(h, size, bold=True, italic=False)
    h.paragraph_format.alignment = align
    h.paragraph_format.space_before = Pt(before); h.paragraph_format.space_after = Pt(after)
    h.paragraph_format.keep_with_next = True; h.paragraph_format.line_spacing = 1.15


def new_style(name, size, align, before, after, line=1.0, left=None, hanging=None, base='Normal'):
    s = st.add_style(name, 1)
    s.base_style = st[base]
    set_font(s, size)
    p = s.paragraph_format
    p.alignment = align; p.space_before = Pt(before); p.space_after = Pt(after); p.line_spacing = line
    if left is not None: p.left_indent = Pt(left)
    if hanging is not None: p.first_line_indent = Pt(-hanging)
    return s


new_style('Keterangan Gambar', 11, WD_ALIGN_PARAGRAPH.CENTER, 3, 10)
new_style('Keterangan Tabel', 11, WD_ALIGN_PARAGRAPH.CENTER, 6, 4)
new_style('Judul Halaman', 12, WD_ALIGN_PARAGRAPH.CENTER, 0, 18, 1.15)
st['Judul Halaman'].font.bold = True
new_style('Daftar Bernomor', 12, WD_ALIGN_PARAGRAPH.JUSTIFY, 0, 3, 1.15, left=18, hanging=14)
new_style('Isi Tabel', 10, WD_ALIGN_PARAGRAPH.LEFT, 0, 0, 1.0)
new_style('Pustaka', 12, WD_ALIGN_PARAGRAPH.LEFT, 0, 8, 1.15, left=28, hanging=28)
new_style('Gambar', 12, WD_ALIGN_PARAGRAPH.CENTER, 4, 0, 1.0)
st['Gambar'].paragraph_format.keep_with_next = True


# ───────────── inline markup (<b>, <i>, <sub>, <br/>, entities) ─────────────
def add_rich(par, text, size=None, bold=False):
    state = {'b': bold, 'i': False, 'sub': False, 'sup': False}
    for tok in re.split(r'(<[^>]+>)', text):
        if not tok:
            continue
        if tok.startswith('<'):
            t = tok.lower().replace(' ', '')
            if t in ('<br/>', '<br>'):
                par.add_run().add_break()
            elif t.startswith('<b>'): state['b'] = True
            elif t.startswith('</b>'): state['b'] = bold
            elif t.startswith('<i>'): state['i'] = True
            elif t.startswith('</i>'): state['i'] = False
            elif t.startswith('<sub>'): state['sub'] = True
            elif t.startswith('</sub>'): state['sub'] = False
            elif t.startswith('<super>'): state['sup'] = True
            elif t.startswith('</super>'): state['sup'] = False
            continue
        r = par.add_run(html.unescape(tok))
        r.bold = state['b'] or None
        r.italic = state['i'] or None
        if state['sub']: r.font.subscript = True
        if state['sup']: r.font.superscript = True
        if size: r.font.size = Pt(size)
    return par


def plain(text):
    return html.unescape(re.sub(r'<[^>]+>', '', text))


# ───────────── page backgrounds (template images behind the text) ─────────────
def background(section, path):
    section.header.is_linked_to_previous = False
    hp = section.header.paragraphs[0]
    run = hp.add_run()
    run.add_picture(path, width=Mm(210), height=Mm(297))
    inline = run._r.find('.//' + qn('wp:inline'))
    anchor = OxmlElement('wp:anchor')
    for k, v in dict(distT='0', distB='0', distL='0', distR='0', simplePos='0', relativeHeight='0', behindDoc='1', locked='1',
                     layoutInCell='1', allowOverlap='1').items():
        anchor.set(k, v)
    sp = OxmlElement('wp:simplePos'); sp.set('x', '0'); sp.set('y', '0'); anchor.append(sp)
    for tag in ('wp:positionH', 'wp:positionV'):
        e = OxmlElement(tag); e.set('relativeFrom', 'page')
        o = OxmlElement('wp:posOffset'); o.text = '0'; e.append(o); anchor.append(e)
    anchor.append(copy.deepcopy(inline.find(qn('wp:extent'))))
    ee = OxmlElement('wp:effectExtent')
    for k in 'ltrb': ee.set(k, '0')
    anchor.append(ee)
    anchor.append(OxmlElement('wp:wrapNone'))
    for tag in ('wp:docPr', 'wp:cNvGraphicFramePr', 'a:graphic'):
        e = inline.find(qn(tag))
        if e is not None:
            anchor.append(copy.deepcopy(e))
    inline.getparent().replace(inline, anchor)


def page_number(section, fmt, start):
    section.footer.is_linked_to_previous = False
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), 'PAGE')
    r = OxmlElement('w:r'); t = OxmlElement('w:t'); t.text = '1'; r.append(t); fld.append(r)
    fp._p.append(fld)
    for run in fp.runs: set_font(run, 11)
    pg = OxmlElement('w:pgNumType'); pg.set(qn('w:fmt'), fmt); pg.set(qn('w:start'), str(start))
    sp = section._sectPr
    for old in sp.findall(qn('w:pgNumType')):   # a new section copies the previous one's settings
        sp.remove(old)
    anchor = sp.find(qn('w:cols'))
    if anchor is not None:
        anchor.addprevious(pg)          # schema order: ... pgMar, pgNumType, cols ...
    else:
        sp.find(qn('w:pgMar')).addnext(pg)


def setup(section):
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Pt(ML), Pt(MR)
    section.top_margin, section.bottom_margin = Pt(MT), Pt(MB)
    section.header_distance, section.footer_distance = Pt(20), Pt(34)


def jpg(name):
    stem = os.path.splitext(os.path.basename(name))[0]
    p = os.path.join(FIG, '_jpg', stem + '.jpg')
    return p if os.path.exists(p) else (name if os.path.isabs(name) else os.path.join(FIG, name))


def pic_size(path, w, maxh=None):
    iw, ih = PILImage.open(path).size
    h = w * ih / iw
    if maxh and h > maxh:
        w, h = w * maxh / h, maxh
    return w, h


# ═════════════ cover ═════════════
cover = doc.sections[0]
setup(cover)
background(cover, os.path.join(TPL, 'bg_sampul.png'))


def cpar(text, size=14, bold=True, before=0, after=0, align=WD_ALIGN_PARAGRAPH.CENTER, left=None):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = Pt(18.5)
    if left is not None: p.paragraph_format.left_indent = Pt(left)
    r = p.add_run(text); r.bold = bold; r.font.size = Pt(size)
    return p


cpar('LAPORAN ANALISIS')
for i, line in enumerate(CFG['title_lines']):
    cpar(('“' if i == 0 else '') + line + ('”' if i == len(CFG['title_lines']) - 1 else ''))
logo = os.path.join(ROOT, 'logo_instansi.png')
lp = logo if os.path.exists(logo) else os.path.join(TPL, 'logo_placeholder.png')
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(22); p.paragraph_format.space_after = Pt(28)
w, h = pic_size(lp, 216, 189)
p.add_run().add_picture(lp, width=Pt(w), height=Pt(h))
cpar('Disusun Oleh:')
cpar(CFG['team'])
for i, n in enumerate([CFG['leader']] + CFG['members']):
    cpar(f'{i + 1}.  {n}', bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, left=126)
cpar(CFG['institution'], before=60)
for t in ['DASHBOARD ANALYSIS', 'GELAR RASA 2026', '2026']:
    cpar(t)

# ═════════════ front matter: contents and lists (Word fields with the current entries filled in) ═════════════
front = doc.add_section(WD_SECTION.NEW_PAGE)
setup(front)
background(front, os.path.join(TPL, 'bg_halaman.jpg'))
page_number(front, 'lowerRoman', 2)


def fld_run(par, kind, instr=None):
    r = OxmlElement('w:r')
    if kind == 'instr':
        t = OxmlElement('w:instrText'); t.set(qn('xml:space'), 'preserve'); t.text = instr; r.append(t)
    else:
        f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), kind); r.append(f)
    par._p.append(r)


def field_list(instr, entries):
    """entries: (level, text, page). A real TOC field whose current result is already filled in."""
    if not entries:
        entries = [(0, '(diperbarui saat field diperbarui)', '')]
    pars = []
    for k, (lvl, text, page) in enumerate(entries):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par.paragraph_format.space_after = Pt(2); par.paragraph_format.line_spacing = 1.15
        par.paragraph_format.left_indent = Pt(24 * lvl)
        par.paragraph_format.tab_stops.add_tab_stop(Pt(TW), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        if k == 0:
            fld_run(par, 'begin'); fld_run(par, 'instr', instr); fld_run(par, 'separate')
        r = par.add_run(plain(text).replace('\xa0', ' ')); r.bold = (lvl == 0 and instr.startswith(' TOC \\o')) or None
        par.add_run('\t' + str(page))
        pars.append(par)
    fld_run(pars[-1], 'end')


def page_title(text, new_page=False):
    p = doc.add_paragraph(text, style='Judul Halaman')
    p.paragraph_format.page_break_before = new_page


toc = [(lvl, txt, pg) for kind, lvl, txt, pg in C['toc'] if kind == 'toc']
tabs = [(0, txt, pg) for kind, lvl, txt, pg in C['toc'] if kind == 'TabEntry']
figs = [(0, txt, pg) for kind, lvl, txt, pg in C['toc'] if kind == 'FigEntry']
page_title('DAFTAR ISI')
field_list(' TOC \\o "1-3" \\h \\z \\u ', toc)
page_title('DAFTAR TABEL', True)
field_list(' TOC \\h \\z \\t "Keterangan Tabel,1" ', tabs)
page_title('DAFTAR GAMBAR', True)
field_list(' TOC \\h \\z \\t "Keterangan Gambar,1" ', figs)

# ═════════════ body ═════════════
body = doc.add_section(WD_SECTION.NEW_PAGE)
setup(body)
background(body, os.path.join(TPL, 'bg_halaman.jpg'))
page_number(body, 'decimal', 1)
first_chapter = [True]


def figure_block(b):
    paths = [jpg(x) for x in b['paths']]
    maxh = min(b.get('maxh') or 330, 330)
    if len(paths) == 1:
        p = doc.add_paragraph(style='Gambar')
        w, h = pic_size(paths[0], TW * b['w'], maxh)
        p.add_run().add_picture(paths[0], width=Pt(w), height=Pt(h))
    else:
        cw = (TW - 10) / len(paths)
        t = doc.add_table(rows=1, cols=len(paths)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for k, path in enumerate(paths):
            cell = t.rows[0].cells[k]; cell.width = Pt(cw + 5)
            cp = cell.paragraphs[0]; cp.style = st['Gambar']
            w, h = pic_size(path, cw, maxh)
            cp.add_run().add_picture(path, width=Pt(w), height=Pt(h))
    cap = doc.add_paragraph(style='Keterangan Gambar')
    r = cap.add_run(f'Gambar {b["num"]}'); r.bold = True
    add_rich(cap, ' ' + b['caption'])


def table_block(b):
    cap = doc.add_paragraph(style='Keterangan Tabel')
    cap.paragraph_format.keep_with_next = True
    r = cap.add_run(f'Tabel {b["num"]}'); r.bold = True
    add_rich(cap, ' ' + b['caption'])
    head, rows, widths, align = b['head'], b['rows'], b['widths'], b['align']
    t = doc.add_table(rows=1 + len(rows), cols=len(head))
    t.style = st['Table Grid']; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    al = {'L': WD_ALIGN_PARAGRAPH.LEFT, 'C': WD_ALIGN_PARAGRAPH.CENTER, 'R': WD_ALIGN_PARAGRAPH.RIGHT}
    for i, row in enumerate([head] + rows):
        tr = t.rows[i]
        if i == 0:
            trpr = tr._tr.get_or_add_trPr(); th = OxmlElement('w:tblHeader'); th.set(qn('w:val'), 'true'); trpr.append(th)
        for j, val in enumerate(row):
            cell = tr.cells[j]; cell.width = Pt(TW * widths[j])
            cp = cell.paragraphs[0]; cp.style = st['Isi Tabel']
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else al[align[j]]
            add_rich(cp, val, bold=(i == 0))
            if i == 0:
                shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), 'E8F3E3')
                cell._tc.get_or_add_tcPr().append(shd)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


for b in C['blocks']:
    t = b['t']
    if t == 'chapter':
        p = doc.add_paragraph(style='Heading 1')
        p.paragraph_format.page_break_before = not first_chapter[0]
        first_chapter[0] = False
        p.add_run(f'BAB {b["num"]}'); p.add_run().add_break(); p.add_run(b['title'])
    elif t == 'section':
        p = doc.add_paragraph(b['title'], style='Heading 1'); p.paragraph_format.page_break_before = True
    elif t == 'h2':
        p = doc.add_paragraph(style='Heading 2')
        p.paragraph_format.left_indent = Pt(28); p.paragraph_format.first_line_indent = Pt(-28)
        p.paragraph_format.tab_stops.add_tab_stop(Pt(28))
        p.add_run(f'{b["num"]}\t{plain(b["title"])}')
    elif t == 'h3':
        doc.add_paragraph(f'{b["num"]}  {plain(b["title"])}', style='Heading 3')
    elif t == 'p':
        add_rich(doc.add_paragraph(), b['text'])
    elif t in ('numbers', 'bullets'):
        for k, item in enumerate(b['items']):
            p = doc.add_paragraph(style='Daftar Bernomor')
            p.paragraph_format.tab_stops.add_tab_stop(Pt(18))
            add_rich(p, (f'{b.get("start", 1) + k}.' if t == 'numbers' else '•') + '\t' + item)
        doc.paragraphs[-1].paragraph_format.space_after = Pt(6)
    elif t == 'figure':
        figure_block(b)
    elif t == 'table':
        table_block(b)
    elif t == 'refs':
        for r in b['items']:
            add_rich(doc.add_paragraph(style='Pustaka'), r)
    elif t == 'plainfig':
        p = doc.add_paragraph(style='Gambar')
        path = jpg(b['path'])
        w, h = pic_size(path, TW, 590)
        p.add_run().add_picture(path, width=Pt(w), height=Pt(h))
        doc.add_paragraph(b['caption'], style='Normal').alignment = WD_ALIGN_PARAGRAPH.CENTER

# Word refreshes the contents and lists (page numbers) when the file is opened
settings = doc.settings.element
uf = OxmlElement('w:updateFields'); uf.set(qn('w:val'), 'true')
compat = settings.find(qn('w:compat'))
if compat is not None:
    compat.addprevious(uf)              # schema order: ... updateFields, hdrShapeDefaults, footnotePr, endnotePr, compat ...
else:
    settings.append(uf)
zoom = settings.find(qn('w:zoom'))
if zoom is not None and zoom.get(qn('w:percent')) is None:
    zoom.set(qn('w:percent'), '100')
doc.core_properties.title = 'Laporan Analisis DA Gelar Rasa 2026'
doc.core_properties.author = CFG['team']
doc.save(OUT)
print(OUT)
