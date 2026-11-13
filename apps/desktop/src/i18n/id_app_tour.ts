import type { Translations } from './types'

export const idAppTour: Translations['appTour'] = {
  sessions: { title: 'Chat kamu', text: 'Setiap percakapan ada di sini. Cari, pin, atau buka lagi mana pun.' },
  composer: { title: 'Tanya di sini', text: 'Tulis apa yang ingin kamu kerjakan. Ketik @ untuk menyertakan file.' },
  newSession: { title: 'Mulai dari awal', text: 'Sesi baru punya konteksnya sendiri. Pakai satu per pekerjaan.' },
  model: { title: 'Pemilih model', text: 'Memilih model mana yang menjawab kamu.' },
  modelLocal: 'Komputer ini bisa menjalankannya secara lokal: Pengaturan > Provider > Model Lokal.',
  capabilities: { title: 'Capabilities', text: 'Skill, tool, dan plugin yang bisa dipakai Thor. Tambah lagi di sini.' },
  messaging: { title: 'Pesan', text: 'Jangkau Thor dari Telegram, Slack, Discord, dan lainnya.' },
  rightPane: { title: 'Panel kerja', text: 'Membuka file, terminal, review, dan browser dalam aplikasi di sebelah kanan.' }
}
