import type { FirstRunCopy } from './types_first_run'

export const idFirstRun: FirstRunCopy = {
  beats: {
    name: 'Nama',
    theme: 'Warna aksen',
    layout: 'Tata letak',
    connectors: 'Aplikasi',
    plugins: 'Plugin',
    tour: 'Tur',
    build: 'Tugas pertama'
  },
  namePlaceholder: 'Nama kamu',
  useName: name => `Pakai “${name}”`,
  install: 'Install',
  installed: 'Terpasang',
  loading: 'Memuat…',
  noPlugins: 'Tidak ada plugin untuk ditampilkan saat ini.',
  noneChosen: 'Tidak ada',
  noAnswer: 'Tidak ada jawaban',
  answerRefused: 'Jawaban tidak diterima',
  tours: {
    quick: 'Tur singkat',
    full: 'Tunjukkan semuanya',
    skip: "Lewati, langsung kita bikin sesuatu"
  },
  skippedAll: 'Penyiapan dilewati',
  skip: 'Lewati penyiapan',
  skipTip: 'Akhiri penyiapan terpandu dan buka chat baru.',
  skipFailed: 'Tidak bisa melewati penyiapan',
  slashOffTitle: 'Slash command dimatikan selama penyiapan',
  slashOffBody: 'Berfungsi seperti biasa setelah penyiapan selesai.',
  localModel: {
    title: 'Komputer ini bisa menjalankan model secara lokal',
    text: (model, size) => `${model} (${size}) cocok dengan perangkat kamu. Berjalan gratis, dan chat kamu tetap di komputer ini.`,
    setUp: 'Siapkan',
    notNow: 'Nanti saja'
  },
  intro: {
    greeting: "Hai, saya Thor.",
    plan: "Kita siapkan dulu semuanya untuk kamu. Setelah itu kita kerjakan sesuatu yang keren."
  },
  rerun: {
    title: 'Jalankan onboarding lagi',
    description: 'Buka chat penyiapan baru yang memandu langkah first-run dengan model kamu saat ini.',
    action: 'Jalankan lagi',
    failed: 'Tidak bisa memulai onboarding'
  }
}
