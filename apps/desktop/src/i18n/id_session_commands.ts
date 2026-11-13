import type { SessionCommandNotices } from './types_notices'

// Baris /undo /retry /steer /queue bertipe: kata-kata Ink TUI pada gateway yang sama.
export const idSessionCommands: SessionCommandNotices = {
  undoUsage: 'penggunaan: /undo [N]',
  undoNothing: 'tidak ada yang bisa dibatalkan',
  undidOne: (count: string) => `membatalkan ${count} pesan — pesan yang dihapus ada di composer`,
  undidOther: (count: string) => `membatalkan ${count} pesan — pesan yang dihapus ada di composer`,
  retryNothing: 'tidak ada yang bisa dicoba ulang',
  retryUnsupported: '/retry: coba ulang tidak mendukung media atau bagian konten yang tidak dikenal',
  busy: (command: string) =>
    `sesi sibuk — Thor masih membalas. Hentikan balasan saat ini dulu (tombol Stop, atau Ctrl+C di terminal), lalu jalankan /${command}.`,
  busyCompressing: (command: string) =>
    `sesi sibuk — /compress sedang berjalan; jalankan /${command} saat selesai.`,
  steerUsage: 'penggunaan: /steer <prompt>',
  steerQueued: (preview: string) => `steer masuk antrean — sampai setelah panggilan tool berikutnya: "${preview}"`,
  steerNoActiveTurn: (preview: string) => `tidak ada turn aktif — masuk antrean untuk berikutnya: "${preview}"`,
  steerRejected: 'steer ditolak — tidak ada turn aktif, masuk antrean untuk turn berikutnya',
  queued: (preview: string) => `masuk antrean: "${preview}"`,
  queueFailed: 'tidak bisa memasukkan pesan ke antrean',
  countOne: (count: string) => `${count} pesan dalam antrean`,
  countOther: (count: string) => `${count} pesan dalam antrean`,
  queueEditKeptTitle: 'Pesan dalam antrean tidak diubah',
  queueEditKept: 'Pesan mulai berjalan atau ditolak sebelum editan kamu tersimpan. Teks editan kamu ada di composer.',
  queueEditUnconfirmedTitle: 'Edit tidak terkonfirmasi',
  queueEditUnconfirmed:
    'Thor tidak bisa mengonfirmasi editan kamu. Simpan lagi untuk mencoba ulang editan yang sama; pesan tidak pernah masuk antrean dua kali.'
}
