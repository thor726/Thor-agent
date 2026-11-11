import type { UpdateChannelCopy } from './types_update_channel'

export const idUpdateChannel: UpdateChannelCopy = {
  title: 'Channel update',
  description: 'Instalasi stabil hanya memakai rilis yang dipublikasikan. Setiap commit mengikuti branch main seiring perubahan masuk.',
  stable: 'Rilis stabil',
  main: 'Setiap commit',
  stableConfirmTitle: 'Beralih ke rilis stabil?',
  stableConfirmBody:
    'Thor akan pindah ke rilis terbaru yang dipublikasikan, yang bisa lebih lama dari kode yang kamu jalankan sekarang. Data yang ditulis kode lebih baru mungkin tidak terbaca dengan benar, jadi cadangkan dulu.',
  stableConfirm: 'Beralih ke stabil',
  failed: 'Tidak bisa mengubah channel update',
  detailsLabel: 'Channel',
  branch: (b: string) => `Branch: ${b}`,
  change: 'Ubah',
  latestRelease: (v: string) => `Kamu memakai rilis stabil terbaru (${v}).`,
  rollbackTitle: (v: string) => `Kembali ke rilis stabil ${v}`,
  rollbackBody: (v: string) =>
    `Build ini lebih baru dari rilis stabil ${v}. Menginstalnya memindahkan Thor kembali ke rilis tersebut.`,
  heldBody: (v: string) =>
    `Build ini lebih baru dari rilis stabil ${v}. Sesi kamu sudah memakai runtime gateway yang tidak bisa dibuka ${v}, jadi Thor tetap di build ini sampai rilis stabil yang lebih baru keluar.`,
  rollbackAction: (v: string) => `Kembalikan ke ${v}`,
  allChanges: 'Lihat semua perubahan'
}
