import type { Translations } from './types'

// Salinan layar boot (termasuk layar tahan-update), dirangkai oleh en.ts.
export const idBoot = {
  boot: {
    ready: 'Thor Desktop siap',
    desktopBootFailedWithMessage: message => `Boot desktop gagal: ${message}`,
    steps: {
      connectingGateway: 'Menghubungkan gateway desktop live',
      loadingSettings: 'Memuat pengaturan Thor',
      loadingSessions: 'Memuat sesi terbaru',
      retryingRemoteBackend: 'Menyambungkan ulang ke backend Thor remote…',
      startingDesktopConnection: 'Memulai koneksi desktop',
      startingThorDesktop: 'Menjalankan Thor Desktop…'
    },
    errors: {
      backgroundExited:
        'Layanan yang menjalankan chat kamu berhenti tak terduga. Nyalakan ulang untuk melanjutkan — chat dan pengaturan kamu aman.',
      backgroundExitedDuringStartup: 'Thor berhenti tepat setelah dijalankan.',
      backendStopped: 'Thor berhenti bekerja di latar belakang',
      restartThor: 'Nyalakan ulang Thor',
      openLogs: 'Buka log',
      desktopBootFailed: "Thor tidak bisa dijalankan",
      gatewayConnectionLost: 'Thor kehilangan koneksinya',
      gatewayConnectionLostDetail:
        'Masih mencoba menyambung ulang. Kamu bisa tetap membaca dan menulis draf. Kalau ini terus terjadi, sambungkan ulang sekarang atau periksa pengaturan koneksi kamu.',
      reconnectNow: 'Sambungkan ulang sekarang',
      connectionSettings: 'Pengaturan koneksi',
      gatewaySignInRequired: 'Thor remote kamu mengeluarkan sesi kamu',
      gatewaySignInRequiredDetail: 'Masuk lagi untuk menyambung ulang. Chat dan pengaturan kamu aman.',
      signInAgain: 'Masuk lagi',
      ipcBridgeUnavailable: "Thor Desktop tidak bisa berkomunikasi dengan lapisan latar belakangnya sendiri. Nyalakan ulang aplikasi."
    },
    // Sebab sederhana untuk kegagalan boot backend lokal (`classifyBootFailure`);
    // output mentahnya tersimpan di balik "Tampilkan log terbaru".
    causes: {
      exitedEarly: "Layanan latar belakang Thor berhenti tepat setelah dijalankan.",
      timedOut: "Layanan latar belakang Thor tidak menjawab tepat waktu.",
      permission: "Thor tidak bisa menulis ke folder datanya (masalah izin).",
      diskFull: 'Disk penuh, jadi Thor tidak bisa dijalankan.',
      portInUse: 'Program lain memakai port jaringan yang dibutuhkan Thor.',
      installMissing: "Sebagian instalasi Thor hilang. Pilih Perbaiki instalasi untuk mengembalikannya."
    },
    failure: {
      title: "Thor tidak bisa dijalankan",
      description:
        "Layanan latar belakang Thor tidak menyala. Coba salah satu langkah pemulihan di bawah. Tidak ada yang menghapus chat atau pengaturan kamu.",
      details: 'Detail',
      remoteTitle: 'Perlu login gateway remote',
      remoteDescription:
        'Sesi gateway remote kamu sudah kedaluwarsa. Masuk lagi untuk menyambung ulang. Tidak ada yang menghapus chat atau pengaturan kamu.',
      webappTitle: 'Masuk ke Thor',
      webappDescription: 'Jalankan thor webapp di komputer ini untuk memasukkan browser ini.',
      retry: 'Coba lagi',
      repairInstall: 'Perbaiki instalasi',
      useLocalGateway: 'Pakai gateway lokal',
      gatewaySettings: 'Pengaturan gateway',
      back: 'Kembali',
      openLogs: 'Buka log',
      repairHint: 'Perbaikan menjalankan ulang installer dan bisa memakan beberapa menit di mesin baru.',
      bundledReinstallHint:
        'Instalasi bundled ini tidak bisa memperbaiki dirinya dari dalam aplikasi — install ulang aplikasinya untuk memulihkan backend-nya.',
      reinstallApp: 'Install ulang aplikasi',
      remoteSignInHint: signInLabel =>
        `Keluar dari sesi browser remote yang tersimpan, lalu membuka ${signInLabel}. Pakai gateway lokal untuk beralih ke backend bundled.`,
      signOutAndSignIn: 'Keluar & masuk',
      remoteFailureHint: 'Periksa URL gateway dan login di Pengaturan gateway, atau beralih ke gateway lokal.',
      cloudDownTitle: 'Agent Thor Cloud sedang mati',
      cloudDownDescription:
        'Agent cloud yang dikelola Thor dan disambungkan gateway ini mengembalikan error server. Tidak bisa dinyalakan ulang dari sini — periksa statusnya, beralih ke gateway lokal, atau minta dukungan.',
      cloudDownHint:
        'Tombol di bawah membuka Thor Portal (status dan kontrol instance) dan Discord kami untuk dukungan.',
      cloudDownCheckPortal: 'Periksa status Portal',
      cloudDownDiscord: 'Minta bantuan di Discord',
      hideRecentLogs: 'Sembunyikan log terbaru',
      showRecentLogs: 'Tampilkan log terbaru',
      signedInTitle: 'Sudah masuk',
      signedInMessage: 'Menyambungkan ulang ke gateway remote…',
      signInIncompleteTitle: 'Login belum selesai',
      signInIncompleteMessage: 'Jendela login tertutup sebelum autentikasi selesai.',
      signInFailed: 'Login gagal',
      signInToRemoteGateway: 'Masuk ke gateway remote',
      signInWithProvider: provider => `Masuk dengan ${provider}`,
      identityProvider: 'provider identitas kamu'
    },
    updateHold: {
      title: 'Update sebelumnya masih menahan Thor',
      titleUnverified: "Thor tidak bisa memastikan update terakhir sudah selesai",
      description:
        "Thor menunda start supaya tidak memuat file yang mungkin masih diubah oleh update. Thor mulai sendiri begitu penahanan berakhir.",
      heldByProcess: pid =>
        `Update (proses ${pid}) sudah keluar, tapi proses yang dijalankannya masih menahan instalasi Thor.`,
      heldUnknown: 'Sebuah update sudah keluar, tapi proses yang dijalankannya masih menahan instalasi Thor.',
      unverified: "Helper update tidak bisa memeriksa siapa yang memegang instalasi Thor saat ini. Thor terus memeriksa.",
      since: time => `Menunggu sejak ${time}`,
      lastChecked: time => `Terakhir diperiksa ${time}`,
      recoveryHint:
        'Biasanya ini hilang dalam beberapa menit. Kalau tidak: tutup Thor, akhiri proses git atau thor yang tersisa (atau nyalakan ulang komputer), lalu buka Thor lagi.',
      checkAgain: 'Periksa lagi',
      quit: 'Tutup Thor',
      openLogs: 'Buka log',
      startAnyway: 'Mulai saja…',
      confirmTitle: 'Mulai Thor saat update masih menahannya?',
      confirmBody:
        "Proses update yang tersisa mungkin masih mengubah file Thor. Mulai sekarang bisa memuat instalasi setengah ter-update, yang mungkin tidak berfungsi sampai kamu menjalankan update lagi. Thor mencatat pilihan ini di log-nya dan membiarkan penanda update di tempatnya.",
      confirmKeepWaiting: 'Tetap menunggu',
      confirmStart: 'Mulai saja',
      startAnywayRefused: 'Yang menahan instalasi berubah sebelum Thor sempat mulai. Tinjau lalu coba lagi.'
    }
  }
} satisfies Pick<Translations, 'boot'>
