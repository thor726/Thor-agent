import type { CronControlCopy } from './types_cron_control'

export const idCronControl: CronControlCopy = {
  stop: 'Stop',
  stopping: 'Menghentikan…',
  stopped: 'Run dibatalkan',
  finishedFirst: 'Run selesai sebelum sempat dihentikan',
  nothingToStop: 'Tidak ada run yang berjalan',
  failedStop: 'Tidak bisa menghentikan run',
  lastCancelled: (reason: string) => (reason ? `Run terakhir dibatalkan: ${reason}` : 'Run terakhir dibatalkan'),
  catchUpLabel: 'Run yang terlewat',
  catchUpHint: 'Apa yang harus dilakukan dengan run yang terlewat saat Thor tidak berjalan.',
  catchUpChoices: {
    default: 'Pakai default',
    run: 'Jalankan sekali saat kembali',
    skip: 'Lewati'
  }
}
