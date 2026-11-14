# Dashboard Tableau DA2026: Cara Membuka dan Menerbitkan

Folder ini berisi versi Tableau dari dashboard DA2026. Data dan hasil analisisnya sama dengan versi web
(`dashboard-app`): seluruh berkas di `Data/` dibentuk dari `dashboard-app/public/data/dashboard.json`
tanpa tambahan data apa pun.

## Isi folder

| Berkas | Fungsi |
|---|---|
| `DA2026_Dashboard_EconsUGMCobaCoba_NamaKetua.twbx` | Workbook siap buka (workbook, data, dan logo dalam satu berkas) |
| `DA2026_Dashboard_EconsUGMCobaCoba_NamaKetua.twb` | Workbook tanpa data (membaca folder `Data/` dan `Images/`) |
| `Data/` | 22 berkas CSV untuk workbook |
| `build_data.py` | Membentuk ulang `Data/` dari `dashboard.json` |
| `build_workbook.py` | Membentuk ulang workbook dari `Data/` |

## Halaman

Ringkasan, Kondisi, Waktu Kritis, Penyebab, Kesehatan, Jaringan, dan Petunjuk Pengukuran.
Filter Pulau, Tipe Lokasi, Musim, dan Tahun berlaku di semua halaman.

## Langkah menerbitkan ke Tableau Public

1. Pasang **Tableau Public** (gratis) dari public.tableau.com, lalu masuk dengan akun Tableau Public.
2. Buka `DA2026_Dashboard_EconsUGMCobaCoba_NamaKetua.twbx` melalui **File > Open**.
3. Periksa setiap halaman (tab di bagian bawah).
4. Pilih **File > Save to Tableau Public As...**, beri judul
   `DA2026_Dashboard_NamaTim_NamaKetua` (ganti dengan nama tim dan nama ketua).
5. Setelah halaman Tableau Public terbuka, buka pengaturan viz:
   - aktifkan **Show Sheets as Tabs** agar juri dapat berpindah halaman;
   - pastikan viz **tidak disembunyikan** dari profil (harus dapat dibuka tanpa meminta akses).
6. Salin tautan viz untuk formulir pengumpulan dan lampiran laporan.

## Membentuk ulang

```bash
python3 build_data.py
python3 build_workbook.py
```
