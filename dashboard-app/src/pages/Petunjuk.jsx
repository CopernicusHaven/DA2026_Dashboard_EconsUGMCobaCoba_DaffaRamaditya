import katex from 'katex';
import 'katex/dist/katex.min.css';
import { useDash } from '../lib/DashContext.js';
import { nf } from '../lib/engine.js';
import { POL } from '../lib/constants.js';

// Every unit, conversion and definition used in the dashboard and the analysis (analysis/01–03),
// in one place. Nothing here is new data: values come from the scripts and the conversion table.
const ISPU = [
  ['Baik', '0–50', '0–15,5', '0–50', '0–52', '0–4.000', '0–120', '0–80'],
  ['Sedang', '51–100', '15,5–55,4', '50–150', '52–180', '4.000–8.000', '120–235', '80–200'],
  ['Tidak Sehat', '101–200', '55,4–150,4', '150–350', '180–400', '8.000–15.000', '235–400', '200–1.130'],
  ['Sangat Tidak Sehat', '201–300', '150,4–250,4', '350–420', '400–800', '15.000–30.000', '400–800', '1.130–2.260'],
  ['Berbahaya', '>300', '>250,4', '>420', '>800', '>30.000', '>800', '>2.260'],
];
const BM = [
  ['PM2.5', '–', '–', '55', '15', '15 / 5'],
  ['PM10', '–', '–', '75', '40', '45 / 15'],
  ['SO₂', '150', '–', '75', '45', '–'],
  ['NO₂', '200', '–', '65', '50', '– / 10'],
  ['CO', '10.000', '4.000', '–', '–', '–'],
  ['O₃', '150', '100', '–', '35', '–'],
];

const Tbl = ({ head, rows, num = 1 }) => (
  <div className="tbl-wrap">
    <table className="t">
      <thead><tr>{head.map((h, i) => <th key={i} className={i >= num ? 'num' : ''}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className={j >= num ? 'num' : ''}>{c}</td>)}</tr>)}</tbody>
    </table>
  </div>
);
const Item = ({ t, children }) => <div className="g-item"><dt>{t}</dt><dd>{children}</dd></div>;

// equations typeset by KaTeX (LaTeX), like a math editor
const M = ({ m, note }) => <><span className="eq" dangerouslySetInnerHTML={{ __html: katex.renderToString(m, { displayMode: true, throwOnError: false }) }} />{note && <span className="eq-note">{note}</span>}</>;
const EQS = {
  lengkap: String.raw`\textit{Kelengkapan} = \dfrac{\textit{Jumlah jam berdata}}{\textit{Jumlah seluruh jam pada periode tersebut}} \times 100`,
  ppm: String.raw`\mu\text{g/m}^3 = \dfrac{\text{ppm} \times M \times 1000}{24{,}45}`,
  jam: String.raw`\bar{x}_{\textit{jam}} = \dfrac{\displaystyle\sum_{i=1}^{n} x_i}{n}`,
  hari: String.raw`\bar{x}_{\textit{hari}} = \dfrac{\displaystyle\sum_{j=1}^{n} \bar{x}_{\textit{jam},\,j}}{n}`,
  stasiun: String.raw`\bar{x}_{\textit{stasiun}} = \dfrac{\displaystyle\sum_{k=1}^{N} x_{\textit{jam},\,k}}{N}`,
  delapan: String.raw`\bar{x}_{\textit{8 jam}}(t) = \dfrac{\displaystyle\sum_{k=t-7}^{t} x_k}{n}`,
  ieu: String.raw`\textit{Ieu} = \dfrac{\dfrac{\text{NO}_2}{40} + \dfrac{\text{SO}_2}{20}}{2}`,
  iku: String.raw`\textit{IKU} = 100 - \dfrac{50}{0{,}9}\left(\textit{Ieu} - 0{,}1\right)`,
  kritis: String.raw`\textit{Skor} = \dfrac{P_{\textit{PM2.5 rata-rata}} + P_{\textit{\% hari > baku mutu}} + P_{\textit{persentil 98}} + P_{\textit{hari tidak sehat}}}{4} \times 100`,
  r: String.raw`\bar{r} = \dfrac{\displaystyle\sum_{s=1}^{n} r_s}{n}`,
  beta: String.raw`\left(e^{\beta} - 1\right) \times 100`,
  atribusi: String.raw`\textit{Kasus teratribusi} = \textit{Jumlah kasus} \times \left(1 - \dfrac{1}{\textit{RR}}\right)`,
  prioritas: String.raw`\textit{Skor} = \dfrac{\begin{gathered} 0{,}25 \times \textit{Polusi} + 0{,}20 \times \textit{Kabut asap} + 0{,}20 \times \textit{Beban rumah sakit} \\ +\, 0{,}20 \times \textit{Defisit data} + 0{,}15 \times \textit{Keterisolasian} \end{gathered}}{\textit{Jumlah bobot komponen yang tersedia}} \times 100`,
};

