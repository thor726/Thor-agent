import type { PluginUpdateAllTranslations } from './types_plugin_update'

/** Tab Plugin: "Update semua" dan saklar update otomatis. */
export const idPluginUpdateAll: PluginUpdateAllTranslations = {
  updateAll: 'Update semua',
  updatingAll: 'Meng-update…',
  updateAllTip: 'Periksa setiap plugin terpasang dan terapkan update yang tidak perlu ditinjau',
  updateAllDone: (updated: number, review: number, failed: number) =>
    `${updated} diperbarui` + (review ? `, ${review} perlu ditinjau` : '') + (failed ? `, ${failed} gagal` : ''),
  updateAllNone: 'Semua plugin sudah terbaru',
  updateAllFailed: 'Tidak bisa meng-update plugin',
  autoUpdate: 'Update otomatis',
  autoUpdateTip: (hours: number) =>
    `Terapkan update plugin otomatis saat gateway memeriksa (setiap ${hours} jam). Kode yang diperbarui dimuat di sesi baru.`,
  autoUpdateFailed: 'Tidak bisa mengubah update otomatis plugin'
}
