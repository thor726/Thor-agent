---
title: ThorHub — Beli Token AI untuk Thor
---

# ThorHub

ThorHub adalah toko token AI di **https://llm.thormarket.site**.
Pembeli mendapat Sub-API Key (`sk-thor-...`) dengan kuota token, dan
memakainya lewat API yang kompatibel dengan OpenAI di
`https://llm.thormarket.site/v1`.

ThorHub adalah **dagangan berbayar, bukan gratis**. Untuk pemakaian
gratis, pembeli memilih provider gratis langsung saat setup Thor
(misalnya provider gratis yang mereka punya key-nya sendiri).

## Beli dan top-up

- Toko: https://llm.thormarket.site/beli
- Paket: 10 juta token Rp 5.000, 20 juta Rp 10.000, 50 juta Rp 25.000,
  100 juta Rp 48.000, 200 juta Rp 93.000, 500 juta Rp 225.000,
  1 miliar Rp 435.000 (cek harga terbaru di toko, karena harga dapat
  berubah).
- Bayar via QRIS dengan jumlah persis = harga paket + kode unik
  Rp 1–999. Jangan tutup halaman sampai selesai.
- Key baru muncul di halaman dan dikirim ke email pembeli.
  Masa aktif key 25 hari sejak diterbitkan.
- Top-up key lama: tab "Top-up Key Saya" di halaman /beli, atau
  https://llm.thormarket.site/beli/topup. Kuota ditambahkan ke key
  yang sama dan masa aktif diperpanjang 25 hari.
- Konfirmasi pembayaran otomatis bergantung pada ponsel admin +
  MacroDroid yang sedang online. Pembayaran kurang dari jumlah yang
  diminta tidak otomatis terkonfirmasi dan perlu konfirmasi manual admin.

## Memakai key ThorHub di Thor

Setiap pembeli mengatur Thor-nya sendiri lewat full setup Thor
(`thor setup`). Tidak ada settingan bawaan yang disalin dari
instalasi orang lain — pembeli memilih provider, model, dan key
mereka sendiri.

Untuk memakai ThorHub sebagai salah satu provider:

1. Beli paket di https://llm.thormarket.site/beli dan simpan key
   `sk-thor-...` milik sendiri.
2. Di Thor, tambahkan provider custom (OpenAI-compatible) dengan:
   - `base_url: https://llm.thormarket.site/v1`
   - API key: key ThorHub milik sendiri.
3. Ganti provider/model dengan `/model` di dalam sesi Thor, sesuai
   pilihan sendiri.

## Cek saldo

Buka https://llm.thormarket.site/portal dan login dengan key ThorHub
milik sendiri. Terlihat sisa kuota (`tokens_remaining`) dan sisa masa
aktif key. Di Thor, perintah `/saldo` menjelaskan cara ini. Bila key ThorHub sudah
terpasang di Thor, `/topup` menampilkan sisa kuota langsung.

## Jangan

- Jangan menempel key `sk-thor-...` di Discord, DM, atau chat apa pun.
  Key hanya ditempel di halaman web ThorHub atau di file `.env` Thor
  milik sendiri.
- Jangan meminta key orang lain untuk dicekkan.
