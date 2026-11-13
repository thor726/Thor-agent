/**
 * Which persisted keys are machine-level UI preferences (#145213).
 *
 * Only these leave localStorage for the machine's shared store, so native
 * Desktop and every browser that opens this machine's Webapp show the same
 * choices. Scoped families keep their scope inside the key name (a
 * `….profile.<name>` or per-connection suffix): only the location changes.
 *
 * Deliberately NOT here (they stay in this browser/window):
 * - credentials, grants and connection config: gateway registry, custom model
 *   endpoints, plugin decisions and preview-script grants, embed permissions;
 * - per-window or per-device runtime state: layout tree, open tiles and tabs,
 *   last route/session, scroll, zoom, pet and popout geometry, keep-awake;
 * - drafts, queues, journals and caches: composer queue, in-flight turns,
 *   pending/prepared submissions, previews, pricing, backend skin cache, the
 *   "provider configured" onboarding cache (each backend answers that itself);
 * - one-off notices: butterbar, update and real-profile prompts.
 */

const SHARED_KEYS: ReadonlySet<string> = new Set([
  // Appearance.
  'thor-desktop-theme-v2',
  'thor-desktop-mode-v1',
  'thor-desktop-profile-themes-v1',
  'thor-desktop-profile-modes-v1',
  'thor-desktop-user-themes-v1',
  'thor.desktop.backdrop.v1',
  'thor.desktop.chat-text-scale.v1',
  'thor.desktop.interfaceMode.v1',
  'thor.desktop.textDirection',
  'thor.desktop.translucency.v2',
  'thor.desktop.user-bubble-transparency.v1',
  // Sessions sidebar and profile rail.
  'thor.desktop.agentsGroupedByWorkspace',
  'thor.desktop.profileColors',
  'thor.desktop.profileOrder',
  'thor.desktop.profileRailVisible',
  'thor.desktop.sessionListDensity',
  'thor.desktop.sessionOrder',
  'thor.desktop.sessionOrder.manual',
  'thor.desktop.showAllProfiles',
  'thor.desktop.sidebarAgentsGrouped.allProfiles',
  'thor.desktop.sidebarCardRows',
  'thor.desktop.sidebarGrouping',
  'thor.desktop.sidebarGrouping.allProfiles',
  'thor.desktop.sidebarRowMeta',
  'thor.desktop.sidebarShowAllSessions',
  'thor.desktop.sidebarShowArchived',
  'thor.desktop.sidebarSortKey',
  // Status bar.
  'thor.desktop.statusbarHidden.v2',
  'thor.desktop.statusbarVisible.v2',
  // Transcript and tools.
  'thor.desktop.hideThreadTimeline',
  'thor.desktop.reasoning.collapsedByDefault',
  'thor.desktop.toolView.hideCodeDiffs',
  'thor.desktop.toolView.technical',
  // Shell, panes and behaviour.
  'thor.desktop.alwaysExternalLinks.v1',
  'thor.desktop.capabilities.catalogCardView',
  'thor.desktop.composerPopout.enabled',
  'thor.desktop.composerPopout.gesturesEnabled',
  'thor.desktop.files.showIgnored',
  'thor.desktop.keybinds',
  'thor.desktop.layoutPresets.v2',
  'thor.desktop.panesFlipped',
  'thor.desktop.tabStripDefault',
  'thor.desktop.titlebarAppActions',
  // Guidance: what the user already skipped, saw or dismissed does not come
  // back in every new browser or origin (#145600).
  'thor-onboarding-skipped-v1',
  'thor.desktop.tips.last.v1',
  'thor.desktop.tips.next.v1',
  'thor.desktop.tips.retired.v1',
  'thor.desktop.tips.rotation.v1',
  'thor.desktop.tips.shownAt.v1',
  'thor.desktop.tours.v1',
  // Sound and media.
  'thor.desktop.autoSpeakReplies',
  'thor.desktop.completionSoundVariantId',
  'thor.desktop.hapticsMuted',
  'thor.desktop.videoPlaybackSpeed',
  // Model picker.
  'thor.desktop.collapsed-providers',
  'thor.desktop.favorite-models',
  // visible-models is a diff against known-models: they only make sense together.
  'thor.desktop.known-models',
  'thor.desktop.model-presets',
  'thor.desktop.visible-models'
])

/** Families whose scope rides in the key suffix (gateway aliases/order/collapsed). */
const SHARED_PREFIXES: readonly string[] = ['thor.desktop.sidebar.gatewayGroups.v1.']

export function isSharedPreferenceKey(key: string): boolean {
  return SHARED_KEYS.has(key) || SHARED_PREFIXES.some(prefix => key.startsWith(prefix))
}
