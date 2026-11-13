import type { MemoryLayersTranslations } from './types_memory_layers'

// Settings > Memory & Context dan Command Center > Maintenance (#145175).
export const idMemoryLayers: MemoryLayersTranslations = {
  activeProvider: 'Provider memori aktif',
  selectedProvider: 'Provider memori terpilih',
  selectedDesc: current => `Belum aktif: sesi tetap memakai ${current} sampai pilihan ini disimpan.`,
  builtinMemory: 'hanya memori bawaan',
  noProvider: 'Tidak ada — hanya memori bawaan',
  noProviderDesc:
    'Thor hanya memakai lapisan bawaan di bawah. Pilih provider eksternal di Pengaturan › Memori & Konteks untuk menambahkannya.',
  providerDesc: name => `${name} menambah daya ingatnya sendiri ke setiap sesi, di atas lapisan bawaan.`,
  providerNotReadyDesc: name =>
    `${name} adalah provider tersimpan tapi tidak menambah daya ingat sampai siap. Lapisan bawaan tetap bekerja.`,
  providerUnknownDesc: name => `${name} adalah provider tersimpan; Thor tidak bisa membaca apakah sudah siap.`,
  statusUnavailable: 'Status memori tidak tersedia',
  statusUnavailableDesc: "Tidak bisa membaca provider memori mana yang aktif atau apakah sudah siap.",
  retry: 'Coba lagi',
  status: {
    ready: 'siap',
    needs_config: 'perlu penyiapan',
    unavailable: 'tidak tersedia',
    missing: 'belum terpasang'
  },
  builtinLayer: 'Lapisan bawaan',
  onByDefault: 'Aktif secara default',
  on: 'Aktif',
  off: 'Mati',
  onlyFile: file => `hanya ${file}`,
  builtinDesc:
    'MEMORY.md dan USER.md adalah memori milik Thor sendiri, terpisah dari provider eksternal mana pun. Keduanya dimuat ke sesi secara default; toggle memori dan profil pengguna di Pengaturan › Memori & Konteks mematikan masing-masing. Provider menambah lapisan ini; tidak pernah menggantikannya.'
}
