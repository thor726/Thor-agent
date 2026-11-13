import type { Translations } from './types'

export const idConnectorAccounts: Translations['connectorsPage']['accounts'] = {
  heading: 'Akun',
  count: (count: number) => `${count} akun`,
  addAnother: 'Tambah akun lain',
  aliasLabel: 'Nama akun',
  aliasHint: 'Huruf kecil, angka dan tanda hubung, maksimal 32. Misalnya work atau home.',
  aliasInvalid: 'Pakai huruf kecil, angka dan tanda hubung, diawali huruf atau angka.',
  aliasTaken: 'Nama itu sudah dipakai.',
  add: 'Hubungkan',
  rename: 'Ganti nama',
  renameLabel: (name: string) => `Nama baru untuk ${name}`,
  renameGone: 'Akun itu sudah tidak ada. Akun dihapus atau digantikan oleh koneksi ulang.',
  remove: 'Hapus',
  removeTitle: (app: string, name: string) => `Hapus akun ${app} ${name}?`,
  removeBody: 'Thor berhenti bertindak sebagai akun ini. Akun kamu yang lain tetap terhubung.',
  retiredCount: (count: number) => `${count} dinonaktifkan`,
  status: {
    expired: 'Akses kedaluwarsa',
    failed: 'Tidak bisa terhubung',
    inactive: 'Nonaktif',
    pending: 'Menunggu login',
    retired: 'Digantikan oleh koneksi ulang',
    revoked: 'Akses dicabut'
  }
}
