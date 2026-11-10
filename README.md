<p align="center">
  <img src="assets/banner.png" alt="Thor Agent" width="100%">
</p>

# Thor Agent ⚡

<p align="center">
  <a href="https://github.com/dwisetyabudi15581/Thor-agent"><img src="https://img.shields.io/badge/Repo-GitHub-FFBF00?style=for-the-badge&logo=github" alt="Repo GitHub"></a>
  <a href="https://github.com/dwisetyabudi15581/Thor-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/Lisensi-MIT-green?style=for-the-badge" alt="Lisensi: MIT"></a>
</p>

**Agen AI yang menyempurnakan dirinya sendiri** — Thor Agent membuat *skill* dari pengalaman, memperbaikinya saat dipakai, mengingat percakapan lama, dan membangun pemahaman yang makin dalam tentang Anda di setiap sesi. Ia tidak terikat pada satu laptop: bicara dengannya dari Telegram sementara ia bekerja di VM cloud, atau jalankan langsung di terminal Anda.

Gunakan model apa pun yang Anda mau — OpenRouter, OpenAI, Anthropic, atau endpoint Anda sendiri. Ganti kapan saja dengan `thor model` — tanpa mengubah kode, tanpa lock-in.

## Daftar Isi

- [Fitur Utama](#fitur-utama)
- [Apakah Perlu Docker?](#apakah-perlu-docker)
- [Persyaratan Sistem](#persyaratan-sistem)
- [Instalasi](#instalasi)
- [Cara Penggunaan](#cara-penggunaan)
- [Otomatisasi dengan Cron](#otomatisasi-dengan-cron)
- [Menjalankan di Banyak Platform (Gateway)](#menjalankan-di-banyak-platform-gateway)
- [Menjalankan di Docker (Opsional)](#menjalankan-di-docker-opsional)
- [Konfigurasi](#konfigurasi)
- [Keamanan](#keamanan)
- [Lisensi](#lisensi)

## Fitur Utama

| Fitur | Keterangan |
|---|---|
| **Antarmuka terminal sungguhan** | TUI lengkap: edit multi-baris, autocomplete slash-command, riwayat percakapan, interupsi-di-tengah-jalan, dan output tool yang mengalir (streaming). |
| **Hadir di banyak platform** | Telegram, Discord, Slack, WhatsApp, Signal, dan CLI — semuanya dari satu proses gateway. Transkripsi pesan suara, kesinambungan percakapan lintas platform. |
| **Loop pembelajaran tertutup** | Memori yang dikurasi agen itu sendiri. Pembuatan skill otomatis setelah tugas kompleks, skill menyempurnakan diri saat dipakai, pencarian sesi FTS5 dengan ringkasan LLM untuk mengingat lintas sesi. |
| **Otomatisasi terjadwal** | Penjadwal cron bawaan dengan pengiriman hasil ke platform mana pun. Laporan harian, backup malam, audit mingguan — semuanya dalam bahasa natural, berjalan tanpa diawasi. |
| **Mendelegasikan & paralel** | Memunculkan subagent terisolasi untuk alur kerja paralel. Tulis skrip Python yang memanggil tool via RPC. |
| **Berjalan di mana saja** | Enam backend terminal: **local**, Docker, SSH, Modal, Daytona, dan Vercel Sandbox. |
| **Siap untuk riset** | Pembangkitan trajektori batch untuk melatih generasi model berikutnya. |

## Apakah Perlu Docker?

**Tidak.** Thor Agent berjalan penuh di terminal Anda tanpa Docker — backend terminal `local` adalah bawaan (default), dan seluruh fitur (chat, skill, cron, gateway) bekerja normal di mode ini. Ini adalah cara pakai yang disarankan untuk penggunaan di terminal.

Docker berguna hanya jika Anda ingin:

1. **Menjalankan Thor di dalam container** — misalnya deploy gateway di VPS secara terisolasi dan mudah di-upgrade tanpa menyentuh sistem host.
2. **Docker sebagai backend terminal (sandbox)** — Thor berjalan di host, tetapi setiap perintah shell dieksekusi di dalam container sandbox terisolasi yang persisten.
3. **Lingkungan yang reproducible** — versi Python, Node, dan dependensi terkunci di image.

Ketiga opsi tersebut **sudah disertakan** di repo ini (`Dockerfile`, direktori `docker/`, dan panduan di bawah), jadi Anda bisa memakainya kapan pun mau.

## Persyaratan Sistem

| Kebutuhan | Keterangan |
|---|---|
| Sistem operasi | Linux, macOS, atau WSL2 (Windows native juga didukung untuk CLI) |
| Python | 3.11–3.14 (3.14 disarankan; installer menyediakannya otomatis) |
| Node.js & pnpm | Untuk TUI dan gateway; dipasang otomatis oleh manajer paket bawaan (PM) |
| Git (+ git-lfs) | Untuk kloning dan pembaruan |
| Opsional | FFmpeg (media/suara), ripgrep (pencarian cepat) |

## Instalasi

### Cara 1 — Installer satu baris (disarankan)

Linux, macOS, WSL2:

```bash
curl -fsSL https://raw.githubusercontent.com/dwisetyabudi15581/Thor-agent/main/scripts/install.sh | bash
```

Installer mengkloning repo, menyiapkan Python/uv, Node, pnpm, dan dependensi, lalu mengakhiri prosesnya dengan wizard `thor setup`. Lokasi bawaan: `~/.thor/thor-agent`. Data pengguna (konfigurasi, sesi, skill, memori) disimpan di `~/.thor/`.

Untuk folder khusus:

```bash
curl -fsSL https://raw.githubusercontent.com/dwisetyabudi15581/Thor-agent/main/scripts/install.sh | bash -s -- --dir ~/thor
```

### Cara 2 — Manual dari source (untuk pengembangan)

```bash
git clone https://github.com/dwisetyabudi15581/Thor-agent.git
cd Thor-agent
source ./activate        # menyiapkan Python 3.14, pnpm, dan dependensi (fish: activate.fish)
thor --version
```

Skrip `activate` mendefinisikan perintah `thor` sebagai fungsi shell untuk checkout ini. Ulangi `source ./activate` di setiap shell baru. Untuk data terpisah dari produksi, set `export THOR_HOME=~/.thor-dev` sebelum menjalankan.

### Cara 3 — Docker (opsional)

Lihat bagian [Menjalankan di Docker (Opsional)](#menjalankan-di-docker-opsional).

## Cara Penggunaan

### 1) Setup pertama kali

```bash
thor setup
```

Wizard interaktif ini memandu Anda memilih penyedia model (OpenRouter, OpenAI, dll.), memasukkan kunci API, dan (opsional) menyiapkan platform chat untuk gateway. Kunci API tersimpan di `~/.thor/.env`.

### 2) Ngobrol di terminal

```bash
thor          # memulai chat interaktif (TUI)
thor chat     # sama seperti di atas
```

Melanjutkan percakapan sebelumnya:

```bash
thor -c                 # lanjutkan sesi terakhir
thor -r                 # pilih sesi lama untuk dilanjutkan
thor -c "Nama Sesi"     # lanjutkan sesi bernama tertentu
```

### 3) Perintah CLI yang sering dipakai

| Perintah | Fungsi |
|---|---|
| `thor` / `thor chat` | Chat interaktif di terminal |
| `thor setup` | Wizard konfigurasi (penyedia, kunci API, platform) |
| `thor model` | Melihat & mengganti model (picker interaktif) |
| `thor status` | Ringkasan status: model aktif, gateway, sesi |
| `thor doctor` | Diagnosis instalasi & konfigurasi |
| `thor sessions` | Daftar & kelola sesi percakapan |
| `thor skills` | Kelola skill (buat, lihat, pasang) |
| `thor cron list` | Lihat tugas terjadwal |
| `thor gateway run` | Jalankan gateway multi-platform di latar depan |
| `thor mcp` | Kelola server MCP |
| `thor plugins` | Kelola plugin |
| `thor auth login` | Login penyedia via OAuth |
| `thor dashboard` | Dasbor web bawaan |
| `thor logs` | Lihat log |
| `thor update` | Perbarui Thor Agent |
| `thor backup` / `thor import` | Cadangkan / pulihkan data |
| `thor uninstall` | Hapus instalasi |
| `thor --version` | Versi & status pembaruan |
| `thor <perintah> --help` | Bantuan per perintah |

### 4) Slash command di dalam chat

Saat berada di dalam TUI/chat, Anda bisa memakai perintah slash:

| Perintah | Fungsi |
|---|---|
| `/new [nama]` | Mulai sesi baru (opsional langsung diberi nama) |
| `/history` | Tampilkan riwayat percakapan |
| `/save md laporan.md` | Ekspor sesi ke Markdown/JSON/HTML (tambahkan `redact` untuk menyamarkan kunci API) |
| `/retry` | Kirim ulang pesan terakhir |
| `/undo` | Hapus pasangan tanya-jawab terakhir |
| `/rewind` | Kembali ke pesan lama untuk diedit (browser transkrip) |
| `/title Judul` | Beri judul sesi |
| `/compress` | Padatkan konteks percakapan (ringkas riwayat lama) |
| `/rollback` | Kembalikan checkpoint sistem berkas |
| `/stop` | Hentikan semua proses latar belakang |
| `/help` | Daftar semua slash command |

Tekan `Esc` dua kali untuk mengedit pesan sebelumnya, dan `Ctrl+C` untuk interupsi di tengah respons lalu arahkan ulang agen.

### 5) Ganti model

```bash
thor model
```

Picker interaktif menampilkan katalog model dari semua penyedia yang terpasang. Pilihan tersimpan di `~/.thor/config.yaml` (`model.default`).

## Otomatisasi dengan Cron

Buat tugas terjadwal dalam bahasa natural atau cron klasik:

```bash
# cek harga tiap jam, hasil dikirim ke Telegram
thor cron add "every 1h" "Bandingkan harga di situs X dengan catatan terakhir. Jika berubah, ringkas apa yang berubah." \
  --name "Monitor Harga" --deliver telegram

# laporan mingguan tiap Senin jam 9 pagi
thor cron add "0 9 * * 1" "Buat laporan mingguan dari catatan sesi: progres, temuan, dan rencana minggu depan." \
  --name "Laporan Mingguan"

thor cron list      # lihat semua tugas
thor cron edit 1    # ubah tugas #1
thor cron rm 1      # hapus tugas #1
```

Opsi `--deliver` mendukung `telegram`, `discord`, `slack`, `whatsapp`, `signal`, dan `local` (terminal). Tugas berjalan tanpa diawasi dan hasilnya dikirim ke tujuan yang dituju.

## Menjalankan di Banyak Platform (Gateway)

1. Jalankan `thor setup` dan pilih platform chat (mis. Telegram) — Anda akan dipandu memasukkan token bot.
2. Jalankan gateway:

```bash
thor gateway run            # di latar depan
thor gateway start          # di latar belakang
thor gateway install        # pasang agar jalan saat login/boot
```

Sekarang Anda bisa mengobrol dengan Thor dari Telegram/Discord/Slack/WhatsApp/Signal sementara agen bekerja di mesin Anda. Port `8642` (opsional) mengekspos API server yang kompatibel dengan OpenAI dan endpoint kesehatan.

## Menjalankan di Docker (Opsional)

Bangun image dari source, lalu jalankan wizard setup:

```bash
git clone https://github.com/dwisetyabudi15581/Thor-agent.git
cd Thor-agent
docker build -t thor-agent .

mkdir -p ~/.thor
docker run -it --rm -v ~/.thor:/opt/data thor-agent setup
```

Semua data pengguna (konfigurasi, kunci API, sesi, skill, memori) tersimpan di satu direktori yang di-mount dari host ke `/opt/data` — image-nya stateless dan bisa diganti tanpa kehilangan konfigurasi.

Menjalankan gateway sebagai layanan latar belakang:

```bash
docker run -d \
  --name thor \
  --restart unless-stopped \
  -v ~/.thor:/opt/data \
  -p 8642:8642 \
  thor-agent gateway run
```

Menambahkan dasbor web (port 9119):

```bash
docker run -d \
  --name thor \
  --restart unless-stopped \
  -v ~/.thor:/opt/data \
  -p 8642:8642 -p 9119:9119 \
  -e THOR_DASHBOARD=1 \
  thor-agent gateway run
```

> 💡 **Docker sebagai backend terminal (sandbox)**: jika hanya ingin eksekusi perintah terisolasi tanpa menjalankan Thor di container, atur backend terminal ke `docker` di konfigurasi — agen tetap di host, perintah shell dieksekusi di dalam container sandbox persisten. Rincian ada di `website/docs/user-guide/docker.md`.

> ⚠️ Gunakan SSH (bukan konsol browser VPS) saat menyalin perintah `docker run` di atas — konsol browser sering merusak karakter `:`, `@`, dan `=`.

## Konfigurasi

- **`~/.thor/config.yaml`** — konfigurasi utama (model bawaan, penyedia, gateway, backend terminal). Lebih mudah lewat `thor setup` / `thor model` / `thor config`.
- **`~/.thor/.env`** — kunci API per penyedia, antara lain:
  `OPENROUTER_API_KEY`, `FIREWORKS_API_KEY`, `NOVITA_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `KIMI_API_KEY`, `DEEPINFRA_API_KEY`, dan banyak lagi — daftar lengkap beserta contohnya ada di [`.env.example`](.env.example).
- **`thor auth login`** — login OAuth untuk penyedia yang mendukungnya (Anthropic, OpenAI Codex, xAI, Qwen, MiniMax, OpenRouter) — tanpa perlu menaruh kunci manual.
- **`THOR_HOME`** — variabel lingkungan untuk memindahkan lokasi data (default `~/.thor`), berguna untuk instance terpisah.

## Keamanan

- Thor meminta persetujuan (approval) sebelum menjalankan perintah berisiko — di terminal maupun via tombol persetujuan di platform chat.
- Pemindaian keamanan MCP bawaan memblokir server MCP berbahaya.
- Gunakan `/save ... redact` saat mengekspor transkrip agar kunci API tersamarkan.
- Untuk gateway tanpa pengawasan, pemberhentian keras loop tool aktif secara bawaan (`tool_loop_guardrails` di config).

## Bahasa

README dan panduan repo ini berbahasa Indonesia. Antarmuka CLI mendukung banyak bahasa (Inggris, Jerman, Spanyol, Prancis, Korea, Jepang, Arab, Portugis, Rusia, Mandarin, dll.) melalui berkas locale di `locales/` — terjemahan Bahasa Indonesia (`locales/id.yaml`) belum tersedia dan kontribusi sangat diterima.

## Lisensi

[MIT](LICENSE) — silakan lihat berkas `LICENSE` untuk teks lengkapnya.
