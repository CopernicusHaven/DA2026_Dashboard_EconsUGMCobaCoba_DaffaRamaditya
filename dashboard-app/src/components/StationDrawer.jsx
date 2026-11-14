import { memo, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import EChart from './EChart.jsx';
import { useDash } from '../lib/DashContext.js';
import { ax, sparseLine, tipRow } from '../lib/chartBase.js';
import { nf, pct } from '../lib/engine.js';
import { CAT_S, ISPU_C, ISPU_L, SERIES, INK2 } from '../lib/constants.js';
import { Tag } from './ui.jsx';
import Icon from './Icon.jsx';

function Body({ code }) {
  const { E, F, agg, theme, closeStation } = useDash();
  const s = E.SM[code], d = E.D.daily[code], dur = E.D.diurnal[code];
  const m = agg.stMean(code, 'pm25'), cats = agg.catCounts(code);
  const tot = cats.reduce((a, b) => a + b, 0);
  const haze = useMemo(() => { let h = 0; for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i] && d.haze[i]) h++; return h; }, [code, agg]); // eslint-disable-line
  const hosp = E.HOSP.find(h => h.station === code);
  const hz = hosp ? agg.hazeStats([hosp.id]) : null;
  const iku = E.D.annual.find(r => r.station === code && r.year === 2025);
  const relKind = s.reliability === 'Baik' ? 'ok' : s.reliability === 'Perlu standardisasi' ? 'warn' : 'bad';

  const spark = useMemo(() => {
    const idx = []; for (let i = F.d0; i <= F.d1; i++) idx.push(i);
    return {
      grid: { left: 40, right: 12, top: 16, bottom: 26 }, toolbox: false,
      tooltip: { trigger: 'axis', formatter: ps => `<b>${E.fmtDay(E.idxOf(ps[0].axisValue))}</b>` + tipRow(SERIES[0], 'PM2.5', ps[0].value == null ? '–' : nf(ps[0].value, 1) + ' µg/m³') },
      xAxis: ax({ type: 'category', data: idx.map(i => E.DAY_S[i]), boundaryGap: false, name: 'Bulan', axisLabel: { color: INK2, fontSize: 11, formatter: v => v.slice(0, 7) } }),
      yAxis: ax({ type: 'value', name: 'µg/m³' }),
      series: [{ type: 'line', symbol: 'none', showAllSymbol: true, lineStyle: { width: 1.4, color: SERIES[0] }, itemStyle: { color: SERIES[0] }, areaStyle: { color: SERIES[0], opacity: 0.12 },
        data: sparseLine(idx.map(i => agg.mask[i] ? d.pm25[i] : null)),
        markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: 'Baku mutu 24 jam (55 µg/m³)', position: 'insideEndTop' }, data: [{ yAxis: 55 }] } }],
    };
  }, [code, F.d0, F.d1, agg, theme]); // eslint-disable-line

  const diur = useMemo(() => dur ? ({
    grid: { left: 40, right: 12, top: 30, bottom: 24 }, toolbox: false, legend: { top: 0, left: 0, itemWidth: 14, itemHeight: 3, textStyle: { fontSize: 11, color: INK2 } },
    tooltip: { trigger: 'axis', formatter: ps => `<b>Pukul ${String(ps[0].axisValue).padStart(2, '0')}.00</b>` + ps.map(p => tipRow(p.color, p.seriesName, nf(p.value, 1))).join('') },
    xAxis: ax({ type: 'category', data: [...Array(24).keys()], boundaryGap: false, name: 'Jam (WIB)', axisLabel: { interval: 3, color: INK2, fontSize: 11 } }), yAxis: ax({ type: 'value', name: 'µg/m³', scale: true }),
    series: [{ name: 'PM2.5', type: 'line', symbol: 'none', lineStyle: { color: SERIES[0], width: 2 }, itemStyle: { color: SERIES[0] }, data: dur.pm25 },
      { name: 'NO₂', type: 'line', symbol: 'none', lineStyle: { color: SERIES[1], width: 2 }, itemStyle: { color: SERIES[1] }, data: dur.no2 }],
  }) : null, [code, theme]); // eslint-disable-line

  const kota = s.kota_kabupaten.replace('Kota Administrasi ', 'Kota ');
  const REL = { 'Baik': 'Berfungsi baik', 'Perlu standardisasi': 'Perlu penyesuaian', 'Buruk - perlu kalibrasi/perawatan': 'Perlu kalibrasi', 'Kritis - ganti/perbaiki': 'Perlu diganti' };
  const OPS = { Active: 'Aktif', Intermittent: 'Sering mati', Defective: 'Rusak' };
  return (
    <>
      <div className="drawer-h">
        <h3>{kota} ({s.station})</h3>
        <button className="icon-btn" onClick={closeStation} aria-label="Tutup"><Icon name="x" size={16} /></button>
      </div>
      {!s.used_in_analysis ? (
        <div className="answer">Sensor stasiun ini <b>rusak</b> (hanya 0,5% jam valid) sehingga tidak dianalisis dan datanya tidak diganti.</div>
      ) : (
        <>
          <div className="mini-kpis">
            <div><span>PM2.5 Rata-Rata</span><b>{nf(m.mean, 1)}</b><small>µg/m³, {nf(m.mean / 15, 1)}× baku mutu</small></div>
            <div><span>Hari Tidak Sehat</span><b>{pct(tot ? (cats[2] + cats[3] + cats[4]) / tot * 100 : null, 0)}</b><small>dari {tot} hari</small></div>
            <div><span>Hari Berkabut</span><b>{haze}</b><small>hari</small></div>
            <div><span>Tren 2024 ke 2026</span><b>{pct(s.chg_2024_2026_pct, 0, true)}</b><small>{s.trend_overall}</small></div>
          </div>
          <section className="dsec"><h4>PM2.5 Harian</h4>
          <EChart option={spark} height={170} ariaLabel={'PM2.5 harian ' + code} /></section>
          <section className="dsec"><h4>Kategori ISPU</h4>
          <div className="ispu-bar">
            {cats.map((c, k) => c > 0 && <motion.i key={k} style={{ background: ISPU_C[k] }} initial={{ width: 0 }} animate={{ width: `${c / tot * 100}%` }} transition={{ duration: 0.7, delay: k * 0.05 }} title={`${ISPU_L[k]}: ${pct(c / tot * 100, 1)}`} />)}
          </div>
          <div className="legend-inline">{ISPU_L.map((l, k) => cats[k] > 0 && <span key={k}><i style={{ background: ISPU_C[k] }} />{l} {pct(cats[k] / tot * 100, 0)}</span>)}</div></section>
          {diur && <section className="dsec"><h4>Pola per Jam</h4><EChart option={diur} height={170} ariaLabel={'Pola harian ' + code} /></section>}
        </>
      )}
      <section className="dsec"><h4>Lokasi</h4>
      <dl className="facts">
        <dt>Wilayah</dt><dd>{s.kecamatan}, {s.provinsi}</dd>
        <dt>Tipe Lokasi</dt><dd>{CAT_S[s.site_category]}</dd>
        <dt>Lalu Lintas</dt><dd>{nf(s.traffic_intensity_per_h, 0)} kendaraan/jam</dd>
        <dt>Jarak ke Jalan</dt><dd>{nf(s.distance_to_road_m, 0)} m</dd>
        <dt>Stasiun Terdekat</dt><dd>{s.nearest_station}, {nf(s.nn_distance_km, 0)} km</dd>
      </dl></section>
      <section className="dsec"><h4>Alat</h4>
      <dl className="facts">
        <dt>Sensor</dt><dd>{s.model_sensor}</dd>
        <dt>Tindakan</dt><dd>{s.aksi_alat}</dd>
        <dt>Skor Prioritas</dt><dd>{nf(s.priority_score, 1)} dari 100</dd>
        {iku && <><dt>IKU 2025</dt><dd>{nf(iku.IKU, 1)} ({iku.IKU_kategori})</dd></>}
      </dl></section>
      {hosp && (
        <section className="dsec">
          <h4>Rumah Sakit</h4>
          <dl className="facts">
            <dt>Nama</dt><dd>{s.nama_rumah_sakit} ({hosp.id})</dd>
            <dt>Kelas</dt><dd>{s.kelas_faskes}</dd>
            <dt>Tempat Tidur</dt><dd>{nf(s.kapasitas_tempat_tidur, 0)}</dd>
            {hz && hz.n > 0 && <><dt>Saat Kabut Asap</dt><dd>ISPA balita {pct(hz.pct.resp_admissions_under5, 0, true)}, ISPA lansia {pct(hz.pct.resp_admissions_over60, 0, true)}, kematian {pct(hz.pct.death, 0, true)}</dd></>}
          </dl>
        </section>
      )}
    </>
  );
}

export default memo(function StationDrawer({ code }) {
  const { closeStation } = useDash();
  return (
    <AnimatePresence>
      {code && (
        <>
          <motion.div key="scrim" className="scrim" onClick={closeStation} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.aside key="drawer" className="drawer" role="dialog" aria-label={'Detail stasiun ' + code}
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 300, damping: 34 }}>
            <Body code={code} />
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
});
