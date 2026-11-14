// Locale Bahasa Indonesia: overlay di atas en.ts via defineLocale (pola ja.ts/ru.ts).
// Fragmen terjemahan ada di id_*.ts; file ini hanya merangkai dan menempatkannya
// pada key yang sama seperti locale lain. Key yang tidak di-overlay jatuh kembali
// ke bahasa Inggris.
import {
  defineLocale,
  type TranslationOverrides
} from './define-locale'

import { idAppTour } from './id_app_tour'
import { idBoot } from './id_boot'
import { idClarify } from './id_clarify'
import { idConnectorAccounts } from './id_connector_accounts'
import { idConnectorCard } from './id_connector_card'
import { idCronControl } from './id_cron_control'
import { idErrorLayers } from './id_error_layers'
import { idFirstRun } from './id_first_run'
import { idGatewayGroupOpen, idSkillDeepLink } from './id_deep_links'
import { idMemoryLayers } from './id_memory_layers'
import { idNotices } from './id_notices'
import { idNotifications } from './id_notifications'
import { idPluginPreviewAccess } from './id_plugin_preview_access'
import { idPluginUpdateAll } from './id_plugin_update_all'
import { idThemePicker } from './id_theme_picker'
import { idUpdateChannel } from './id_update_channel'

export const idOverrides = {
  gatewayGroupOpen: idGatewayGroupOpen,
  appTour: idAppTour,
  firstRun: idFirstRun,
  connectors: idConnectorCard,
  connectorsPage: {
    accounts: idConnectorAccounts
  },
  boot: idBoot.boot,
  ...idNotices,
  settings: {
    memoryLayers: idMemoryLayers,
    notifications: idNotifications,
    about: { channel: idUpdateChannel }
  },
  skillDeepLink: idSkillDeepLink,
  skills: {
    plugins: { ...idPluginPreviewAccess, ...idPluginUpdateAll }
  },
  cron: {
    control: idCronControl
  },
  assistant: {
    thread: {
      ...idErrorLayers,
      clarify: idClarify,
      themePicker: idThemePicker
    }
  }
} satisfies TranslationOverrides

export const id = defineLocale(idOverrides)
