# Audit Kepatuhan — Booklet, Handbook & Rekap QnA DA Gelar Rasa 2026
*Diperiksa ulang 13 Nov 2026 dengan `analysis/05_audit.py`. Hasil mesin lengkap ada di `output/audit/audit_checks.csv` (41 pemeriksaan, semuanya lulus; dashboard sudah dibangun tetapi belum dipublikasikan).*

## A. Aturan "tidak menambah data" & integritas file asli

| Pemeriksaan | Status | Bukti |
|---|---|---|
| 33 file asli tidak diubah | ✅ | MD5 identik 33/33 dengan unduhan asli |
| Hanya dataset panitia yang dipakai (Handbook F) | ✅ | Skrip hanya membaca 33 file panitia; baku mutu/WHO/IKU adalah acuan, bukan dataset |
| Tidak ada jam/baris data baru | ✅ | 655.808 jam bersih, semuanya ada di file asli; 3.632 jam hilang MDN-01 tidak diisi |
| Tidak ada nilai rekaan/imputasi | ✅ | 5.878.268 nilai dicek satu per satu = nilai asli (× faktor ppm untuk 3 stasiun) |
| Tidak ada stasiun pengganti/proksi | ✅ | RS-XXX-27 tanpa paparan; JMB-02 tanpa nilai pinjaman |
| Angka kesehatan tidak diubah | ✅ | 27.486 baris identik (hanya 5 baris 2023-12-31 di luar periode yang dibuang) |
| Laporan tanpa fakta dari luar dataset | ✅ | Celah jaringan dihitung dari koordinat stasiun saja |

Catatan: baris yang **dibuang** (timestamp rusak JMB-02, data kesehatan 2023-12-31) dan nilai yang **dikosongkan** (QC tidak valid, sentinel, sensor macet) adalah pengurangan, bukan penambahan. Semuanya tercatat di `cleaning_log`.

## B. Rekap QnA

| Butir QnA | Status | Penerapan |
|---|---|---|
| Q1: rumus konversi ppm → µg/m³ ditentukan peserta | ✅ | Satu rumus: µg/m³ = ppm × M × 1000 / 24,45 (25 °C, 1 atm) |
| Q3: PM tidak bisa memakai berat molekul gas; asumsi boleh asal ilmiah, konsisten, dijelaskan | ✅ | PM diperlakukan sebagai ppm **massa** (M udara 28,97 ≈ densitas udara), gas sebagai ppm volume. Dasar ilmiah dan sensitivitas (×1000 → −16%) dijelaskan di subbab 2.3.1 + tabel `unit_conversion_ppm` |
| Q2: `resp_admissions_over60` = ISPA lansia; `resp` = pernapasan umum semua umur & jenis | ✅ | Label dan interpretasi diperbarui; 92 baris `resp` < balita+lansia ditandai, tidak diubah |

## C. Case study booklet (Tujuan & acuan)

| Tujuan / ketentuan | Status | Di mana |
|---|---|---|
| T1 Banding antarstasiun & antarpulau | ✅ | 3.1.1, Gambar 3.1 |
| T1 Evaluasi vs baku mutu nasional PP 22/2021 | ✅ *diperluas* | Tahunan per tahun kalender, 24 jam, 8 jam, 1 jam |
| T1 Kategori ISPU (Permen LHK 14/2020) | ✅ | ISPU harian, Gambar 3.2 |
| T1 Penilaian IKU (Permen LHK 27/2021) | ✅ *baru* | Tabel IKU per stasiun/tahun (lihat catatan D.4) |
| T1 Pedoman kesehatan | ✅ | WHO AQG 2021 |
| T1 Tren perbaikan/pemburukan | ✅ | Gambar 3.3 |
| T2 Pola jam, hari kerja vs akhir pekan, musim | ✅ | 3.1.2 |
| T2 Episode kabut asap karhutla/gambut | ✅ | 84 episode, Gambar 3.6 |
| T2 Beda kawasan perkotaan, industri, latar bersih | ✅ *baru* | Tabel 3.1 |
| T3 Suhu, kelembapan, kecepatan & arah angin, lalu lintas, jarak jalan, tipe lokasi → faktor terkuat | ✅ *diperluas ke 6 polutan* | 3.1.3 |
| T4 PM2.5 vs ISPA, asma, PPOK, kardiovaskular, kematian + efek jeda + balita vs lansia | ✅ | 3.1.4 |
| T5 Kecukupan jaringan & wilayah prioritas | ✅ | 3.1.5 |
| T6 Dashboard interaktif, komunikatif, *storytelling* | ✅ dibangun / ⏳ belum online | `dashboard-app/` (React + Vite), 7 halaman, logo Gelar Rasa |
| 33 file dipakai | ✅ | `metadata_sensors.csv` kini dipakai untuk validasi kategori QC |
| Pemetaan stasiun–sensor–RS (bagian E) | ✅ | 27/27 cocok |

## D. Handbook & template laporan — yang masih harus dikerjakan

1. **Dashboard sudah dibangun tetapi belum online.**
   - Logo resmi Gelar Rasa sudah tercantum di header.
   - Langkah berikutnya: publikasikan sebagai link publik (GitHub Pages, Netlify, atau Vercel) bernama `DA2026_Dashboard_NamaTim_NamaKetua` yang bisa dibuka **tanpa meminta akses**, lalu isi nama tim dan ketua di footer.
2. **Laporan masih draf Markdown.** Pindahkan ke salinan template Google Docs, lalu:
   - format: Times New Roman 12, spasi 1,15, rata kanan-kiri, A4;
   - isi sampul dan daftar isi/tabel/gambar;
   - isi subbab 2.4, 3.2 (tangkapan layar dashboard), 3.3 (pembahasan tiap visual), dan link di Lampiran A;
   - simpan sebagai `DA2026_Laporan_NamaTim_NamaKetua.pdf`.
3. **Batas 20 halaman (Bab I–IV) berisiko terlampaui.**
   - Draf saat ini ±3.800 kata, 20 tabel, dan 12 gambar, atau sekitar 17–20 halaman sebelum bagian dashboard ditambahkan.
   - Saran: pindahkan Gambar 3.2, 3.5, 3.8, dan 3.12 serta Tabel 2.1 versi lengkap ke Lampiran. Lampiran tidak dihitung.
4. **Penomoran tabel:** baru 4 dari 20 tabel yang bernomor. Beri nomor dan judul pada semua tabel agar Daftar Tabel lengkap.
5. **Rumus IKU:** dipakai rumus IKU KLHK, yaitu Ieu = ((NO₂/40) + (SO₂/20))/2 dan IKU = 100 − (50/0,9)(Ieu − 0,1), dengan kategori Sangat Baik ≥90, Baik ≥70, Sedang ≥50, Kurang ≥25. **Cocokkan dengan lampiran Permen LHK 27/2021** sebelum dikumpulkan.
6. **Tenggat: 14 November 2026 pukul 23.59 WIB** melalui bit.ly/PreliminarySubmissionDAGelarRasa2026. Terlambat berarti diskualifikasi.
