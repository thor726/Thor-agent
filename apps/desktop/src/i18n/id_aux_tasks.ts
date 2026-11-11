import type { AuxTaskCopyMap } from './types_aux_tasks'

export const idAuxTasks: AuxTaskCopyMap = {
  vision: { label: 'Vision', hint: 'Analisis gambar' },
  compression: { label: 'Kompresi', hint: 'Pemadatan konteks' },
  approval: { label: 'Persetujuan', hint: 'Auto-approve pintar' },
  mcp: { label: 'MCP', hint: 'Perutean tool MCP' },
  title_generation: { label: 'Pembuatan judul', hint: 'Judul sesi' },
  review: { label: 'Review', hint: '/review subagent reviewer' },
  voice_chat: { label: 'Voice chat', hint: 'Balasan mode suara' },
  triage_specifier: { label: 'Triage specifier', hint: 'Penjabaran spec Kanban' },  kanban_decomposer: { label: 'Kanban decomposer', hint: 'Pemecahan tugas' },
  profile_describer: { label: 'Profile describer', hint: 'Deskripsi profil otomatis' },
  curator: { label: 'Curator', hint: 'Tinjauan pemakaian skill' }
}
