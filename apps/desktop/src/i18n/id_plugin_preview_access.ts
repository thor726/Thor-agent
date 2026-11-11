import type { PluginPreviewAccessTranslations } from './types_plugin_preview_access'

/** Salinan untuk prompt persetujuan skrip preview dan daftar izin per-plugin (Capabilities ▸ Plugins). */
export const idPluginPreviewAccess: PluginPreviewAccessTranslations = {
  previewScriptPromptTitle: (plugin: string) => `Izinkan ${plugin} menjalankan skrip di halaman ini?`,
  previewScriptPromptBody: (plugin: string, origin: string) =>
    `${plugin} ingin menjalankan JavaScript di Browser preview pada ${origin}.`,
  previewScriptPromptRisk: 'Skrip bisa membaca dan mengubah apa pun di situs itu, termasuk halaman dari akun yang kamu login di sana.',
  previewScriptPromptRevokeHint: 'Hanya berlaku untuk situs ini. Kamu bisa mencabutnya di Capabilities ▸ Plugins.',
  previewScriptAllow: 'Izinkan di situs ini',
  previewScriptDeny: "Jangan izinkan",
  previewScriptAccessLabel: 'Skrip halaman',
  previewScriptAccessNone: 'Bertanya sebelum menjalankan skrip di halaman',
  previewScriptRevoke: (origin: string) => `Cabut akses ke ${origin}`,
  previewScriptRevoked: (plugin: string, origin: string) => `${plugin} tidak bisa lagi menjalankan skrip di ${origin}.`,
  previewScriptRevokeUnsaved: (plugin: string, origin: string) =>
    `Tidak bisa menyimpan perubahan itu, jadi hanya berlaku sampai Thor dinyalakan ulang. ${plugin} diblokir di ${origin} untuk sekarang.`
}
