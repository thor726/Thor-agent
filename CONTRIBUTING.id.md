# Berkontribusi ke Thor Agent

> 🌐 **English:** [CONTRIBUTING.md](CONTRIBUTING.md) — versi asli dokumen ini.

Terima kasih telah berkontribusi ke Thor Agent! Panduan ini mencakup semua yang Anda butuhkan: menyiapkan lingkungan pengembangan, memahami arsitektur, menentukan apa yang akan dibuat, dan membuat PR Anda di-merge.

---

## Prioritas Kontribusi

Kami menghargai kontribusi dalam urutan berikut:

1. **Perbaikan bug** — crash, perilaku yang salah, kehilangan data. Selalu prioritas utama.
2. **Kompatibilitas lintas platform** — macOS, berbagai distro Linux, dan WSL2 di Windows. Kami ingin Thor berjalan di mana saja.
3. **Pengerasan keamanan** — shell injection, prompt injection, path traversal, privilege escalation. Lihat [Keamanan](#pertimbangan-keamanan).
4. **Performa dan ketahanan** — logika retry, penanganan error, degradasi bertahap.
5. **Skill baru** — tetapi hanya yang berguna secara luas. Lihat [Haruskah Jadi Skill atau Tool?](#haruskah-jadi-skill-atau-tool)
6. **Tool baru** — jarang dibutuhkan. Sebagian besar kemampuan sebaiknya menjadi skill. Lihat di bawah.
7. **Dokumentasi** — perbaikan, klarifikasi, contoh baru.

---

## Sebelum Memulai: Cari Dulu

Pencarian singkat sebelum Anda membangun menghemat waktu Anda dan menjaga antrean PR tetap bersih — duplikat sering terjadi di sini, jadi ada baiknya meluangkan waktu sebentar di awal.

- **Cari di PR dan issue yang terbuka *maupun* yang sudah di-merge** untuk topik atau gejala error Anda — pemeriksaan duplikat di template PR baru menyala saat review, setelah Anda terlanjur mengerjakannya:
  ```bash
  gh search issues --repo dwisetyabudi15581/Thor-agent "<kata kunci Anda>"
  gh search prs --repo dwisetyabudi15581/Thor-agent --state all "<kata kunci Anda>"
  ```
  Atau gunakan web UI: [issues](https://github.com/dwisetyabudi15581/Thor-agent/issues?q=) · [PR (semua status)](https://github.com/dwisetyabudi15581/Thor-agent/pulls?q=is%3Apr).
- **Issue tracker bisa tertinggal dari kode.** Banyak fitur yang diminta sudah ada di dalam tree, jadi cari juga di source (`search_files`, atau grep editor Anda) untuk kemampuan tersebut sebelum mengusulkannya.
- **Jika sudah ada PR terbuka yang menanganinya**, pertimbangkan meninjau atau menyempurnakan PR itu daripada membuka duplikat yang bersaing.
- **Untuk pekerjaan yang lebih besar**, komentari issue-nya untuk menandakan Anda sedang mengerjakannya, agar orang lain tidak memulai hal yang sama.

Terkait: #38284 mencakup analog di sisi agent — Thor sendiri memeriksa issue dan PR yang ada sebelum melakukan self-troubleshooting mendalam. Bagian ini adalah pelengkapnya untuk kontributor manusia.

---

## Haruskah Jadi Skill atau Tool?

Ini pertanyaan paling umum dari kontributor baru. Jawabannya hampir selalu **skill**.

### Jadikan Skill ketika:

- Kemampuan dapat dinyatakan sebagai instruksi + perintah shell + tool yang sudah ada
- Ia membungkus CLI atau API eksternal yang bisa dipanggil agent lewat `terminal` atau `web_extract`
- Ia tidak butuh integrasi Python khusus atau pengelolaan API key yang ditanam ke dalam agent
- Contoh: pencarian arXiv, alur kerja git, manajemen Docker, pemrosesan PDF, email lewat tool CLI

### Jadikan Tool ketika:

- Ia membutuhkan integrasi end-to-end dengan API key, alur auth, atau konfigurasi multi-komponen yang dikelola oleh harness agent
- Ia butuh logika pemrosesan khusus yang harus dieksekusi secara presisi setiap kali (bukan "sebisanya" dari interpretasi LLM)
- Ia menangani data biner, streaming, atau event real-time yang tidak bisa lewat terminal
- Contoh: otomatisasi browser (manajemen sesi Browserbase), TTS (encoding audio + pengiriman ke platform), analisis vision (penanganan gambar base64)

### Haruskah Skill-nya di-bundle?

Skill yang di-bundle (di `skills/`) ikut terkirim di setiap instalasi Thor. Skill tersebut harus **berguna secara luas bagi sebagian besar pengguna**:

- Penanganan dokumen, riset web, alur kerja dev yang umum, administrasi sistem
- Digunakan secara rutin oleh beragam orang

Jika skill Anda resmi dan berguna tetapi tidak dibutuhkan semua orang (misalnya integrasi layanan berbayar, dependensi berat), letakkan di **`optional-skills/`** — ikut terkirim dengan repo tetapi tidak aktif secara bawaan. Pengguna dapat menemukannya lewat `thor skills browse` (berlabel "official") dan memasangnya dengan `thor skills install` (tanpa peringatan pihak ketiga, trust bawaan).

Jika skill Anda khusus, kontribusi komunitas, atau niche, lebih cocok untuk **Skills Hub** — unggah ke registry skill dan bagikan di [Discord Thor Agent](https://github.com/dwisetyabudi15581/Thor-agent). Pengguna dapat memasangnya dengan `thor skills install`.

---

## Memory Provider: Kirim sebagai Plugin Mandiri

**Kami tidak lagi menerima memory provider baru ke dalam repo ini.** Kumpulan provider bawaan di `plugins/memory/` (byterover, retaindb) sudah ditutup, dan provider yang sebelumnya ada di tree — hindsight, honcho, supermemory, mem0, openviking, dan holographic — kini dikirim dari katalog plugin. Jika Anda ingin menambahkan backend memory baru, terbitkan sebagai **repo plugin mandiri** yang dipasang pengguna ke `~/.thor/plugins/` (atau lewat entry point pip).

Memory plugin mandiri:

- Mengimplementasikan ABC `MemoryProvider` yang sama (`agent/memory_provider.py`) — `sync_turn`, `prefetch`, `shutdown`, dan opsional `post_setup(thor_home, config)` untuk integrasi wizard setup
- Menggunakan sistem discovery yang sama — `discover_memory_providers()` mengenali mereka dari direktori plugin user/project dan entry point pip
- Terintegrasi dengan `thor memory setup` lewat `post_setup()` — tidak perlu menyentuh kode core
- Dapat mendaftarkan subcommand CLI-nya sendiri lewat `register_cli(subparser)` di berkas `cli.py`
- Mendapat semua lifecycle hook dan plumbing config yang sama seperti provider di dalam tree

PR yang menambahkan direktori baru di bawah `plugins/memory/` akan ditutup dengan arahan untuk menerbitkan provider tersebut sebagai repo tersendiri. Provider di dalam tree yang sudah ada tetap dipertahankan; perbaikan bug untuk mereka tetap diterima.

Ini bukan standar kualitas — ini keputusan soal coupling dan beban maintenance. Memory provider adalah tipe plugin yang paling umum dan semuanya tidak seharusnya tinggal di tree ini.

---

## Integrasi Produk Pihak Ketiga: Kirim sebagai Plugin Mandiri

Aturan yang sama berlaku untuk **plugin apa pun yang mengintegrasikan produk atau proyek orang lain** — backend observability/metrics, konektor SaaS vendor, dashboard analitik, integrasi layanan berbayar, dan sejenisnya. **Hal-hal ini tidak masuk ke repo ini.**

Alasannya beban maintenance, bukan kualitas. Setiap produk eksternal yang diserap ke tree core menjadi tanggung jawab kami agar tetap berjalan di atas basis kode yang bergerak cepat, untuk backend yang bukan milik kami dan tidak bisa kami kendalikan. Thor mengirim banyak hal dan core-nya bergerak cepat; menggabungkan produk pihak ketiga ke dalamnya menciptakan beban terbuka bagi para maintainer.

Terbitkan ini sebagai **repo plugin mandiri**:

- Implementasikan ABC yang relevan dan gunakan jalur discovery plugin yang sudah ada (`~/.thor/plugins/`, `.thor/plugins/` di project, atau entry point pip) — lihat [Build a Thor Plugin](https://thor-agent.thor-agent.local/docs/guides/build-a-thor-plugin)
- Daftarkan lifecycle hook (`pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `on_session_start`, `on_session_end`), tool (`ctx.register_tool`), dan subcommand CLI (`ctx.register_cli_command`) melalui permukaan yang sudah kami ekspos — tidak perlu perubahan core
- Jika plugin Anda membutuhkan kemampuan yang belum diekspos framework, itu adalah feature request untuk **memperluas permukaan plugin generik** (hook baru atau metode `ctx`) — jangan pernah membuat kasus khusus untuk plugin Anda di core
- Promosikan di kanal `#plugins-skills-and-skins` di [Discord Thor Agent](https://github.com/dwisetyabudi15581/Thor-agent) agar pengguna dapat menemukan dan memasangnya

Plugin produk pihak ketiga yang dibangun dengan baik bisa lolos review otomatis dan tetap ditutup karena alasan ini — ini keputusan penempatan, bukan penilaian atas kodenya. PR yang menambahkan direktori semacam itu di bawah `plugins/` akan ditutup dengan arahan untuk menerbitkannya sebagai repo tersendiri.

---

## Mengirim Plugin ke Katalog

Plugin mandiri sampai ke pengguna lewat [katalog plugin](https://thor-agent.thor-agent.local/docs/plugins): sebuah PR ke repo ini yang menambahkan satu berkas `plugin-catalog/<name>.yaml` yang mem-pin repo Anda pada commit tepat. Baca **[Submitting to the plugin catalog](https://thor-agent.thor-agent.local/docs/developer-guide/plugins/catalog-submission)** sebelum membukanya. Dokumen itu mencakup apa yang harus diperiksa lebih dulu (`thor plugins validate --install-deps`), bagaimana review berjalan, dan setiap aturan penerimaan. Aturan kanoniknya ada di [`plugin-catalog/README.md`](plugin-catalog/README.md); jika Anda mengubahnya, ubah blok yang dicerminkan di halaman docs pada PR yang sama (sebuah test menjaga keduanya tetap identik).

Aturan yang paling sering membuat pengajuan dikembalikan: plugin hanya boleh memperluas Thor melalui hook publik, API `ctx.register_*` dan Desktop SDK (tidak boleh mem-patch kode core atau markup Desktop saat runtime), tidak boleh memperbarui dirinya sendiri, harus mendeklarasikan kemampuan yang didaftarkannya, dan harus mengungkapkan perilaku berisiko.

---

## Persiapan Pengembangan

### Prasyarat

| Kebutuhan | Catatan |
|-------------|-------|
| **Git** | Dengan ekstensi `git-lfs` terpasang |
| **Python 3.14** | Proyek membutuhkan `>=3.14,<3.15`; PM menyediakan interpreter yang di-pin |
| **Node.js** | Gunakan pin PM, atau versi yang diterima oleh `package.json` root: `>=26` |
| **pnpm** | Tepat seperti pin `pm/lock.json`; `source ./activate` menyediakannya |

### Lingkungan developer PM

Gunakan [alur kerja developer PM](website/docs/reference/package-management.md#developer-workflow) untuk persiapan, aktivasi, perintah sehari-hari, perubahan dependensi, dan lingkungan test. Pilih home pengembangan Anda sebelum setup agar kode eksperimental tidak memigrasi data produksi.

Aktifkan dari root repositori di setiap shell baru. Aktivasi menjalankan jalur runtime-only milik setup, sehingga ia menyiapkan checkout baru dan menyinkronkan dependensi yang usang.

Bash:

```bash
source ./activate
thor --version
```

fish:

```fish
source ./activate.fish
thor --version
```

PowerShell:

```powershell
. .\activate.ps1
thor --version
```

Jalankan `thor` untuk checkout ini. Aktivasi mendefinisikannya sebagai fungsi untuk worktree ini, sehingga ia menyembunyikan perintah `thor` global atau alias MSIX dan menolak di luar worktree. Aktivasi PM menyinkronkan tool dan dependensi Python sebelum menambahkannya ke shell. Ia tidak memasang workspace JS atau menulis ulang launcher dan konfigurasi shell. `deactivate` mengembalikan lingkungan shell sebelumnya dan menghapus fungsi tersebut.

Untuk menjalankan satu perintah di lingkungan itu tanpa mengaktifkan shell, gunakan `scripts/run-in-thor-env CMD...`.

### Perintah developer (`just`)

`just` tanpa argumen akan menampilkan setiap perintah developer. Setiap resep memanggil satu skrip atau tool di repositori ini, jadi perintah di bawah juga berfungsi tanpa `just`. Hook pre-commit lefthook memanggil resep yang sama.

| Resep | Menjalankan |
|---|---|
| `just setup` | `setup-thor.sh --runtime-only --test-environment` (PowerShell: `setup-thor.ps1 -RuntimeOnly`) |
| `just check` | `scripts/check`, setiap lint check yang memblokir; `just check --only health` memilih check tertentu |
| `just fix` | ruff yang di-pin dengan `--fix`, lalu `pnpm -r fix` |
| `just test <paths>` | `scripts/run_tests.sh <paths>`; menolak mulai tanpa path, bahkan dengan flag |
| `just test-all` | seluruh rangkaian test Python |
| `just js-install`, `just check-js`, `just test-js` | `pnpm install --frozen-lockfile`, `pnpm -r check`, `pnpm -r test` (setelah membangun `@thor/ink`) |
| `just desktop`, `just tui` | dev server desktop dan TUI |
| `just docs-install`, `just docs-build` | `npm ci` dan `build:fast` untuk website |
| `just docs-generate`, `just docs-check` | regenerasi halaman docs skill; lalu setiap check docs yang dijalankan CI (halaman yang di-commit cocok, tautan, diagram) |
| `just lock` | `scripts/relock.sh`: menyegarkan `uv.lock` setelah perubahan `pyproject.toml`, lalu menyinkronkan ulang |
| `just check-repo-guards`, `just check-uv-lock` | langkah history repo-guards, kontributor dan supply-chain, serta check `uv.lock`, melalui `scripts/ci/local_step.sh` terhadap merge base dengan `origin/main` |
| `just check-icons`, `just lint-docker`, `just check-plugin-catalog`, `just check-nix` | check ikon yang di-commit, hadolint dan shellcheck pada input container, validator katalog, `nix flake check` |
| `just test-catalog`, `just test-whatsapp-bridge`, `just test-rust` | test katalog plugin, test node untuk WhatsApp bridge (setelah `just js-install-whatsapp-bridge`), `cargo test --lib` untuk bootstrap installer |

Resep yang menjalankan Python lewat `scripts/run-in-thor-env`, sehingga tetap berfungsi di shell yang belum diaktifkan. Perintah developer baru adalah skrip di bawah `scripts/` plus resep yang memanggilnya; resepnya tidak menyimpan logika.

### Lingkungan pengembangan dan test manual

Gunakan [alur kerja developer PM](website/docs/reference/package-management.md#developer-workflow) untuk menyiapkan Python 3.14 (`>=3.14,<3.15`) terlebih dahulu. Jalankan perintah ini dari checkout tersebut dengan Python yang sudah disiapkan. Pertahankan `THOR_HOME` pengembangan yang sama. PM harus bisa memulai sebelum dapat membangun lingkungan lain. Di Windows, inisialisasi lingkungan build C++ native untuk arsitektur Anda sebelum membangun dependensi sumber.

Bangun interpreter independen untuk test dan tool editor:

```bash
python -m pm.build_env --source . --out .venv --group dev --group test
```

PM membangun dari lock yang di-commit dan memeriksa konsistensi dependensi sebelum mengembalikan interpreter baru. Grup `test` mencakup dependensi test launcher native dan tidak masuk ke runtime aplikasi. Jika test memerlukan fitur lain yang dideklarasikan, tambahkan `--extra`-nya.

Output tidak boleh sudah ada, bahkan sebagai direktori kosong atau symlink. Untuk meregenerasinya setelah perubahan dependensi, hentikan prosesnya dan dengan sengaja hapus hanya lingkungan sekali-pakai itu terlebih dahulu. PM tidak menghapus tujuan yang sudah ada. Jangan menjalankan perintah pip atau uv mentah untuk mengubah lingkungan yang dibangun PM.

Untuk menyimpan lingkungan test di luar checkout, ganti `.venv` dengan path absolut yang baru. Set `THOR_PYTHON` ke interpreter lingkungan tersebut:

- POSIX: `export THOR_PYTHON="/absolute/path/to/thor-dev/bin/python"`
- PowerShell: `$env:THOR_PYTHON = 'C:\absolute\path\to\thor-dev\Scripts\python.exe'`

Runner kanonik menemukan `.venv` repositori secara otomatis. Ia membersihkan `PYTHONPATH`, sehingga pytest harus terpasang di lingkungan interpreter itu sendiri. Lingkungan test ini tidak menggantikan pemilihan aplikasi atau tool store milik PM. Jangan mengarahkan aplikasi bundled ke sana atau memasang ke payload MSIX.

Untuk instance pengembangan yang terisolasi, pilih `THOR_HOME` sekali-pakai sebelum menjalankan perintah source. Gunakan `thor setup` untuk mengonfigurasinya daripada menyalin kredensial produksi ke dalam checkout.

### Workspace JavaScript dan website

Dari root repositori, jalankan `pnpm install --frozen-lockfile` (`just js-install`) untuk workspace JS desktop, TUI, dashboard, dan shared. `pm/lock.json` mem-pin pnpm (`source ./activate`, atau `. .\activate.ps1` di PowerShell, menyediakan versi tepat itu). Instalasi yang menjalankan lifecycle script menolak pnpm lain, termasuk `pnpm install` langsung atau terfilter: skrip `preinstall` root mensyaratkan pnpm dari `pm/lock.json` (dan menolak `npm install`), dan pnpm 10 serta 11 juga menolak rentang `engines.pnpm` root. pnpm 12 melewati `preinstall` root di bawah `--ignore-scripts`, `--lockfile-only` (yang menulis `pnpm-lock.yaml`) dan `pnpm fetch`, sehingga pnpm 12 lain tidak ditolak di sana; CI memasang setiap lockfile yang berubah dengan pnpm yang di-pin di bawah `--frozen-lockfile`. Website adalah proyek npm terpisah (`just docs-install`, `just docs-build`):

```bash
npm ci --prefix website
npm run build:fast --prefix website
```

Di root repositori dan folder workspace JS, npm menolak setiap perintah yang memasang atau menyelesaikan dependensi (`npm install` dengan atau tanpa `--ignore-scripts`, `--package-lock-only` atau `--force`, `npm ci`, `update`, `dedupe`, `uninstall`, `link`): masing-masing folder memiliki `.npmrc` dengan `engine-strict=true`, dan `package.json`-nya mendeklarasikan `engines.npm` yang tidak dipenuhi npm mana pun. `npm rebuild` dan `npm pkg set` tidak ditolak. `--engine-strict=false` eksplisit menimpa penolakan itu.

`npx`, `npm exec` dan `npm run` tetap berfungsi, sehingga server dan tool MCP tetap bisa dijalankan. Tetapi `engine-strict` berlaku di mana saja dalam checkout: di folder-folder ini, dan lewat `.npmrc` root di setiap folder tanpa `package.json` sendiri (`agent/`, `tools/`, `/opt/thor` pada image Docker). Di sana `npx` menolak memasang paket ketika paket itu atau dependensi non-opsional yang dibawanya mendeklarasikan `engines` yang tidak dipenuhi Node atau npm saat ini, padahal di luar checkout ia hanya akan memperingatkan.

Gunakan versi Node yang diterima oleh `engines` pada `package.json` terkait. Dependensi desktop native juga bisa memerlukan toolchain build platform.

Logo dan ikon dihasilkan dari `assets/thor-mark-*.svg` dan `assets/backgrounds/`. `node scripts/generate-icons.mjs` (`just icons`) merendernya dengan Python runtime Thor (`THOR_PYTHON`, jika tidak ada maka `python` di PATH): Pillow dan resvg-py adalah dependensi core. Output yang dihasilkan di-commit dan CI gagal jika kedaluwarsa; jalankan ulang generator dan commit setelah mengubah SVG sumber.

### Menjalankan test

Gunakan runner kanonik di setiap host:

```bash
just test-all
just test tests/agent/ -v
```

Kedua resep memanggil `scripts/run_tests.sh`; `just test` menolak mulai tanpa path, dan `just test-all` menjalankan seluruh rangkaian test.

Di Windows, jalankan skrip itu melalui Bash. Ketika tidak ada `.venv` atau `venv` lokal yang berisi pytest, runner menerima `THOR_PYTHON` eksplisit di atas. Ia membersihkan kredensial, mengisolasi `THOR_HOME`, dan menjalankan setiap berkas test di subprocess terpisah melalui `scripts/run_tests_parallel.py`. Ia tidak menggunakan xdist.

Jalankan check workspace JS yang relevan untuk perubahan JS. E2E instalasi/update native berjalan di host CI sekali-pakai, tidak pernah terhadap aplikasi live milik developer. Lihat [Package management](website/docs/reference/package-management.md) untuk perintah PM dan kepemilikan runtime.

---

## Struktur Proyek

```
thor-agent/
├── run_agent.py              # Facade AIAgent (~1,5k LOC) — turn loop ada di agent/conversation_loop.py + agent/turn_*.py
├── cli.py                    # Kelas ThorCLI — orkestrator CLI interaktif (~4,6k LOC + thor_cli/cli_*_mixin.py)
├── model_tools.py            # Orkestrasi tool (lapisan tipis di atas tools/registry.py)
├── toolsets.py               # Pengelompokan dan preset tool (thor-cli, thor-telegram, dll.)
├── thor_state.py           # Facade SessionDB (~1,4k LOC); implementasi di thor_state_*.py (21 sibling) — pencarian FTS5, judul sesi
├── batch_runner.py           # Pemrosesan batch paralel untuk generasi trajectory
│
├── agent/                    # Internal agent (modul yang diekstrak)
│   ├── conversation_loop.py      # run_conversation() — turn loop agent (fase di turn_*.py)
│   ├── tool_executor.py          # Dispatch tool (tool inline level agent, delegate, registry)
│   ├── session_persistence.py    # Penyimpanan sesi/trajectory
│   ├── prompt_builder.py         # Perakitan system prompt (identitas, skill, file konteks, memory)
│   ├── context_compressor.py     # Auto-summarization saat mendekati batas konteks
│   ├── auxiliary_client.py       # Menyelesaikan klien OpenAI tambahan (summarization, vision)
│   ├── display.py                # KawaiiSpinner, pemformatan progres tool
│   ├── model_metadata.py         # Panjang konteks model, estimasi token
│   └── trajectory.py             # Helper penyimpanan trajectory
│
├── thor_cli/               # Implementasi perintah CLI
│   ├── main.py                   # Entry point, parsing argumen, dispatch perintah
│   ├── cli_*_mixin.py            # Mixin ThorCLI (slash command, display, sesi, ...)
│   ├── config.py                 # Manajemen config, migrasi, definisi env var
│   ├── setup.py                  # Wizard setup interaktif
│   ├── auth.py                   # Resolusi provider, OAuth, Thor Portal (facade + sibling auth_*.py)
│   ├── models.py                 # Daftar pemilihan model OpenRouter
│   ├── banner.py                 # Banner selamat datang, ASCII art
│   ├── commands.py               # Registry slash command terpusat (CommandDef), autocomplete, helper gateway
│   ├── callbacks.py              # Callback interaktif (clarify, sudo, approval)
│   ├── doctor.py                 # Diagnostik
│   ├── skills_hub.py             # CLI Skills Hub + slash command /skills
│   ├── skin_engine.py            # Mesin skin/tema — kustomisasi visual CLI berbasis data
│   ├── web_server.py             # Server dashboard (facade + sibling web_server_*.py)
│   └── web_routers/              # Router FastAPI dashboard (satu berkas per permukaan)
│
├── tools/                    # Implementasi tool (mendaftar sendiri)
│   ├── registry.py               # Registry tool terpusat (schema, handler, dispatch)
│   ├── approval.py               # Deteksi perintah berbahaya + approval per sesi
│   ├── terminal_tool.py          # Orkestrasi terminal (sudo, siklus hidup env, backend)
│   ├── file_operations.py        # read_file, write_file, search, patch, dll.
│   ├── web_tools.py              # web_search, web_extract (Parallel/Firecrawl + summarization Gemini)
│   ├── vision_tools.py           # Analisis gambar lewat model multimodal
│   ├── delegate_tool.py          # Spawning subagent dan eksekusi task paralel
│   ├── code_execution_tool.py    # Python tersandbox dengan akses tool RPC (allowlist env di code_execution_env.py)
│   ├── mcp_tool.py               # Klien MCP (facade + sibling mcp_tool_*.py: config, discovery, transport, ...)
│   ├── browser_use_cli.py        # browser_exec (Python di atas CDP); sesi di browser_session*.py, launcher di browser_launcher.py
│   ├── session_search_tool.py    # Cari percakapan lampau dengan FTS5 + jendela ter-anchor
│   ├── cronjob_tools.py          # Manajemen task terjadwal
│   ├── skill_tools.py            # Pencarian, pemuatan, pengelolaan skill
│   └── environments/             # Backend eksekusi terminal
│       ├── base.py                   # ABC BaseEnvironment
│       ├── local.py, docker.py, ssh.py, modal.py, daytona.py
│
├── gateway/                  # Gateway pesan
│   ├── run.py                    # Facade GatewayRunner (~5,5k LOC); fase di run_*.py (startup, inbound, turn, busy, ...)
│   ├── slash_commands_*.py       # Mixin handler slash command gateway
│   ├── config.py                 # Resolusi konfigurasi platform
│   ├── session.py                # Penyimpanan sesi, prompt konteks, reset eksplisit (+ sibling session_*.py)
│   └── platforms/                # Adaptor platform
│       ├── telegram.py, discord_adapter.py, slack.py, whatsapp.py
│
├── scripts/                  # Skrip installer dan bridge
│   ├── install.sh                # Installer Linux/macOS
│   ├── install.ps1               # Installer PowerShell Windows
│   └── whatsapp-bridge/          # Bridge WhatsApp Node.js (Baileys)
│
├── skills/                   # Skill bundled (disalin ke ~/.thor/skills/ saat instalasi)
├── optional-skills/          # Skill opsional resmi (dapat ditemukan lewat hub, tidak aktif secara bawaan)
├── tests/                    # Rangkaian test
├── website/                  # Situs dokumentasi (thor-agent.thor-agent.local)
│
├── cli-config.yaml.example   # Contoh konfigurasi (disalin ke ~/.thor/config.yaml)
└── AGENTS.md                 # Panduan pengembangan untuk asisten coding AI
```

### Konfigurasi pengguna (disimpan di `~/.thor/`)

| Path | Kegunaan |
|------|---------|
| `~/.thor/config.yaml` | Pengaturan (model, terminal, toolset, kompresi, dll.) |
| `~/.thor/.env` | API key dan secret |
| `~/.thor/auth.json` | Kredensial OAuth (Thor Portal) |
| `~/.thor/skills/` | Semua skill aktif (bundled + terpasang dari hub + dibuat agent) |
| `~/.thor/memories/` | Memory persisten (MEMORY.md, USER.md) |
| `~/.thor/state.db` | Basis data sesi SQLite |
| `~/.thor/sessions/` | Indeks routing gateway (`sessions.json`), breadcrumb dump request, transkrip `*.jsonl` gateway, dan ekspor `/save` eksplisit. Snapshot JSON otomatis per sesi tidak lagi ditulis; state.db bersifat kanonik. |
| `~/.thor/cron/` | Data job terjadwal |
| `~/.thor/whatsapp/session/` | Kredensial bridge WhatsApp |

---

## Ikhtisar Arsitektur

### Core Loop

```
Pesan pengguna → AIAgent._run_agent_loop()
  ├── Bangun system prompt (prompt_builder.py)
  ├── Bangun API kwargs (model, messages, tools, konfigurasi reasoning)
  ├── Panggil LLM (API yang kompatibel dengan OpenAI)
  ├── Jika ada tool_calls di respons:
  │     ├── Eksekusi setiap tool lewat dispatch registry
  │     ├── Tambahkan hasil tool ke percakapan
  │     └── Kembali ke pemanggilan LLM
  ├── Jika respons teks:
  │     ├── Simpan sesi ke DB
  │     └── Kembalikan final_response
  └── Kompresi konteks jika mendekati batas token
```

### Pola Desain Utama

- **Tool yang mendaftar sendiri**: Setiap berkas tool memanggil `registry.register()` saat import. `model_tools.py` memicu discovery dengan mengimpor semua modul tool.
- **Pengelompokan toolset**: Tool dikelompokkan ke dalam toolset (`web`, `terminal`, `file`, `browser`, dll.) yang dapat diaktifkan/dinonaktifkan per platform.
- **Persistensi sesi**: Semua percakapan disimpan di SQLite (`thor_state.py`) dengan pencarian full-text dan judul sesi yang unik. Snapshot JSON otomatis per sesi telah dihapus. Berkas yang ada dibiarkan utuh; gunakan `/save json` atau `thor sessions export` untuk ekspor eksplisit.
- **Injeksi sementara (ephemeral)**: System prompt dan pesan prefill diinjeksi saat pemanggilan API, tidak pernah dipersistensikan ke basis data atau log.
- **Abstraksi provider**: Agent bekerja dengan API apa pun yang kompatibel dengan OpenAI. Resolusi provider terjadi saat init (OAuth Thor Portal, API key OpenRouter, atau endpoint kustom).
- **Routing provider**: Saat menggunakan OpenRouter, `provider_routing` di config.yaml mengendalikan pemilihan provider (urut berdasarkan throughput/latency/price, izinkan/abaikan provider tertentu, kebijakan retensi data). Ini diinjeksi sebagai `extra_body.provider` dalam permintaan API.

---

## Gaya Kode

- **PEP 8** dengan pengecualian praktis (kami tidak menegakkan panjang baris yang ketat)
- **Komentar**: Hanya saat menjelaskan maksud yang tidak jelas, trade-off, atau keanehan API. Jangan menarasikan apa yang dilakukan kode — `# increment counter` tidak menambah apa pun
- **Penanganan error**: Tangkap exception yang spesifik. Catat dengan `logger.warning()`/`logger.error()` — gunakan `exc_info=True` untuk error tak terduga agar stack trace muncul di log
- **Pesan error**: setiap pesan error yang menghadap pengguna menyebutkan penyebab sebenarnya dan langkah perbaikannya — bukan gejala terdekatnya. API key yang hilang adalah "no OpenRouter API key configured — set `OPENROUTER_API_KEY`", bukan "payment/credit error"; permintaan yang gagal mencatat kelas dan pesan exception (secret disamarkan) alih-alih alasan kosong; pekerjaan panjang yang timeout melaporkan timeout dan ke mana pekerjaan itu pergi, bukan string derau fallback-routing. Jika Anda tahu penyebabnya, sebutkan; jika tidak, sebutkan apa yang Anda ketahui plus apa yang harus diperiksa — jangan pernah placeholder yang menunjuk ke tempat lain.
- **Lintas platform**: Jangan pernah mengasumsikan Unix. Lihat [Kompatibilitas Lintas Platform](#kompatibilitas-lintas-platform)
- **Ratchet kesehatan kode**: `python scripts/check` menjalankan setiap lint check yang memblokir di CI, dengan tool yang di-pin sama. Untuk menjalankannya otomatis, `python scripts/check --install-hook pre-push` menilai ujung setiap branch yang Anda push, sebagaimana CI menilai PR secara keseluruhan, bukan tiap commit perantara (`--install-hook` saja menjalankannya di setiap commit, menilai apa yang Anda stage; `--uninstall-hook` menghapus keduanya; `--no-verify` melewati sekali). Hook mencakup setiap worktree pada klon Anda, menilai setiap ujung yang di-push dengan checker milik ujung itu sendiri, mengutamakan Python `.venv`/`venv` repositori (3.11+), dan membutuhkan ruff 0.15.10 atau `uv` di `PATH`; jalankan ulang `--install-hook` setelah pull untuk menyegarkan skrip hook. Bagian kesehatan kodenya memberi setiap fungsi dan berkas batasnya sendiri: fungsi baru tetap pada kompleksitas siklomatik ≤ 20, ≤ 300 baris dan nesting ≤ 6, berkas pada ≤ 2.000 baris, dan kode yang sudah melewati target hanya boleh mengecil (berkas yang sudah melewati 2.000 baris tidak boleh bertambah: imbangi pertumbuhannya dengan memindahkan fungsi yang ada ke sibling `<stem>_<topic>`, atau letakkan test baru di berkas test baru). Aturan pola (`except Exception` buta, timeout yang hilang, bahaya cakupan profil seperti `~/.thor` yang di-hardcode atau env var `THOR_*` baru) melacak setiap pelanggaran yang ada di tempatnya, sehingga utang yang ada tidak pernah memblokir Anda, tetapi instance baru memblokir, bahkan yang menggantikan pelanggaran identik yang Anda hapus. Memindahkan kode mempertahankan riwayatnya: fungsi atau pernyataan level modul yang dipindah ke berkas lain mempertahankan batas dan pelanggaran yang dimilikinya, begitu juga fungsi yang dipindah dan sedikit Anda edit, kecuali fungsi dengan nama itu sudah ada di tujuan (yang diedit lalu dinilai terhadap batas fungsi tersebut). Fungsi yang Anda ganti nama sekaligus edit adalah kode baru, begitu juga salinan yang meninggalkan aslinya di tempatnya. Berkas yang tidak dapat di-parse atau diukur oleh checker akan gagal. Kompleksitas TypeScript mengikuti aturan `complexity` ESLint kecuali di mana `scripts/code_health/ts_units.mjs` menyatakan lain. Setiap temuan mencetak perbaikannya; exception yang sah memerlukan komentar `# health: allow <RULE> -- <why>` pada baris itu (atau pada baris khusus komentar tepat di atasnya), yang dibaca reviewer; `# noqa` dari ruff tidak menggugurkan temuan ratchet, dan penangkapan luas yang mencatat log harus mempertahankan traceback (`logger.exception` atau `exc_info=True`). Aturan heuristik dicetak sebagai peringatan sampai replay beku dari PR yang sudah di-merge menunjukkan bahwa aturan itu cukup presisi untuk memblokir. Aturan dan target: `scripts/code_health/config.py`. Maintainer mengalihkan seluruh ratchet dengan `ENFORCEMENT` di sana (`blocking`, `advisory` atau `off`): nilainya selalu dibaca dari main (CI: parent pertama dari merge commit; run lokal: `origin/main`), tidak pernah dari branch yang sedang diuji, sehingga satu commit satu baris ke main mencapai setiap PR terbuka pada run CI berikutnya (re-run memakai merge commit lama) dan setiap hook lokal setelah fetch, dan sebuah PR tidak dapat melonggarkan pemeriksaannya sendiri; satu aturan dapat diturunkan dengan `blocking=False`.

### Gagal dengan lantang di batas integrasi

**Gagal dengan lantang di batas integrasi.** Ketika nilai konfigurasi, kredensial, atau input dari pengguna tidak dapat digunakan — token placeholder, field wajib yang kosong, angka di luar rentang seperti `TERMINAL_TIMEOUT=0` — tolak di tempat ia dibaca dan sebutkan masalahnya: error yang jelas saat startup atau di jalur penulisan, bukan no-op senyap yang mengubah kebingungan menjadi sesi debugging di kemudian hari. Setiap batas memvalidasi nilainya sendiri di tempat; sengaja tidak ada helper `fail_loud` bersama, karena satu bentuk call-site tidak cocok untuk semua — aturannya tentang perilaku yang dilihat pengguna, bukan fungsi yang Anda panggil. Default senyap hanya dapat diterima bila default tersebut adalah pilihan produk yang disengaja dan didokumentasikan di referensi config; selain itu semuanya harus memberi tahu pengguna apa yang rusak, di mana, dan apa yang harus diatur.

---

## Menambahkan Tool Baru

Sebelum menulis tool, tanyakan: [haruskah ini menjadi skill saja?](#haruskah-jadi-skill-atau-tool)

Tool mendaftar sendiri ke registry terpusat. Setiap berkas tool menempatkan schema, handler, dan registrasinya bersama-sama:

```python
"""my_tool — Deskripsi singkat tentang apa yang dilakukan tool ini."""

import json
from tools.registry import registry


def my_tool(param1: str, param2: int = 10, **kwargs) -> str:
    """Handler. Mengembalikan hasil string (sering JSON)."""
    result = do_work(param1, param2)
    return json.dumps(result)


MY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "Apa yang dilakukan tool ini dan kapan agent harus menggunakannya.",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Apa itu param1"},
                "param2": {"type": "integer", "description": "Apa itu param2", "default": 10},
            },
            "required": ["param1"],
        },
    },
}


def _check_requirements() -> bool:
    """Kembalikan True jika dependensi tool ini tersedia."""
    return True


registry.register(
    name="my_tool",
    toolset="my_toolset",
    schema=MY_TOOL_SCHEMA,
    handler=lambda args, **kw: my_tool(**args, **kw),
    check_fn=_check_requirements,
)
```

**Sambungkan ke toolset (wajib):** Tool bawaan ditemukan secara otomatis: berkas `tools/*.py` apa pun yang memuat pemanggilan `registry.register(...)` di level atas akan diimpor oleh `discover_builtin_tools()` di `tools/registry.py` saat `model_tools` dimuat. **Tidak ada** daftar import manual di `model_tools.py` yang perlu dipelihara.

Anda tetap harus menambahkan nama tool ke daftar yang sesuai di `toolsets.py` (misalnya `_THOR_CORE_TOOLS` atau toolset khusus); jika tidak, tool akan terdaftar tetapi tidak pernah diekspos ke agent. Jika Anda memperkenalkan toolset baru, tambahkan di `toolsets.py` dan sambungkan ke preset platform yang relevan.

Lihat `AGENTS.md` (bagian **Adding New Tools**) untuk path yang sadar profil dan panduan plugin vs core.

---

## Menambahkan Skill

Skill bundled ada di `skills/` yang diorganisasi per kategori. Skill opsional resmi menggunakan struktur yang sama di `optional-skills/`:

```
skills/
├── research/
│   └── arxiv/
│       ├── SKILL.md              # Wajib: instruksi utama
│       └── scripts/              # Opsional: skrip pembantu
│           └── search_arxiv.py
├── productivity/
│   └── ocr-and-documents/
│       ├── SKILL.md
│       ├── scripts/
│       └── references/
└── ...
```

### Format SKILL.md

```markdown
---
name: my-skill
description: Deskripsi singkat (ditampilkan di hasil pencarian skill)
version: 1.0.0
author: Nama Anda
license: MIT
platforms: [macos, linux]          # Opsional — batasi ke platform OS tertentu
                                   #   Valid: macos, linux, windows
                                   #   Hilangkan untuk dimuat di semua platform (bawaan)
required_environment_variables:    # Opsional — metadata setup-on-load yang aman
  - name: MY_API_KEY
    prompt: API key
    help: Dari mana mendapatkannya
    required_for: fungsionalitas penuh
prerequisites:                     # Opsional, kebutuhan runtime gaya lama
  env_vars: [MY_API_KEY]           #   Alias yang kompatibel mundur untuk required env vars
  commands: [curl, jq]             #   Hanya saran; tidak menyembunyikan skill
metadata:
  thor:
    tags: [Kategori, Subkategori, Kata Kunci]
    related_skills: [nama-skill-lain]
    fallback_for_toolsets: [web]       # Opsional — tampilkan hanya saat toolset tidak tersedia
    requires_toolsets: [terminal]      # Opsional — tampilkan hanya saat toolset tersedia
---

# Judul Skill

Intro singkat.

## When to Use
Kondisi pemicu — kapan agent harus memuat skill ini?

## Prerequisites
Env var, langkah instalasi, penyiapan MCP, sumber API key.

## How to Run
Pemanggilan kanonik lewat tool `terminal`.

## Quick Reference
Tabel perintah atau pemanggilan API yang umum.

## Procedure
Instruksi langkah demi langkah yang diikuti agent.

## Pitfalls
Mode kegagalan yang diketahui dan cara menanganinya.

## Verification
Bagaimana agent memastikan bahwa itu berhasil.
```

### Skill khusus platform

Skill dapat mendeklarasikan platform OS mana yang didukung melalui field frontmatter `platforms`. Skill dengan field ini otomatis disembunyikan dari system prompt, `skills_list()`, dan slash command pada platform yang tidak kompatibel.

```yaml
platforms: [macos]            # Hanya macOS (mis. iMessage, Apple Reminders)
platforms: [macos, linux]     # macOS dan Linux
platforms: [windows]          # Hanya Windows
```

Jika field dihilangkan atau kosong, skill dimuat di semua platform (kompatibel mundur). Lihat `skills/apple/` untuk contoh skill khusus macOS.

### Aktivasi skill bersyarat

Skill dapat mendeklarasikan kondisi yang mengendalikan kapan mereka muncul di system prompt, berdasarkan tool dan toolset mana yang tersedia di sesi saat ini. Ini terutama digunakan untuk **skill fallback** — alternatif yang hanya boleh ditampilkan ketika tool utama tidak tersedia.

Empat field didukung di bawah `metadata.thor`:

```yaml
metadata:
  thor:
    fallback_for_toolsets: [web]      # Tampilkan HANYA saat toolset ini tidak tersedia
    requires_toolsets: [terminal]     # Tampilkan HANYA saat toolset ini tersedia
    fallback_for_tools: [web_search]  # Tampilkan HANYA saat tool spesifik ini tidak tersedia
    requires_tools: [terminal]        # Tampilkan HANYA saat tool spesifik ini tersedia
```

**Semantik:**
- `fallback_for_*`: Skill ini adalah cadangan. Ia **disembunyikan** ketika tool/toolset yang terdaftar tersedia, dan **ditampilkan** ketika tidak tersedia. Gunakan ini untuk alternatif gratis bagi tool premium.
- `requires_*`: Skill ini membutuhkan tool tertentu agar berfungsi. Ia **disembunyikan** ketika tool/toolset yang terdaftar tidak tersedia. Gunakan ini untuk skill yang bergantung pada kemampuan spesifik (misalnya skill yang hanya masuk akal dengan akses terminal).
- Jika keduanya ditentukan, kedua kondisi harus terpenuhi agar skill muncul.
- Jika tidak ada yang ditentukan, skill selalu ditampilkan (kompatibel mundur).

**Contoh:**

```yaml
# Pencarian DuckDuckGo — ditampilkan saat Firecrawl (toolset web) tidak tersedia
metadata:
  thor:
    fallback_for_toolsets: [web]

# Skill smart home — hanya berguna saat terminal tersedia
metadata:
  thor:
    requires_toolsets: [terminal]

# Fallback browser lokal — ditampilkan saat Browserbase tidak tersedia
metadata:
  thor:
    fallback_for_toolsets: [browser]
```

Penyaringan terjadi saat pembangunan prompt di `agent/prompt_builder.py`. Fungsi `build_skills_system_prompt()` menerima himpunan tool dan toolset yang tersedia dari agent dan menggunakan `_skill_should_show()` untuk mengevaluasi kondisi setiap skill.

### Metadata setup skill

Skill dapat mendeklarasikan metadata setup-on-load yang aman melalui field frontmatter `required_environment_variables`. Nilai yang hilang tidak menyembunyikan skill dari discovery; mereka memicu prompt aman yang hanya berjalan di CLI ketika skill benar-benar dimuat.

```yaml
required_environment_variables:
  - name: TENOR_API_KEY
    prompt: Tenor API key
    help: Dapatkan kunci dari https://developers.google.com/tenor
    required_for: fungsionalitas penuh
```

Pengguna dapat melewati setup dan tetap memuat skill tersebut. Thor hanya mengekspos metadata (`stored_as`, `skipped`, `validated`) ke model — tidak pernah nilai secretnya.

`prerequisites.env_vars` gaya lama tetap didukung dan dinormalisasi ke representasi baru.

```yaml
prerequisites:
  env_vars: [TENOR_API_KEY]       # Alias gaya lama untuk required_environment_variables
  commands: [curl, jq]            # Pemeriksaan CLI yang bersifat saran
```

Sesi gateway dan pesan tidak pernah mengumpulkan secret secara in-band; mereka menginstruksikan pengguna untuk menjalankan `thor setup` atau memperbarui `~/.thor/.env` secara lokal.

**Kapan mendeklarasikan required environment variables:**
- Skill menggunakan API key atau token yang harus dikumpulkan secara aman saat dimuat
- Skill tetap bisa berguna jika pengguna melewati setup, tetapi mungkin terdegradasi secara bertahap

**Kapan mendeklarasikan prasyarat perintah:**
- Skill bergantung pada tool CLI yang mungkin belum terpasang (mis. `himalaya`, `openhue`, `ddgs`)
- Perlakukan pemeriksaan perintah sebagai panduan, bukan penyembunyian saat discovery

Lihat `optional-skills/media/gif-search/` dan `skills/email/himalaya/` untuk contoh.

### Standar penulisan skill (WAJIB)

Setiap skill baru atau yang dimodernisasi — bundled, opsional, atau kontribusi — harus memenuhi standar ini sebelum di-merge. Reviewer menolak PR yang melanggarnya.

1. **`description` ≤ 60 karakter, satu kalimat, diakhiri titik.** Deskripsi yang panjang membebani UI daftar skill dan mengencerkan perhatian model saat banyak skill dimuat. Nyatakan kemampuannya, bukan implementasinya. Tanpa kata pemasaran ("powerful", "comprehensive", "seamless", "advanced"). Jangan mengulang nama skill. Verifikasi dengan:
   ```python
   import re, pathlib
   m = re.search(r'^description: (.*)$',
                 pathlib.Path('skills/<cat>/<name>/SKILL.md').read_text(),
                 re.MULTILINE)
   assert len(m.group(1)) <= 60, len(m.group(1))
   ```

   Baik: `Search arXiv papers by keyword, author, category, or ID.`
   Buruk: `A powerful and comprehensive skill that allows the agent to search arXiv for relevant academic papers using various criteria including keywords, authors, and categories.`

2. **Tool yang dirujuk dalam prosa SKILL.md harus berupa tool native Thor atau server MCP yang memang diharapkan skill tersebut.** Ketika skill membutuhkan kemampuan, tunjuk tool yang tepat dengan namanya di dalam backtick: `` `terminal` ``, `` `web_extract` ``, `` `web_search` ``, `` `read_file` ``, `` `write_file` ``, `` `patch` ``, `` `search_files` ``, `` `vision_analyze` ``, `` `browser_exec` ``, `` `delegate_task` ``, `` `image_generate` ``, `` `text_to_speech` ``, `` `cronjob` ``, `` `memory` ``, `` `skill_view` ``, `` `todo` ``, `` `execute_code` ``.

   JANGAN menyebut utilitas shell yang sudah dibungkus agent:

   | Jangan katakan | Katakan |
   |---|---|
   | `grep`, `rg` | `search_files` |
   | `cat`, `head`, `tail` | `read_file` |
   | `sed`, `awk` | `patch` |
   | `find`, `ls` | `search_files` (dengan `target='files'`) |
   | `curl` untuk ekstraksi konten | `web_extract` |
   | `echo > file`, `cat <<EOF` | `write_file` |

   Jika skill bergantung pada server MCP, sebutkan nama server MCP tersebut dan dokumentasikan penyiapannya di `## Prerequisites`. CLI pihak ketiga (mis. `ffmpeg`, `gh`, SDK tertentu) boleh dipanggil dari dalam berkas skrip, tetapi prosanya harus membingkai interaksi sebagai "panggil melalui tool `terminal`", bukan sebagai sesi shell manual.

3. **Gerbang `platforms:` diaudit terhadap import skrip yang sebenarnya.** Skill yang menggunakan primitif khusus POSIX (`fcntl`, `termios`, `os.setsid`, `os.kill(pid, 0)` untuk cek hidup, `/proc`, path `/tmp` yang di-hardcode, `signal.SIGKILL`, heredoc bash, `osascript`, `apt`, `systemctl`) harus mendeklarasikan platform yang didukung lewat frontmatter `platforms:`. Sikap bawaannya adalah memperbaikinya agar lintas platform terlebih dahulu — `tempfile.gettempdir()`, `pathlib.Path`, `psutil.pid_exists()`, penyaringan level Python alih-alih `grep`. Batasi ke himpunan yang lebih sempit hanya ketika dependensinya memang terikat platform (mis. `osascript` hanya macOS, `/proc` hanya Linux). <!-- no-tmp: ok — names the POSIX-only anti-pattern reviewers look for -->

4. **`author` mencantumkan kontributor manusia lebih dulu.** Untuk kontribusi eksternal, nama asli + handle GitHub kontributor didahulukan (`Jane Doe (jane-doe)`); "Thor Agent" adalah kolaborator sekunder. Jika commit kontributor menampilkan "Thor Agent" sebagai author karena mereka memakai Thor untuk menyusun skill itu, ganti dengan nama asli mereka — beri kredit pada manusia, bukan tool.

5. **Isi SKILL.md menggunakan urutan bagian modern.** Judul `# <Skill> Skill`, intro 2-3 kalimat yang menyatakan apa yang dilakukannya dan apa yang tidak, lalu:
   - `## When to Use` — kondisi pemicu
   - `## Prerequisites` — env var, langkah instalasi, penyiapan MCP, sumber API key
   - `## How to Run` — pemanggilan kanonik lewat tool `terminal`
   - `## Quick Reference` — referensi perintah/API yang ringkas
   - `## Procedure` — langkah bernomor dengan perintah siap tempel
   - `## Pitfalls` — batasan yang diketahui, rate limit, hal yang tampak rusak padahal tidak
   - `## Verification` — satu perintah yang membuktikan skill berfungsi

   Targetkan ~200 baris untuk skill kompleks, ~100 baris untuk yang sederhana. Pangkas basa-basi intro yang berulang, prosa pemasaran, dan penjelasan ulang env var yang sudah didokumentasikan di `## Prerequisites`.

6. **Skrip di `scripts/`, referensi di `references/`, template di `templates/`.** Jangan berharap model menulis parser, penelusur XML, atau logika non-trivial secara inline setiap pemanggilan — sertakan skrip pembantu. Rujuk skrip dari SKILL.md dengan path relatif terhadap direktori skill.

7. **Test berada di `tests/skills/test_<skill>_skill.py`** dan hanya menggunakan stdlib + pytest + `unittest.mock`. Tanpa panggilan jaringan langsung. Jalankan lewat `scripts/run_tests.sh tests/skills/test_<skill>_skill.py -q`. Harus lolos di env CI hermetik (tidak ada API key yang bocor). Gunakan `monkeypatch` dan `tmp_path` untuk dependensi env var atau filesystem.

8. **Penambahan `.env.example` terisolasi pada blok yang dibatasi dengan jelas.** Jangan sentuh berkas di sekitarnya — versi `.env.example` dari kontributor biasanya sudah usang, dan suntingan di luar blok milik skill akan dibuang saat salvage. Beri komentar pada semua nilai dengan `#` (itu dokumentasi, bukan config hidup).

### Panduan skill

- **Tanpa dependensi eksternal kecuali benar-benar diperlukan.** Utamakan stdlib Python, curl, dan tool Thor yang sudah ada (`web_extract`, `terminal`, `read_file`).
- **Pengungkapan bertahap.** Letakkan alur kerja yang paling umum di awal. Kasus tepi dan penggunaan lanjutan di bagian bawah.
- **Sertakan skrip pembantu** untuk parsing XML/JSON atau logika kompleks — jangan berharap LLM menulis parser inline setiap kali.
- **Uji coba.** Jalankan `thor --toolsets skills -q "Use the X skill to do Y"` dan pastikan agent mengikuti instruksi dengan benar.

---

## Menambahkan Skin / Tema

Thor menggunakan sistem skin berbasis data — tidak perlu perubahan kode untuk menambahkan skin baru.

**Opsi A: Skin pengguna (berkas YAML)**

Buat `~/.thor/skins/<name>.yaml`:

```yaml
name: mytheme
description: Deskripsi singkat tema

colors:
  banner_border: "#HEX"     # Warna batas panel
  banner_title: "#HEX"      # Warna judul panel
  banner_accent: "#HEX"     # Warna header bagian
  banner_dim: "#HEX"        # Warna teks redup/muted
  banner_text: "#HEX"       # Warna teks isi
  response_border: "#HEX"   # Batas kotak respons

spinner:
  waiting_faces: ["(⚔)", "(⛨)"]
  thinking_faces: ["(⚔)", "(⌁)"]
  thinking_verbs: ["forging", "plotting"]
  wings:                     # Dekorasi kiri/kanan opsional
    - ["⟪⚔", "⚔⟫"]

branding:
  agent_name: "My Agent"
  welcome: "Pesan selamat datang"
  response_label: " ⚔ Agent "
  prompt_symbol: "⚔"

tool_prefix: "╎"             # Prefiks baris output tool
```

Semua field opsional — nilai yang hilang diwarisi dari skin bawaan.

**Opsi B: Skin bawaan**

Tambahkan ke dict `_BUILTIN_SKINS` di `thor_cli/skin_engine.py`. Gunakan schema yang sama seperti di atas tetapi sebagai dict Python. Skin bawaan ikut terkirim dengan paket dan selalu tersedia.

**Mengaktifkan:**
- CLI: `/skin mytheme` atau set `display.skin: mytheme` di config.yaml
- Config: `display: { skin: mytheme }`

Lihat `thor_cli/skin_engine.py` untuk schema lengkap dan skin yang sudah ada sebagai contoh.

---

## Kompatibilitas Lintas Platform

Thor berjalan di Linux, macOS, dan Windows native (plus WSL2). Saat menulis kode
yang menyentuh OS, asumsikan *platform apa pun* bisa melewati jalur kode Anda.

> **Sebelum PR:** jalankan `scripts/check-windows-footguns.py` untuk menangkap
> pola tidak aman di Windows yang umum pada diff Anda. Berbasis grep dan murah;
> CI juga menjalankannya di setiap PR.

### Aturan kritis

1. **Jangan pernah memanggil `os.kill(pid, 0)` untuk cek hidup.** `os.kill(pid, 0)`
   adalah idiom POSIX standar untuk memeriksa "apakah PID ini hidup" — sinyal 0
   adalah pemeriksaan izin yang tidak melakukan apa-apa. **Di Windows itu BUKAN no-op.** `os.kill`
   Python di Windows memetakan `sig=0` ke `CTRL_C_EVENT` (keduanya bertabrakan pada
   nilai integer 0) dan merutekannya melalui `GenerateConsoleCtrlEvent(0, pid)`,
   yang menyiarkan Ctrl+C ke **seluruh grup proses konsol** yang memuat
   PID target. "Cek apakah hidup" diam-diam berubah menjadi "membunuh target dan
   sering juga proses tak terkait yang berbagi konsolnya." Lihat [bpo-14484](https://bugs.python.org/issue14484)
   (terbuka sejak 2012 — tidak akan pernah diperbaiki karena alasan kompatibilitas).

   **Lebih baik:** gunakan `psutil` (dependensi core — selalu tersedia):

   ```python
   import psutil
   if psutil.pid_exists(pid):
       # proses hidup — aman di setiap platform
       ...
   ```

   Jika Anda memang membutuhkan pembungkus thor (ia punya fallback
   stdlib untuk import fase scaffold sebelum PM menyelesaikan persiapan dependensi), gunakan
   `gateway.status._pid_exists(pid)`. Ia memanggil `psutil.pid_exists` lebih dulu
   dan jatuh ke tarian `OpenProcess + WaitForSingleObject` buatan sendiri
   di Windows hanya ketika psutil entah bagaimana hilang.

   Grep audit untuk callsite baru: `rg "os\.kill\([^,]+,\s*0\s*\)"`. Temuan apa pun
   di kode non-test dianggap bug silent-kill Windows.

2. **Gunakan `shutil.which()` sebelum memanggil shell — jangan asumsikan Windows
   punya tool yang dimiliki Linux.** `wmic` dihapus di Windows 10 21H1 dan setelahnya. `ps`,
   `kill`, `grep`, `awk`, `fuser`, `lsof`, `pgrep`, dan sebagian besar tool CLI POSIX
   memang tidak ada di Windows. Uji ketersediaan dengan
   `shutil.which("tool")` dan jatuh ke padanan native Windows —
   biasanya PowerShell lewat `subprocess.run(["powershell", "-NoProfile",
   "-Command", ...])`.

   Untuk enumerasi proses: `Get-CimInstance Win32_Process` dari PowerShell adalah
   pengganti modern untuk `wmic process`. Lihat
   `thor_cli/gateway.py::_scan_gateway_pids` untuk polanya.

3. **Encoding berkas.** Windows mungkin menyimpan berkas `.env` dalam `cp1252`. Selalu
   tangani error encoding:
   ```python
   try:
       load_dotenv(env_path)
   except UnicodeDecodeError:
       load_dotenv(env_path, encoding="latin-1")
   ```
   Berkas config (`config.yaml`) mungkin disimpan dengan BOM UTF-8 oleh Notepad dan
   editor serupa — gunakan `encoding="utf-8-sig"` saat membaca berkas yang
   mungkin pernah disentuh editor GUI Windows.

4. **Manajemen proses.** `os.setsid()`, `os.killpg()`, `os.fork()`,
   `os.getuid()`, dan penanganan sinyal POSIX berbeda di Windows. Lindungi dengan
   `platform.system()`, `sys.platform`, atau `hasattr(os, "setsid")`:
   ```python
   if platform.system() != "Windows":
       kwargs["preexec_fn"] = os.setsid
   else:
       kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
   ```

   **Lebih baik:** untuk membunuh proses DAN anak-anaknya (yang dilakukan `os.killpg`
   di POSIX), gunakan `psutil` — ia bekerja di setiap platform:
   ```python
   import psutil
   try:
       parent = psutil.Process(pid)
       # Bunuh anak dulu (dari daun ke atas), lalu induknya.
       for child in parent.children(recursive=True):
           child.kill()
       parent.kill()
   except psutil.NoSuchProcess:
       pass
   ```

5. **Sinyal yang tidak ada di Windows: `SIGALRM`, `SIGCHLD`, `SIGHUP`,
   `SIGUSR1`, `SIGUSR2`, `SIGPIPE`, `SIGQUIT`, `SIGKILL`.** Modul `signal`
   Python memunculkan `AttributeError` saat import jika Anda merujuknya
   di Windows. Gunakan `getattr(signal, "SIGKILL", signal.SIGTERM)` atau
   lindungi seluruh blok di belakang pemeriksaan platform. `loop.add_signal_handler`
   memunculkan `NotImplementedError` di Windows — selalu tangkap.

6. **Pemisah path.** Gunakan `pathlib.Path` alih-alih penggabungan string
   dengan `/`. Garis miring ke depan berfungsi hampir di mana saja di Windows, tetapi
   `subprocess.run(["cmd.exe", "/c", ...])` dan konteks shell lain bisa
   memerlukan garis miring terbalik — konversi dengan `str(path)` di batas subprocess,
   bukan di dalam logika Python.

7. **Symlink memerlukan hak istimewa di Windows** (kecuali Developer Mode
   aktif). Test yang membuat symlink memerlukan `@pytest.mark.skipif(sys.platform ==
   "win32", reason="Symlinks require elevated privileges on Windows")`.

8. **Mode berkas POSIX (0o600, 0o644, dll.) TIDAK ditegakkan pada NTFS** secara
   bawaan. Test yang melakukan assert pada `stat().st_mode & 0o777` harus di-skip di
   Windows — konsepnya tidak dapat diterjemahkan. Gunakan ACL (`icacls`, `pywin32`)
   untuk perlindungan berkas secret di Windows jika diperlukan.

9. **Daemon latar terlepas di Windows memerlukan `pythonw.exe`, BUKAN
   `python.exe`.** `python.exe` selalu mengalokasikan atau menempel ke konsol,
   yang membuatnya rentan terhadap siaran `CTRL_C_EVENT` dari proses
   saudara mana pun. `pythonw.exe` adalah varian tanpa konsol. Kombinasikan dengan
   `CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP |
   CREATE_BREAKAWAY_FROM_JOB` di `subprocess.Popen(creationflags=...)`.
   Lihat `thor_cli/gateway_windows.py::_spawn_detached` untuk implementasi
   referensinya.

10. **`subprocess.Popen` dengan shim `.cmd` atau `.bat` memerlukan `shutil.which`
    untuk menyelesaikannya.** Memberikan `"npm"` ke `Popen` di Windows akan menemukan
    shim shebang POSIX tanpa ekstensi di samping `npm.cmd`, yang tidak dapat
    dieksekusi `CreateProcessW` — Anda akan mendapat `WinError 193 "not a valid
    Win32 application"`. Gunakan `shutil.which("npm", path=node_bin)`
    yang menghormati PATHEXT dan memilih varian `.CMD` di Windows.

11. **Jangan gunakan shebang shell sebagai cara menjalankan Python.** `#!/usr/bin/env
    python` hanya berfungsi ketika berkas dieksekusi melalui shell Unix.
    `subprocess.run(["./myscript.py"])` di Windows gagal meskipun berkasnya
    memiliki baris shebang. Selalu panggil Python secara eksplisit:
    `[sys.executable, "myscript.py"]`.

12. **Perintah shell di installer.** Jika Anda mengubah `scripts/install.sh`,
    buat perubahan yang setara di `scripts/install.ps1`. Kedua skrip itu
    adalah contoh kanonik dari "berjalan di Linux tidak berarti berjalan di
    Windows" dan sudah beberapa kali menyimpang — jaga keduanya tetap selaras.

13. **Path yang dialihkan OneDrive di Windows:** Desktop,
    Documents, Pictures, Videos. Path "asli" ketika OneDrive Backup
    aktif adalah `%USERPROFILE%\OneDrive\Desktop` (dst.), BUKAN
    `%USERPROFILE%\Desktop` (yang ada sebagai cangkang kosong). Selesaikan
    lokasi aslinya lewat `ctypes` + `SHGetKnownFolderPath` atau dengan membaca
    key registry `Shell Folders` — jangan pernah mengasumsikan `~/Desktop`.

14. **CRLF vs LF pada skrip yang dihasilkan.** `cmd.exe` dan `schtasks` Windows
    mem-parse baris demi baris; akhir baris campuran atau hanya LF dapat merusak berkas
    `.cmd` / `.bat` multi-baris. Gunakan `open(path, "w", encoding="utf-8",
    newline="\r\n")` — atau `open(path, "wb")` + byte eksplisit — ketika
    menghasilkan skrip yang akan dieksekusi Windows.

15. **Dua skema quoting berbeda dalam satu baris perintah.** `subprocess.run
    (["schtasks", "/TR", some_cmd])` → schtasks sendiri mem-parse `/TR`, DAN
    string `some_cmd` di-parse ulang oleh `cmd.exe` saat task menyala.
    Parser berbeda, aturan escape berbeda. Gunakan dua helper quoting
    terpisah dan jangan pernah menyilangkannya. Lihat `thor_cli/gateway_windows.py::
    _quote_cmd_script_arg` dan `_quote_schtasks_arg` untuk pasangan
    referensinya.

### Menguji lintas platform

Test untuk perilaku spesifik host harus berjalan di host tersebut. Terapkan satu marker
`platforms` pada setiap test, alih-alih mengubah `sys.platform`:

```python
@pytest.mark.platforms("windows", arch="arm64")
def test_native_windows_arm64_behavior():
    ...
```

Untuk beberapa host yang didukung, gunakan satu marker dengan beberapa argumen, seperti
`@pytest.mark.platforms("linux", "macos")`. Jangan menumpuk marker host.
Test fungsi murni yang menerima platform sebagai data tidak memerlukan marker host.
Lihat [AGENTS.md](AGENTS.md#dont-fake-the-host-os) untuk kontrak lengkapnya.

#### Memeriksa `install.ps1` dari Linux

PowerShell 7 (`pwsh`) berjalan di Linux, jadi sebagian besar `install.ps1` bisa diperiksa
tanpa mesin Windows. Pasang dengan:

```bash
curl -fsSL https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb -o /tmp/ms.deb
dpkg -i /tmp/ms.deb && apt-get update && apt-get install -y powershell
```

Yang bisa diverifikasi nyata: parse syntax lewat AST
(`[Parser]::ParseFile()`), daftar parameter (`Get-Command`), manifest
(`-Manifest`, `-ShowResolvedPaths`, `-ProtocolVersion`), perbandingan terjemahan
stage antara `install.sh` dan `install.ps1` dengan `THOR_INSTALL_LANG`, dan
fungsi internal lewat dot-source (`pwsh -File` dengan `. './scripts/install.ps1'`).

Yang **tidak** bisa diverifikasi di Linux: apa pun yang memanggil `winreg`, `icacls`,
`schtasks`, `Get-CimInstance`, atau `%LOCALAPPDATA%`. Test yang ditandai
`@pytest.mark.platforms("windows")` tetap di-skip — perilaku yang benar.

#### Batas ukuran `AGENTS.md`

`scripts/ci/check_agents_md_size.py` menegakkan `ROOT_MAX_CHARS = 12_000` untuk
`AGENTS.md` di root dan `CHAIN_MAX_CHARS = 30_000` per rantai direktori
(root + semua `AGENTS.md` leluhur). Ini bukan gaya penulisan: berkas tersebut
dimuat sebagai satu blok project-context ke LLM, dan yang melewati batas akan
terpotong saat dimuat. Perkecil berkasnya (pindahkan bentuk panjangnya ke
`website/docs/developer-guide/` atau dokumen sibling), jangan menaikkan batasnya.

---

## Pertimbangan Keamanan

Thor memiliki akses terminal. Keamanan itu penting.

### Perlindungan yang sudah ada

| Lapisan | Implementasi |
|-------|---------------|
| **Piping password sudo** | Menggunakan `shlex.quote()` untuk mencegah shell injection |
| **Deteksi perintah berbahaya** | Pola regex di `tools/approval.py` dengan alur approval pengguna |
| **Prompt injection via cron** | Scanner di `tools/cronjob_tools.py` memblokir pola instruction-override |
| **Write deny list** | Path yang dilindungi (`~/.ssh/authorized_keys`, `/etc/shadow`) diselesaikan lewat `os.path.realpath()` untuk mencegah bypass symlink |
| **Skills guard** | Scanner keamanan untuk skill yang dipasang dari hub (`tools/skills_guard.py`) |
| **Sandbox eksekusi kode** | Proses anak `execute_code` berjalan dengan API key yang dibuang dari environment |
| **Pengerasan container** | Docker: semua capability dibuang, tanpa privilege escalation, batas PID, tmpfs berbatas ukuran |

### Saat menyumbang kode yang sensitif terhadap keamanan

- **Selalu gunakan `shlex.quote()`** ketika menginterpolasi input pengguna ke perintah shell
- **Selesaikan symlink** dengan `os.path.realpath()` sebelum pemeriksaan kontrol akses berbasis path
- **Jangan mencatat secret ke log.** API key, token, dan password tidak boleh muncul di output log
- **Tangkap exception luas** di sekitar eksekusi tool agar satu kegagalan tidak membuat loop agent crash
- **Uji di semua platform** jika perubahan Anda menyentuh path berkas, manajemen proses, atau perintah shell

Jika PR Anda memengaruhi keamanan, catat secara eksplisit di deskripsinya.

### Kebijakan pinning dependensi (pengerasan supply chain)

Setelah [kompromi supply chain litellm](https://github.com/BerriAI/litellm/issues/24512) pada Maret 2026 dan [kampanye worm Mini Shai-Hulud](https://socket.dev/blog/tanstack-npm-packages-compromised-mini-shai-hulud-supply-chain-attack) pada Mei 2026, semua dependensi harus mengikuti aturan berikut:

| Jenis sumber | Perlakuan yang diwajibkan | Alasan |
|---|---|---|
| **Paket PyPI** | `>=floor,<next_major` | Versi PyPI bersifat immutable setelah diterbitkan, tetapi versi baru dapat didorong ke dalam rentang Anda. Plafon `<next_major` mencegah instalasi 1.x naik ke 2.0.0 yang berbahaya. |
| **Git URL** (atroposlib, tinker, yc-bench, Baileys) | Commit SHA penuh | Branch dan tag adalah ref yang bisa berubah; SHA bersifat content-addressed. |
| **GitHub Actions** | Commit SHA penuh + komentar versi | Tag action adalah ref yang bisa berubah (mis. tj-actions/changed-files Maret 2025). Pin sebagai `uses: owner/action@<sha>  # vX.Y.Z` |
| **Instalasi pip hanya untuk CI** | `==exact` | Build CI hermetik; churn dapat diterima. |

**Setiap dependensi PyPI baru dalam sebuah PR harus memiliki batas atas `<next_major`.** PR yang menambahkan spesifikasi `>=X.Y.Z` tanpa batas akan ditolak reviewer. Langkah supply-chain pada alur kerja CI `repo-guards.yml` juga menandai perubahan manifes dependensi untuk review manual.

**Cara menentukan plafon:**
- Jika paket berada di versi `1.x.y`, gunakan `<2`.
- Jika paket berada di versi `0.x.y` (pra-1.0), gunakan `<0.(current_minor + 2)` — misalnya jika saat ini `0.29.x`, gunakan `<0.32`. Ini memberi ruang sekitar 2 versi minor sambil menjaga jendelanya cukup kecil sehingga versi hasil pengambilalihan bermusuhan kecil kemungkinan masuk ke dalamnya.
- Pengecualian: paket dengan API sangat stabil (mis. `aiohttp-socks`) dapat memakai `<1` atas pertimbangan reviewer.

**Contoh:**
```toml
# ✅ Benar — pasca-1.0
"openai>=2.21.0,<3"
"pydantic>=2.12.5,<3"

# ✅ Benar — pra-1.0 (jendela minor yang ketat)
"asyncpg>=0.29,<0.32"
"aiosqlite>=0.20,<0.23"
"hindsight-client>=0.4.22,<0.5"

# ❌ Ditolak — tanpa batas atas
"some-package>=1.2.3"

# ❌ Ditolak — terlalu ketat (memblokir patch yang sah)
"some-package==1.2.3"

# ❌ Ditolak — terlalu longgar untuk pra-1.0 (memungkinkan 80 versi minor)
"some-package>=0.20,<1"
```

**PR referensi:** #2796 (penghapusan litellm), #2810 (pass batas atas), #9801 (pinning SHA + CI audit supply-chain, kini menjadi langkah pada `repo-guards.yml`).

---

## Proses Pull Request

### Penamaan branch

```
fix/description        # Perbaikan bug
feat/description       # Fitur baru
docs/description       # Dokumentasi
test/description       # Test
refactor/description   # Restrukturisasi kode
```

### Sebelum mengirim

1. **Jalankan test**: `just test <paths>` (scripts/run_tests.sh) untuk lingkungan dan isolasi per-berkas yang sama seperti CI.
2. **Jalankan lint check**: `just check` (jalur lint yang memblokir, secara lokal).
3. **Uji secara manual**: Jalankan `thor` dan latih jalur kode yang Anda ubah
4. **Periksa dampak lintas platform**: Jika Anda menyentuh I/O berkas, manajemen proses, atau penanganan terminal, pertimbangkan macOS, Linux, dan WSL2
5. **Jaga PR tetap fokus**: Satu perubahan logis per PR. Jangan mencampur perbaikan bug dengan refactor dan fitur baru.

### Deskripsi PR

Sertakan:
- **Apa** yang berubah dan **mengapa**
- **Cara mengujinya** (langkah reproduksi untuk bug, contoh penggunaan untuk fitur)
- **Platform apa** yang Anda gunakan untuk menguji
- Rujuk issue terkait

### Pesan commit

Kami menggunakan [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipe>(<cakupan>): <deskripsi>
```

| Tipe | Digunakan untuk |
|------|---------|
| `fix` | Perbaikan bug |
| `feat` | Fitur baru |
| `docs` | Dokumentasi |
| `test` | Test |
| `refactor` | Restrukturisasi kode (tanpa perubahan perilaku) |
| `chore` | Build, CI, pembaruan dependensi |

Cakupan: `cli`, `gateway`, `tools`, `skills`, `agent`, `install`, `whatsapp`, `security`, dll.

Contoh:
```
fix(cli): prevent crash in save_config_value when model is a string
feat(gateway): add WhatsApp multi-user session isolation
fix(security): prevent shell injection in sudo password piping
test(tools): add unit tests for file_operations
```

---

## Melaporkan Issue

- Gunakan [GitHub Issues](https://github.com/dwisetyabudi15581/Thor-agent/issues)
- Sertakan: OS, versi Python, versi Thor (`thor --version`), traceback error lengkap
- Sertakan langkah reproduksi
- Periksa issue yang ada sebelum membuat duplikat
- Untuk kerentanan keamanan, laporkan secara privat

---

## Komunitas

- **Discord**: [github.com/dwisetyabudi15581/Thor-agent](https://github.com/dwisetyabudi15581/Thor-agent) — untuk pertanyaan, memamerkan proyek, dan berbagi skill
- **GitHub Discussions**: Untuk proposal desain dan diskusi arsitektur
- **Skills Hub**: Unggah skill khusus ke registry dan bagikan ke komunitas

---

## Lisensi

Dengan berkontribusi, Anda setuju bahwa kontribusi Anda akan dilisensikan di bawah [MIT License](LICENSE).
