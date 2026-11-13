import type { GatewayGroupOpenCopy, SkillDeepLinkCopy } from './types_deep_links'

export const idSkillDeepLink: SkillDeepLinkCopy = {
  installTitle: (name: string) => `Install “${name}”?`,
  installDescription: 'Skill ini akan tersedia di sesi baru. Hanya install sumber yang kamu percayai.',
  installTo: 'Install ke',
  thisComputer: 'Komputer ini',
  installing: 'Menginstall…',
  installComplete: (name: string) => `“${name}” terpasang`,
  destinationChanged: 'Tujuannya berubah. Tutup dialog ini dan buka lagi tautan install-nya.',
  installed: 'Terpasang',
  source: 'Sumber'
}

export const idGatewayGroupOpen: GatewayGroupOpenCopy = {
  opening: 'Membuka grup chat…',
  lookupFailed: 'Tidak bisa mencari grup ini di gateway. Coba lagi.',
  missing: 'Grup chat ini sudah tidak ada.'
}
