import type { Translations } from './types'

type ThreadCopy = Translations['assistant']['thread']

// Fallback lapisan kartu error (lib/error-surface-copy.ts): dipakai saat kode kegagalan tidak punya entri sendiri.
export const idErrorLayers: Pick<ThreadCopy, 'errorLayerBodies' | 'errorLayers'> = {
  errorLayers: {
    auth: 'Masalah login',
    billing: 'Kredit habis',
    disk: 'Disk penuh',
    endpoint: "Tidak bisa menjangkau server model kamu",
    gateway: "Tidak bisa mengirim pesan kamu",
    generic: "Thor tidak bisa menyelesaikan balasan ini",
    provider: 'Layanan AI mengembalikan error',
    runtime: 'Thor mengalami masalah',
    streaming: 'Balasan terpotong'
  },
  errorLayerBodies: {
    auth: 'Layanan AI menolak login kamu. Periksa kredensial untuk provider ini, lalu kirim ulang pesan kamu.',
    billing: 'Akun kamu tidak punya kredit tersisa untuk provider ini. Isi ulang atau ganti provider, lalu kirim lagi.',
    disk: 'Disk kamu penuh, jadi Thor tidak bisa menyimpan percakapan ini. Kosongkan sebagian ruang, lalu coba lagi.',
    endpoint: "Thor tidak bisa menjangkau server model kustom kamu. Pastikan servernya berjalan, lalu kirim ulang pesan kamu.",
    gateway:
      'Thor mengalami masalah internal saat memulai balasan ini. Kirim ulang pesan kamu; kalau terus terjadi, kirim diagnostik.',
    generic: 'Ada yang salah saat Thor membalas. Coba lagi, atau salin detailnya kalau terus terjadi.',
    provider: 'Layanan AI tidak bisa menyelesaikan permintaan ini. Coba lagi sebentar atau ganti provider.',
    runtime:
      'Thor mengalami masalah internal saat memulai balasan ini. Kirim ulang pesan kamu; kalau terus terjadi, kirim diagnostik.',
    streaming: 'Koneksi terputus sebelum balasan selesai. Coba lagi untuk mengirim ulang.'
  }
}
