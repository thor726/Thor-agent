import type { ClarifyCopy } from './types_clarify'

export const idClarify: ClarifyCopy = {
  notReady: 'Permintaan klarifikasi belum siap',
  gatewayDisconnected: 'Thor sedang offline. Sambungkan ulang, lalu kirim lagi.',
  sendFailed: 'Tidak bisa mengirim jawaban klarifikasi',
  loadingQuestion: 'Memuat pertanyaan…',
  other: 'Lainnya (ketik jawaban kamu)',
  placeholder: 'Ketik jawaban kamu…',
  skip: 'Lewati',
  skipped: 'Dilewati',
  noAnswer: 'Tidak ada jawaban',
  confirmAndContinueLabel: 'Konfirmasi dan lanjutkan',
  singleSelectHint: 'Pilih satu',
  multiSelectHint: 'Pilih semua yang berlaku',
  oneQuestion: '1 pertanyaan',
  questionProgress: (answered, total) => `${answered} dari ${total} terjawab`,
  notDelivered:
    "Pertanyaan ini tidak sampai ke aplikasi, jadi tidak bisa dijawab di sini. Tekan Stop untuk mengakhiri turn, lalu balas di chat."
}
