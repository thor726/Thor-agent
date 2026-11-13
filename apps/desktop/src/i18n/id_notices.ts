import { idDesktopCommands } from './id_desktop_commands'
import { idSessionCommands } from './id_session_commands'
import type { Translations } from './types'

// Notis shell (toast tampilan remote, butterbar, tawaran tetap bangun), disebar ke en.ts.
export const idNotices = {
  remoteDisplayBanner: {
    message: reason =>
      `Rendering perangkat lunak aktif — tampilan remote terdeteksi (${reason}). Akselerasi GPU dimatikan untuk mencegah kedipan.`
  },
  butterbar: {
    goTo: (index, total) => `Tampilkan notis ${index} dari ${total}`,
    legal: {
      before: 'Penggunaan Thor Agent tunduk pada ',
      terms: 'Ketentuan Layanan',
      between: ' dan ',
      privacy: 'Kebijakan Privasi',
      after: '.'
    }
  },
  promptNotices: {
    legacySendUnconfirmed:
      'Server ini tidak bisa memastikan pengiriman pesan ini sebelumnya, jadi mungkin sudah dijalankan. Periksa percakapan sebelum mengirimnya lagi.',
    restoredDraftAttachmentsDropped:
      "Lampiran dari pesan yang belum terkirim tidak dipulihkan. Lampirkan lagi sebelum mengirimnya.",
    mcpReloadDeferred:
      'Chat ini sedang sibuk: perubahan MCP berlaku setelah turn-nya selesai dan MCP dimuat ulang lagi, atau saat kamu membuka lagi chat-nya',
    mcpReloadUnavailable: servers => `Tidak terhubung: ${servers}`,
    compactedTurnUnavailable:
      "Pesan itu diringkas saat chat dikompresi, jadi tidak bisa dipulihkan atau diedit lagi.",
    staleTurnUnavailable: "Pesan itu sudah tidak ada di riwayat chat ini.",
    sessionCommands: idSessionCommands,
    desktopCommands: idDesktopCommands
  },
  keepAwakeOffer: {
    title: 'Komputer kamu tidur saat Thor sedang bekerja',
    message:
      'Thor bisa menjaga komputer kamu tetap bangun selama tugas berjalan. Layar tetap mati, dan saat pakai baterai komputer kamu masih bisa tidur.',
    action: 'Tetap bangun saat bekerja'
  },
  connectorOffer: {
    heading: 'Pertahankan aplikasi yang terhubung',
    body: 'Masuk dengan akun Thor gratis untuk mempertahankan aplikasi yang kamu hubungkan, seperti Gmail atau Slack, di akun kamu.'
  }
} satisfies Pick<
  Translations,
  'remoteDisplayBanner' | 'butterbar' | 'promptNotices' | 'keepAwakeOffer' | 'connectorOffer'
>