export default function Petunjuk() {
  const { E } = useDash();
  return (
    <>
      <div className="phead">
        <h1>Petunjuk Pengukuran</h1>
      </div>

      <div className="guide">
        <section className="card sect">
          <h3 className="card-t">Satuan</h3>
          <dl className="g-list">
            <Item t="µg/m³">Mikrogram polutan per meter kubik udara.</Item>
            <Item t="Hari-Stasiun">Satu stasiun pada satu hari.</Item>
            <Item t="Kelengkapan Data (%)">
              <M m={EQS.lengkap} />
            </Item>
          </dl>
        </section>

        <section className="card sect">
          <h3 className="card-t">Konversi Satuan</h3>
          <p className="g-p">Digunakan untuk data yang tercatat dalam satuan ppm.</p>
          <M m={EQS.ppm} />
          <Tbl head={['Parameter', 'Basis ppm', 'M (g/mol)', 'Faktor per ppm']} rows={E.D.conversion.map(r => [POL[r.parameter], r.basis_ppm, nf(r.massa_molar_g_per_mol, 3), nf(r.faktor_ug_m3_per_ppm, 1)])} num={2} />
        </section>

        <section className="card sect">
          <h3 className="card-t">Pengolahan Data</h3>
          <dl className="g-list">
            <Item t="Per Jam">
              <M m={EQS.jam} note="n ≥ 3 dari 4 data 15 menit" />
            </Item>
            <Item t="Harian">
              <M m={EQS.hari} note="n ≥ 18 dari 24 jam" />
            </Item>
            <Item t="Rata-Rata Stasiun">
              <M m={EQS.stasiun} note="N = jumlah jam valid pada filter aktif, minimal 10 hari" />
            </Item>
            <Item t="CO dan O₃ 8 Jam">
              <M m={EQS.delapan} note="n ≥ 6 jam valid, lalu diambil nilai maksimum hariannya" />
            </Item>
          </dl>
        </section>

        <section className="card sect">
          <h3 className="card-t">Indeks Kualitas Udara</h3>
          <dl className="g-list">
            <Item t="ISPU Harian">Sub-indeks tertinggi dari enam polutan (Permen LHK 14/2020).</Item>
            <Item t="IKU">Rata-rata tahunan NO₂ dan SO₂.
              <M m={EQS.ieu} />
              <M m={EQS.iku} />
            </Item>
          </dl>
        </section>

        <section className="card sect wide">
          <h3 className="card-t">Batas Kategori ISPU (µg/m³)</h3>
          <Tbl head={['Kategori', 'ISPU', 'PM2.5 24 jam', 'PM10 24 jam', 'SO₂ 24 jam', 'CO 8 jam', 'O₃ 1 jam', 'NO₂ 1 jam']} rows={ISPU} />
        </section>

        <section className="card sect wide">
          <h3 className="card-t">Baku Mutu dan Pedoman WHO (µg/m³)</h3>
          <Tbl head={['Polutan', '1 jam', '8 jam', '24 jam', 'Tahunan', 'WHO 24 jam / tahunan']} rows={BM} />
        </section>

        <section className="card sect">
          <h3 className="card-t">Identifikasi</h3>
          <dl className="g-list">
            <Item t="Kejadian Kabut Asap">Minimal 3 hari berturut-turut dengan PM2.5 harian &gt;55,4 µg/m³ dan &gt;2× median PM2.5.</Item>
            <Item t="Skor Wilayah Kritis">
              <M m={EQS.kritis} note="P = peringkat persentil (0–1)" />
            </Item>
          </dl>
        </section>

        <section className="card sect">
          <h3 className="card-t">Faktor Penyebab</h3>
          <dl className="g-list">
            <Item t="Spearman (ρ)">Kekuatan korelasi berdasarkan peringkat.</Item>
            <Item t="Korelasi Cuaca">Rata-rata Spearman <i>r</i> per jam.
              <M m={EQS.r} />
            </Item>
            <Item t="R²">Variasi PM2.5 harian dalam model Random Forest.</Item>
            <Item t="Kepentingan Faktor">Penurunan R² ketika faktor diacak.</Item>
          </dl>
        </section>

        <section className="card sect">
          <h3 className="card-t">Dampak Kesehatan</h3>
          <dl className="g-list">
            <Item t="Kenaikan Persentase per 10 µg/m³"><M m={EQS.beta} /></Item>
            <Item t="Lag">Jeda hari setelah paparan.</Item>
            <Item t="95% CI">Rentang ketidakpastian.</Item>
            <Item t="Risiko Relatif (RR)">Perbandingan jumlah kasus terhadap hari berkategori Baik.</Item>
            <Item t="Kasus Teratribusi"><M m={EQS.atribusi} /></Item>
            <Item t="Uji Beda (z)">Perbandingan balita dengan lansia.</Item>
          </dl>
        </section>

        <section className="card sect wide">
          <h3 className="card-t">Sebaran Stasiun</h3>
          <dl className="g-list">
            <Item t="Jarak Antarstasiun">Jarak garis lurus (km) dari koordinat stasiun dalam dataset.</Item>
          </dl>
          <p className="g-sub">Keandalan Alat</p>
          <dl className="g-list">
            <Item t="Baik">Beroperasi normal dengan kelengkapan data ≥75%.</Item>
            <Item t="Perlu Penyesuaian">Beroperasi tidak menentu atau memerlukan konversi satuan.</Item>
            <Item t="Buruk">Kelengkapan data &lt;75%.</Item>
            <Item t="Kritis">Rusak atau kelengkapan data &lt;50%.</Item>
          </dl>
          <p className="g-sub">Skor Prioritas (0–100)</p>
          <dl className="g-list">
            <Item t="Rumus">Rata-rata komponen dari polusi (25%), kabut asap (20%), beban rumah sakit (20%), defisit data (20%), dan keterisolasian (15%).
              <M m={EQS.prioritas} />
            </Item>
          </dl>
        </section>

        <section className="card sect wide">
          <h3 className="card-t">Keterangan</h3>
          <dl className="g-list">
            <Item t="PM2.5">Partikel halus berdiameter kurang dari 2,5 µm.</Item>
            <Item t="PM10">Partikel berdiameter kurang dari 10 µm.</Item>
            <Item t="SO₂">Sulfur dioksida.</Item>
            <Item t="CO">Karbon monoksida.</Item>
            <Item t="O₃">Ozon permukaan.</Item>
            <Item t="NO₂">Nitrogen dioksida.</Item>
            <Item t="M">Massa molar (g/mol).</Item>
            <Item t="β">Koefisien model quasi-Poisson per 10 µg/m³, dengan kontrol tren waktu, suhu, kelembapan, hari, dan rumah sakit.</Item>
            <Item t="Skala IKU">
              <span className="g-rows">
                <span>Sangat Baik (≥90)</span><span>Baik (70–90)</span><span>Sedang (50–70)</span><span>Kurang (25–50)</span><span>Sangat Kurang (&lt;25)</span>
              </span>
            </Item>
          </dl>
        </section>
      </div>
    </>
  );
}
