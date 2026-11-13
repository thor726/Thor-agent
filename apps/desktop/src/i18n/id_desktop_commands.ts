import type { DesktopCommandNotices } from './types_desktop_commands'

// Baris /rollback /agents /config /history /save /export /import /timestamps di sisi desktop.
export const idDesktopCommands: DesktopCommandNotices = {
  error: message => `error: ${message}`,
  rollbackUsage: 'penggunaan: /rollback [list] | diff <n|hash> | <n|hash> [file] [--all]',
  checkpointsDisabled: 'Checkpoint tidak diaktifkan untuk sesi ini (atur checkpoints.enabled di config.yaml).',
  checkpointsEmpty: 'Belum ada checkpoint untuk direktori kerja ini.',
  checkpointsHeader: 'Checkpoint (terbaru lebih dulu):',
  checkpointsHint:
    'Pulihkan dengan /rollback <n> [file] (tambahkan --all untuk juga menimpa editan kamu sendiri); pratinjau dengan /rollback diff <n>.',
  noDiff: 'Tidak ada perubahan sejak checkpoint itu.',
  rollbackFailed: error => `Rollback gagal: ${error}`,
  unknownError: 'error tidak diketahui',
  restored: hash => (hash ? `Checkpoint ${hash} dipulihkan.` : 'Checkpoint dipulihkan.'),
  rewound: count => `Memundurkan ${count} pesan dari percakapan ini.`,
  reopenForRewind: 'Buka lagi chat ini untuk melihat percakapan yang dimundurkan.',
  agentsEmpty: 'Tidak ada subagent aktif atau proses latar belakang di chat ini.',
  subagentsHeader: count => `Subagent (${count}):`,
  subagentFallback: 'subagent',
  statusRunning: 'berjalan',
  toolCalls: count => `${count} panggilan tool`,
  processesHeader: count => `Proses latar belakang (${count}):`,
  configHeader: 'Konfigurasi (tampilan, persetujuan, tempel dan pengaturan suara; sisanya tidak ditampilkan):',
  configDefaults: '(default)',
  configFooter: 'Ubah pengaturan di Pengaturan, atau edit config.yaml dengan `thor config edit` di host gateway.',
  historyHeader: count => `Riwayat percakapan (${count} pesan):`,
  historyEmpty: 'Belum ada pesan.',
  historyYou: 'Kamu',
  historyThor: 'Thor',
  saveUsage: 'penggunaan: /save [json|md|html] [nama-file] [redact]',
  saveLegacyRefused:
    'Tidak disimpan: gateway ini tidak bisa mengekspor salinan yang disunting, bernama, atau bukan JSON. Update gateway-nya, atau jalankan /save tanpa opsi untuk menulis JSON mentah di host gateway.',
  savedOnHost: path => `Tersimpan di host gateway: ${path}`,
  unknownPath: '(path tidak diketahui)',
  saveUnsupported: 'error: build desktop ini tidak bisa menyimpan file',
  saveDialogTitle: 'Simpan percakapan',
  savedTo: path => `Percakapan disimpan ke ${path}`,
  saveCancelled: 'Tidak disimpan (dibatalkan).',
  exportRemote:
    '/export memaketkan profil dari host gateway, yang bukan mesin ini. Jalankan `thor profile export` di host itu.',
  importRemote:
    '/import memasang profil di host gateway, yang bukan mesin ini. Jalankan `thor profile import <archive>` di host itu.',
  timestampsUsage: 'penggunaan: /timestamps [on|off|status]',
  timestampsOn: 'Timestamp: aktif (jendela ini; atur display.timestamps di config.yaml untuk menyimpannya)',
  timestampsOff: 'Timestamp: mati (jendela ini; atur display.timestamps di config.yaml untuk menyimpannya)'
}
