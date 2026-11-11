# Kebijakan Keamanan Thor Agent

> 🌐 **English:** [SECURITY.md](SECURITY.md) — versi asli dokumen ini.

Dokumen ini menjelaskan trust model Thor Agent, menyebutkan satu
security boundary yang dianggap load-bearing oleh proyek ini, dan
mendefinisikan scope untuk laporan kerentanan.

## 1. Melaporkan Kerentanan

Laporkan secara privat melalui [GitHub Security Advisories](https://github.com/dwisetyabudi15581/Thor-agent/security/advisories/new)
atau **security@thor-agent.local**. Jangan membuka issue publik untuk
kerentanan keamanan. **Thor Agent tidak menjalankan program bug
bounty.**

Laporan yang berguna memuat:

- Deskripsi singkat dan penilaian severity.
- Komponen yang terdampak, diidentifikasi dengan file path dan rentang
  baris (misalnya `path/to/file.py:120-145`).
- Detail environment (`thor --version`, commit SHA, OS, versi
  Python).
- Reproduksi terhadap `main` atau release terbaru.
- Pernyataan trust boundary mana di §2 yang terlewati.

Mohon baca §2 dan §3 sebelum mengirim laporan. Laporan yang hanya
menunjukkan batas dari in-process heuristic yang oleh kebijakan ini
tidak dianggap sebagai boundary akan ditutup sebagai out-of-scope
berdasarkan §3 — tetapi lihat §3.2: laporan semacam itu tetap
disambut sebagai issue atau pull request biasa, hanya saja bukan
melalui kanal security privat.

---

## 2. Trust Model

Thor Agent adalah personal agent single-tenant. Posturnya berlapis,
dan setiap lapisan tidak sama-sama load-bearing. Pelapor maupun
operator sebaiknya menilai lapisan-lapisan ini dengan istilah yang
sama.

### 2.1 Definisi

- **Agent process.** Interpreter Python yang menjalankan Thor Agent,
  termasuk semua modul Python yang dimuatnya (skills, plugins,
  hook handler).
- **Terminal backend.** Target eksekusi yang dapat di-plug untuk
  tool `terminal()`. Default-nya menjalankan perintah langsung di
  host. Backend lain menjalankan perintah di dalam container, cloud
  sandbox, atau remote host.
- **Input surface.** Setiap kanal tempat konten masuk ke context
  agent: input operator, web fetch, email, pesan gateway,
  pembacaan file, respons MCP server, hasil tool.
- **Trust envelope.** Himpunan resource yang secara implisit sudah
  diberikan operator kepada Thor Agent dengan menjalankannya —
  biasanya apa pun yang dapat dijangkau oleh akun user milik
  operator sendiri di host tersebut.
- **Stance.** Pernyataan eksplisit di dokumentasi atau code Thor
  Agent tentang bagaimana lapisan yang mengonsumsi output agent
  (adapter, UI, file writer, shell) harus memperlakukan output
  tersebut — misalnya "dashboard merender output agent sebagai HTML
  yang inert."

### 2.2 Boundary: Isolasi di Level OS

**Satu-satunya security boundary terhadap LLM yang bersifat
adversarial adalah operating system.** Tidak ada apa pun di dalam
agent process yang dapat dianggap sebagai containment — bukan
approval gate, bukan output redaction, bukan pattern scanner mana
pun, bukan allowlist tool mana pun. Setiap komponen in-process yang
menyaring output LLM hanyalah heuristic yang bekerja atas string
yang dipengaruhi penyerang, dan kebijakan ini memperlakukannya
sebagai demikian.

Thor Agent mendukung dua postur isolasi di level OS. Keduanya
menangani ancaman yang berbeda, dan operator sebaiknya memilih
secara sadar.

#### Isolasi terminal-backend

Terminal backend non-default menjalankan perintah shell yang
dihasilkan LLM di dalam container, remote host, atau cloud sandbox.
File tool (`read_file`, `write_file`, `patch`) juga berjalan melalui
backend ini, karena diimplementasikan di atas kontrak shell — tool
tersebut tidak dapat menjangkau path yang tidak diekspos oleh
backend.

Yang dibatasi oleh postur ini: segala hal yang dilakukan agent
dengan mengeluarkan operasi shell atau file. Yang **tidak** dibatasi:
segala hal yang dilakukan agent di dalam proses Python-nya sendiri.
Termasuk di dalamnya tool code-execution (di-spawn sebagai host
subprocess), subprocess MCP (di-spawn dari environment agent),
pemuatan plugin, dispatch hook, dan pemuatan skill (semuanya
di-import ke interpreter agent).

Isolasi terminal-backend adalah postur yang tepat ketika
kekhawatirannya adalah perintah shell destruktif yang dihasilkan
LLM atau penulisan file yang tidak diinginkan oleh file tool,
sementara operatornya sendiri sudah dipercaya.

#### Wrapping seluruh proses

Wrapping seluruh proses menjalankan keseluruhan process tree agent
di dalam sandbox. Setiap code path — shell, code-execution, MCP,
file tool, plugin, hook, pemuatan skill — tunduk pada kebijakan
filesystem, network, process, dan (bila berlaku) inference yang
sama.

Thor Agent mendukung hal ini dengan dua cara:

- **Docker image dan setup Compose milik Thor Agent sendiri.**
  Lebih ringan; agent berjalan di container standar dengan mount dan
  kebijakan network yang dikonfigurasi operator.
- **[NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell)**.
  OpenShell menyediakan sandbox per-session dengan kebijakan
  deklaratif di lapisan filesystem, network (egress L7),
  process/syscall, dan inference-routing. Kebijakan network dan
  inference dapat di-hot-reload. Credential disuntikkan dari
  Provider store dan tidak pernah menyentuh filesystem sandbox.

Di bawah whole-process wrapper, in-process heuristic Thor Agent
(§2.4) berfungsi sebagai pencegahan kecelakaan yang dilapiskan di
atas boundary yang sesungguhnya. Ini adalah postur yang didukung
ketika agent menyerap konten dari surface yang tidak dikendalikan
operator — open web, email masuk, kanal multi-user, MCP server yang
tidak dipercaya — serta untuk deployment produksi atau bersama.

Operator yang menjalankan backend lokal default dengan input surface
yang tidak dipercaya, atau yang menjalankan sandbox terminal-backend
dan berharap sandbox tersebut menahan code path yang tidak melewati
shell, berarti beroperasi di luar postur keamanan yang didukung.

### 2.3 Credential Scoping

Thor Agent memfilter environment yang diteruskan ke komponen
in-process-nya yang ber-trust lebih rendah: subprocess shell,
subprocess MCP, script cron job, dan child code-execution.
Credential seperti API key provider dan token gateway dihapus secara
default; variabel yang secara eksplisit dideklarasikan oleh operator
atau oleh skill yang dimuat akan diteruskan.

Ini mengurangi eksfiltrasi kasual. Ini bukan containment. Komponen
apa pun yang berjalan di dalam agent process (skills, plugins, hook
handler) dapat membaca apa pun yang dapat dibaca agent itu sendiri,
termasuk credential di memory. Mitigasi terhadap komponen
in-process yang terkompromi adalah review operator sebelum instalasi
(§2.4, §2.5), bukan environment scrubbing.

### 2.4 In-Process Heuristic

Komponen berikut menyaring atau memberi peringatan atas perilaku
LLM. Komponen-komponen ini berguna. Namun bukan boundary.

- **Approval gate** mendeteksi pola shell destruktif yang umum dan
  meminta konfirmasi operator sebelum eksekusi. Shell bersifat
  Turing-complete; denylist atas string shell secara struktural
  tidak lengkap. Gate ini menangkap kesalahan pada mode kooperatif,
  bukan output yang bersifat adversarial.
- **Output redaction** menghapus pola yang menyerupai secret dari
  tampilan. Pihak yang bertekad menyisipkan output akan
  mengalahkannya.
- **Skills Guard** memindai konten skill yang dapat diinstal untuk
  mencari pola injeksi. Ini alat bantu review; boundary untuk
  skill pihak ketiga adalah review operator sebelum instalasi.
  Meninjau skill berarti membaca code Python dan script-nya, bukan
  hanya deskripsi SKILL.md-nya — skill mengeksekusi Python
  arbitrer pada waktu import.

### 2.5 Trust Model Plugin

Plugin dimuat ke dalam agent process dan berjalan dengan privilege
penuh agent: plugin dapat membaca credential yang sama, memanggil
tool yang sama, mendaftarkan hook yang sama, dan meng-import modul
yang sama seperti apa pun yang dikirim bersama codebase. Boundary
untuk plugin pihak ketiga adalah review operator sebelum instalasi —
aturan yang sama seperti skill (§2.4), disebut terpisah karena
plugin secara arsitektur lebih berat dan sering menyertakan layanan
background, network listener, serta dependency-nya sendiri.

Plugin yang malicious atau buggy bukanlah kerentanan pada Thor Agent
itu sendiri. Bug pada jalur instalasi atau penemuan plugin di Thor
Agent yang membuat operator tidak dapat melihat apa yang sedang
mereka instal termasuk dalam scope berdasarkan §3.1.

### 2.6 External Surface

**External surface** adalah setiap kanal di luar proses agent lokal
tempat pemanggil dapat mengirimkan pekerjaan agent, menyelesaikan
approval, atau menerima output agent. Setiap surface memiliki model
otorisasi sendiri, tetapi aturan di bawah ini berlaku seragam.

**Surface di Thor Agent:**

- **Adapter platform gateway.** Sebagian besar integrasi messaging
  dikirim sebagai bundled plugin di bawah `plugins/platforms/<name>/`
  (Telegram, Discord, Slack, email, SMS, dan lain-lain). Base type
  bersama dan sekumpulan kecil adapter legacy/direct berada di bawah
  `gateway/platforms/` (`base.py`, Signal, API server, webhook, …),
  dengan penemuan dan deferred loading melalui
  `gateway/platform_registry.py`.
- **Surface HTTP yang terekspos ke jaringan.** Adapter API server,
  plugin dashboard, endpoint HTTP milik plugin kanban, dan plugin
  lain apa pun yang mengikat listening socket.
- **Adapter editor / IDE.** Adapter ACP (`acp_adapter/`) dan
  integrasi setara yang menerima request dari proses client lokal.
- **Gateway TUI (`tui_gateway/`).** Backend JSON-RPC untuk terminal
  UI Ink, diakses melalui IPC lokal.

**Aturan yang berlaku seragam:**

1. **Otorisasi wajib ada di setiap surface yang melewati trust
   boundary.** Untuk surface messaging dan HTTP jaringan, boundary-nya
   adalah jaringan: otorisasi berarti allowlist pemanggil yang
   dikonfigurasi operator. Untuk surface editor dan IPC lokal (ACP,
   gateway TUI), boundary-nya adalah akun user di host: otorisasi
   berarti mengandalkan access control di level OS (permission file,
   bind hanya ke loopback) dan tidak mengekspos surface tersebut di
   luar user lokal tanpa lapisan auth jaringan yang eksplisit.
2. **Allowlist wajib ada untuk setiap adapter yang diaktifkan dan
   terekspos ke jaringan.** Adapter harus menolak mengirimkan
   pekerjaan agent, menyelesaikan approval, atau meneruskan output
   sampai allowlist diatur. Code path yang gagal dalam kondisi
   terbuka (fail open) ketika tidak ada allowlist terkonfigurasi
   adalah bug code yang termasuk scope berdasarkan §3.1.
3. **Session identifier adalah routing handle, bukan boundary
   otorisasi.** Mengetahui session ID pemanggil lain tidak
   memberikan akses ke approval atau output mereka; otorisasi
   selalu diperiksa ulang terhadap allowlist (atau padanan di level
   OS).
4. **Di dalam himpunan yang terotorisasi, semua pemanggil dipercaya
   secara setara.** Thor Agent tidak memodelkan kapabilitas
   per-pemanggil di dalam satu adapter. Operator yang membutuhkan
   pemisahan kapabilitas sebaiknya menjalankan instance agent
   terpisah dengan allowlist terpisah.
5. **Mengikat surface lokal-saja ke interface non-loopback adalah
   keputusan operator yang bersifat break-glass (§3.2).** Dashboard
   dan HTTP server plugin lainnya secara default hanya bind ke
   loopback; mengeksposnya via `--host 0.0.0.0` atau setara membuat
   hardening untuk eksposur publik (§4) menjadi tanggung jawab
   operator.

---

## 3. Scope

### 3.1 In Scope

- Escape dari postur isolasi level OS yang telah dideklarasikan
  (§2.2): code path yang dikendalikan penyerang menjangkau state yang
  seharusnya dibatasi oleh postur tersebut.
- Akses external surface tanpa otorisasi: pemanggil di luar himpunan
  otorisasi yang terkonfigurasi (allowlist, atau padanan level OS
  untuk surface IPC lokal) mengirimkan pekerjaan, menerima output,
  atau menyelesaikan approval (§2.6).
- Credential exfiltration: kebocoran credential operator atau
  material otorisasi session ke tujuan di luar trust envelope,
  melalui mekanisme yang seharusnya mencegahnya (bug environment
  scrubbing, logging di adapter, transport error yang menggugurkan
  credential ke upstream, dan sebagainya).
- Pelanggaran dokumentasi trust model: code yang berperilaku
  bertentangan dengan apa yang diprediksi oleh kebijakan ini,
  dokumentasi Thor Agent sendiri, atau ekspektasi operator yang
  wajar — termasuk kasus ketika Thor Agent telah
  mendokumentasikan stance tentang bagaimana output-nya harus
  dirender oleh lapisan yang mengonsumsinya (dashboard, adapter
  gateway, file writer, shell) lalu ada code path yang melanggar
  stance tersebut.

### 3.2 Out of Scope

"Out of scope" di sini berarti "bukan kerentanan keamanan menurut
kebijakan ini." Bukan berarti "tidak layak dilaporkan." Perbaikan
in-process heuristic, ide hardening, dan perbaikan UX tetap
disambut sebagai issue atau pull request biasa — approval gate
selalu bisa menangkap lebih banyak pola, redaction selalu bisa
menjadi lebih pintar, perilaku adapter selalu bisa diperketat.
Hal-hal itu hanya tidak melewati kanal private-disclosure dan tidak
menerima advisory.

- **Bypass atas in-process heuristic (§2.4)** — bypass regex
  approval-gate, bypass redaction, bypass pola Skills Guard, dan
  laporan serupa terhadap heuristic di masa depan. Komponen ini
  bukan boundary; mengalahkannya bukan kerentanan menurut kebijakan
  ini.
- **Prompt injection itu sendiri.** Membuat LLM mengeluarkan output
  yang tidak biasa — lewat konten yang disuntikkan, halusinasi,
  artefak training, atau penyebab lain apa pun — bukanlah
  kerentanan. "Saya berhasil melakukan prompt injection" tanpa
  hasil §3.1 yang dirantai bukan laporan yang dapat ditindaklanjuti
  menurut kebijakan ini.
- **Konsekuensi dari postur isolasi yang dipilih.** Laporan bahwa
  sebuah code path yang beroperasi dalam cakupan posturnya dapat
  melakukan apa yang diizinkan postur tersebut bukanlah kerentanan.
  Contoh: shell atau file tool menjangkau state host di bawah
  backend lokal; subprocess code-execution atau MCP menjangkau state
  host di bawah isolasi terminal-backend yang hanya men-sandbox
  shell; laporan yang prasyaratnya membutuhkan akses tulis yang
  sudah ada sebelumnya ke file konfigurasi atau credential milik
  operator (hal itu sudah berada di dalam trust envelope).
- **Setting break-glass yang terdokumentasi.** Trade-off yang dipilih
  operator dan secara eksplisit menonaktifkan proteksi: flag
  `--insecure` dan setaranya pada dashboard atau komponen lain,
  approval yang dinonaktifkan, backend lokal di produksi, profil
  development yang melewati keamanan thor-home, dan sejenisnya.
  Laporan terhadap konfigurasi tersebut bukan kerentanan — memang
  itulah fungsi flag tersebut.
- **Skill dan plugin dari kontribusi komunitas.** Skill pihak ketiga
  (termasuk repositori skill komunitas) dan plugin pihak ketiga
  berada di review surface operator, bukan di trust surface Thor
  Agent (§2.4, §2.5). Skill atau plugin yang melakukan hal malicious
  adalah mode kegagalan yang diharapkan dari yang tidak ditinjau,
  bukan kerentanan di Thor Agent. Bug pada jalur instalasi skill
  atau instalasi plugin di Thor Agent yang membuat operator tidak
  dapat melihat apa yang sedang mereka instal termasuk scope
  berdasarkan §3.1.
- **Eksposur publik tanpa kontrol eksternal.** Mengekspos gateway
  atau API ke internet publik tanpa authentication, VPN, atau
  firewall.
- **Pembatasan baca/tulis di level tool pada postur yang
  mengizinkan shell.** Jika sebuah path dapat dijangkau melalui
  terminal tool, laporan bahwa file tool lain juga dapat
  menjangkaunya tidak menambah apa pun.

---

## 4. Deployment Hardening

Keputusan hardening yang paling penting adalah mencocokkan isolasi
(§2.2) dengan tingkat kepercayaan konten yang akan diserap agent.
Selain itu:

- Jalankan agent sebagai user non-root. Container image yang
  disediakan sudah melakukan ini secara default.
- Simpan credential di file credential milik operator dengan
  permission yang ketat, jangan pernah di config utama, jangan
  pernah di version control. Di bawah OpenShell, gunakan Provider
  store daripada file credential di disk.
- Jangan mengekspos gateway atau API ke internet publik tanpa
  perlindungan VPN, Tailscale, atau firewall. Di bawah OpenShell,
  gunakan lapisan network policy untuk membatasi egress.
- Konfigurasikan allowlist pemanggil untuk setiap adapter yang
  terekspos ke jaringan yang Anda aktifkan (§2.6).
- Tinjau skill dan plugin pihak ketiga sebelum instalasi (§2.4,
  §2.5). Untuk skill, ini berarti membaca Python dan script-nya,
  bukan hanya SKILL.md. Laporan Skills Guard dan install audit log
  adalah review surface-nya.
- Thor Agent menyertakan supply-chain guard untuk peluncuran MCP
  server dan untuk perubahan dependency / bundled package di CI;
  lihat `CONTRIBUTING.md` untuk detailnya.

---

## 5. Disclosure

- **Jendela coordinated disclosure:** 90 hari sejak laporan, atau
  sampai fix dirilis, mana yang lebih dulu.
- **Kanal:** thread GHSA atau korespondensi email dengan
  security@thor-agent.local.
- **Kredit:** pelapor dicantumkan dalam release notes kecuali
  meminta anonimitas.
