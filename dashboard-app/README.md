# DA2026 Dashboard — Gelar Rasa 2026

Web app interaktif (Vite + React) untuk case study Dashboard Analysis Gelar Rasa 2026: kualitas udara 27 stasiun AQMS dan dampaknya pada kesehatan 27 rumah sakit rujukan, 1 Jan 2024 – 14 Okt 2026.

## Teknologi

| Bagian | Pustaka | Versi |
|---|---|---|
| Framework | React | 19.3.1 |
| Build tool | Vite | 8.3.5 |
| Grafik | ECharts | 6.1.0 |
| Peta | Leaflet + react-leaflet | 1.9.4 / 5.0.0 |
| Animasi & transisi halaman | Framer Motion | 14.9.0 |
| Font | Plus Jakarta Sans (self-hosted) | 5.3.0 |

Semua versi dipatok persis.

Hasil build berupa **situs statis** (`dist/`), jadi tidak butuh server dan bisa di-hosting gratis di GitHub Pages, Netlify, atau Vercel.

## Data

`public/data/dashboard.json` dibuat oleh `../analysis/06_dashboard_data.py`. File ini hanya membentuk ulang data bersih dan hasil analisis di `../output/`, yang semuanya berasal dari 33 file dataset panitia. Tidak ada data eksternal, dan tidak ada nilai yang diimputasi.

Peta dasar (Esri / OpenStreetMap) hanya berfungsi sebagai latar visual, bukan data analisis.

## Menjalankan

```bash
npm install
npm run dev        # http://127.0.0.1:5173
npm run build      # hasil di dist/
npm run preview    # uji hasil build di http://127.0.0.1:4173
```

Jika data analisis berubah, jalankan ulang skrip berikut lalu build ulang:

```bash
python3 ../analysis/06_dashboard_data.py
```

## Fitur interaktif

- 7 halaman yang mengikuti alur Tujuan 1–5, ditambah Ringkasan serta Data & Metode.
- Transisi antarhalaman berupa tirai bermerek Gelar Rasa, dengan konten yang bergeser dan blur.
- Pil tab aktif beranimasi, dan kartu muncul secara bertahap.
- Filter global yang memengaruhi semua halaman: pulau, tipe lokasi, stasiun (pilih 1–6 untuk membandingkan), periode (preset atau kustom), dan musim.
- Klik stasiun di peta, grafik, atau tabel untuk membuka panel detail. Dari panel itu, semua halaman bisa difokuskan ke stasiun tersebut.
- KPI dengan angka beranimasi, tooltip di semua grafik, zoom/slider pada deret waktu, tabel yang bisa diurutkan, serta tampilan tabel dan unduhan PNG di setiap grafik.
- Navigasi lewat tombol ← → di keyboard, geser layar (perangkat sentuh), titik halaman, dan tombol sebelumnya/berikutnya.
- **Mode cerita**: halaman berganti otomatis untuk presentasi.
- Responsif di ponsel (filter bisa dilipat) dan menghormati pengaturan *reduce motion*.

## Publikasi (link bisa dibuka juri tanpa izin)

Nama link wajib mengikuti format handbook: `DA2026_Dashboard_NamaTim_NamaKetua`.

Logo Gelar Rasa sudah tercantum di header.

### GitHub Pages

1. Buat repo **publik** bernama `DA2026_Dashboard_NamaTim_NamaKetua`.
2. Jalankan `npm run build`.
3. Unggah isi folder `dist/` ke branch `gh-pages`.
4. Aktifkan Pages dari branch tersebut.

Hasilnya: `https://<user>.github.io/DA2026_Dashboard_NamaTim_NamaKetua/`

### Netlify

Seret folder `dist/` ke app.netlify.com/drop, lalu ubah nama situs.

### Vercel

`npx vercel` dari folder ini. Pengaturan: framework Vite, output `dist`.

Setelah online, buka link di jendela *incognito* untuk memastikan link bisa diakses tanpa login.
