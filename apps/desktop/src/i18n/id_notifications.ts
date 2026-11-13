// Salinan pengaturan notifikasi yang dipakai saat locale desktop dimuat.
export const idNotifications = {
  title: 'Notifikasi',
  intro: 'Notifikasi OS (bukan toast dalam aplikasi). Per perangkat.',
  enableAll: 'Aktifkan notifikasi',
  enableAllDesc: 'Mematikan ini membisukan semua notifikasi di bawah.',
  focusedHint: 'Peringatan penyelesaian hanya muncul saat Thor ada di latar belakang.',
  kinds: {
    approval: {
      label: 'Perlu persetujuan',
      description: 'Sebuah perintah menunggu kamu menyetujui atau menolaknya.'
    },
    input: {
      label: 'Perlu input',
      description: 'Thor mengajukan pertanyaan atau butuh kata sandi atau secret.'
    },
    turnDone: {
      label: 'Balasan siap',
      description: 'Sebuah turn selesai saat Thor ada di latar belakang.'
    },
    turnError: {
      label: 'Turn gagal',
      description: 'Error turn di latar belakang.'
    },
    backgroundDone: {
      label: 'Tugas latar belakang selesai',
      description: 'Perintah terminal yang dijalankan di latar belakang selesai.'
    },
    credits: {
      label: 'Peringatan kredit',
      description: 'Akses kredit dijeda atau dipulihkan.'
    },
    plugin: {
      label: 'Notifikasi plugin',
      description: 'Plugin desktop mengirim notifikasi saat Thor ada di latar belakang.'
    }
  },
  browserPermission: {
    title: 'Notifikasi browser',
    allow: 'Izinkan',
    states: {
      default:
        'Tampilkan peringatan dari browser ini saat tab ada di latar belakang. Sampai kamu mengizinkannya, hanya judul tab yang berkedip.',
      granted: 'Diizinkan. Peringatan muncul saat tab ini di latar belakang; judul tab juga berkedip.',
      denied: "Diblokir di pengaturan situs browser ini. Judul tab tetap berkedip.",
      insecure: 'Butuh HTTPS, misalnya Tailscale serve. Lewat HTTP biasa judul tab tetap berkedip.',
      unsupported: 'Browser ini tidak bisa menampilkan notifikasi. Judul tab tetap berkedip.'
    }
  },
  test: 'Kirim notifikasi uji',
  testTitle: 'Thor',
  testBody: 'Notifikasi berfungsi.',
  testSent: 'Uji terkirim. Kalau tidak muncul apa pun, periksa izin notifikasi OS dan mode Jangan Ganggu.',
  testUnsupported: 'Sistem ini tidak mendukung notifikasi native.',
  muteSoundsTitle: 'Bisukan suara antarmuka',
  muteSoundsDesc:
    'Membisukan isyarat penyelesaian otomatis, wake-word dan thinking, umpan balik haptik, serta suara notifikasi OS. Pratinjau suara dan balasan yang diucapkan tetap diputar.',
  completionSoundTitle: 'Suara Penyelesaian',
  completionSoundDesc: 'Diputar saat turn agent selesai. Pilih preset dan pratinjau di sini.',
  completionSoundPreview: 'Pratinjau'
}
