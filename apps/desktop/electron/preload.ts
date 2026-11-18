import { contextBridge, ipcRenderer, webFrame, webUtils } from 'electron'

import type { DesktopProfileRoute } from './desktop-profile'
import type { HudModifierApi, HudModifierStatus } from './hud-modifier-types'
import { customWindowControlsEnabled } from './window-controls'

// Which translucency the OS can back. Asked synchronously because the renderer
// needs it before its first paint, and answered by main because deciding it
// needs `os.release()` — a sandboxed preload may only require electron, events,
// timers and url, so importing node:os here throws before contextBridge runs
// and takes the ENTIRE bridge down with it (window.thorDesktop undefined =>
// "Desktop IPC bridge is unavailable"). No reply means no glass, which degrades
// to an ordinary opaque window rather than a page thinned over nothing.
const translucencySupport = ipcRenderer.sendSync('thor:translucency:support')
const hudWindowing = ipcRenderer.sendSync('thor:hud:windowing')
const hudNativeDrag = hudWindowing?.nativeDrag === true

const launchFlags: { localModels?: boolean; assumeFreshInstall?: boolean } | undefined =
  ipcRenderer.sendSync('thor:feature-flags')

// Local, sanitized skin payload for the first renderer theme paint. This does
// not wait on `gateway.ready`, so an unreachable remote primary cannot force
// the built-in palette over the skin configured on this machine.
const localSkin = ipcRenderer.sendSync('thor:skin:local')

// This machine's UI preferences store (#145213), read before the first paint so
// a preference set in another window or in this machine's Webapp paints at once.
const uiPreferencesSnapshot = ipcRenderer.sendSync('thor:ui-preferences:snapshot')

import { unwrapExpectedNotFound } from './api-expected-404'

contextBridge.exposeInMainWorld('thorDesktop', {
  glassSupported: translucencySupport?.glass === true,
  translucencySupported: translucencySupport?.translucency === true,
  // Launch-flag fact: the app was started with --local, so the renderer may
  // show the local-models surfaces. Static for the window's lifetime.
  localModelsEnabled: launchFlags?.localModels === true,
  // Dev-only launch fact: an unpackaged app started with --fresh-install, so
  // onboarding treats this launch as a fresh install. Always false when packaged.
  assumeFreshInstall: launchFlags?.assumeFreshInstall === true,
  localSkin: localSkin && typeof localSkin === 'object' ? localSkin : null,
  uiPreferences: {
    snapshot: uiPreferencesSnapshot && typeof uiPreferencesSnapshot === 'object' ? uiPreferencesSnapshot : null,
    read: () => ipcRenderer.invoke('thor:ui-preferences:read'),
    write: payload => ipcRenderer.invoke('thor:ui-preferences:write', payload),
    onChanged: callback => {
      const listener = (_event, snapshot) => callback(snapshot)
      ipcRenderer.on('thor:ui-preferences:changed', listener)

      return () => ipcRenderer.removeListener('thor:ui-preferences:changed', listener)
    }
  },
  getConnection: (profile, opts) => ipcRenderer.invoke('thor:connection', profile, opts),
  // Loopback origin that hosts YouTube's player for the file:// renderer.
  getEmbedHostOrigin: () => ipcRenderer.invoke('thor:embed-host:origin'),
  // Registry-scoped backend resolution: { connectionId, profile } → descriptor.
  getConnectionFor: payload => ipcRenderer.invoke('thor:connection:for', payload),
  getProfileRoutes: profiles => ipcRenderer.invoke('thor:plugin-profile-routes', profiles),
  revalidateConnection: () => ipcRenderer.invoke('thor:connection:revalidate'),
  getGatewayWsUrl: profile => ipcRenderer.invoke('thor:gateway:ws-url', profile),
  // Registry-scoped fresh WS URL: { connectionId, profile } → result shape of
  // getGatewayWsUrl, minted against that connection's backend.
  getGatewayWsUrlFor: payload => ipcRenderer.invoke('thor:gateway:ws-url-for', payload),
  // { connectionId, profile, pluginId, path } → one-use local plugin socket URL, null, or { refused: 'permission' }.
  getPluginWsUrl: payload => ipcRenderer.invoke('thor:plugin:ws-url', payload),
  // Union agent roster across every registered connection.
  getAgentRoster: () => ipcRenderer.invoke('thor:agents:roster'),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('thor:window:openSession', sessionId, opts),
  openSessionInTerminal: (sessionId, opts) => ipcRenderer.invoke('thor:window:openInTerminal', sessionId, opts),
  openWindow: (options?: DesktopProfileRoute) => ipcRenderer.invoke('thor:window:openInstance', options),
  openBrowserWindow: tabId => ipcRenderer.invoke('thor:window:openBrowser', tabId),
  windowRelay: {
    send: payload => ipcRenderer.send('thor:window:relay', payload),
    onMessage: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:window:relay', listener)

      return () => ipcRenderer.removeListener('thor:window:relay', listener)
    }
  },
  onBrowserPopoutClosed: callback => {
    const listener = (_event, tabId) => callback(tabId)
    ipcRenderer.on('thor:browser-popout:closed', listener)

    return () => ipcRenderer.removeListener('thor:browser-popout:closed', listener)
  },
  claimAmbientCue: key => ipcRenderer.invoke('thor:ambient:claim', key),
  windowControls: {
    custom: customWindowControlsEnabled(),
    minimize: () => ipcRenderer.send('thor:window-control', 'minimize'),
    toggleMaximize: () => ipcRenderer.send('thor:window-control', 'toggle-maximize'),
    close: () => ipcRenderer.send('thor:window-control', 'close')
  },
  wakeIndicator: {
    getState: () => ipcRenderer.invoke('thor:wake-indicator:get'),
    setState: state => ipcRenderer.send('thor:wake-indicator:set', state),
    onState: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('thor:wake-indicator:state', listener)

      return () => ipcRenderer.removeListener('thor:wake-indicator:state', listener)
    }
  },
  chatOnboarding: {
    size: mode => ipcRenderer.send('thor:window:size', mode)
  },
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('thor:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('thor:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('thor:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('thor:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('thor:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('thor:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('thor:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:pet-overlay:state', listener)

      return () => ipcRenderer.removeListener('thor:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:pet-overlay:control', listener)

      return () => ipcRenderer.removeListener('thor:pet-overlay:control', listener)
    }
  },
  // HUD mode: the chrome-free floating chat. A full app renderer (own gateway)
  // sized as a floating bar, so it mounts the real composer. Main owns the
  // window; `onChanged` keeps every window's toggle truthful.
  hud: {
    nativeDrag: hudNativeDrag,
    windowing: {
      clientPlacement: hudWindowing?.clientPlacement !== false,
      controlDrag: hudWindowing?.controlDrag === true,
      nativeDrag: hudNativeDrag,
      solid: hudWindowing?.solid === true,
      workspaceTransfer: hudWindowing?.workspaceTransfer === true
    },
    open: request => ipcRenderer.invoke('thor:hud:open', request),
    close: () => ipcRenderer.invoke('thor:hud:close'),
    setIgnoreMouse: ignore => ipcRenderer.send('thor:hud:ignore-mouse', ignore),
    beginMove: () => ipcRenderer.send('thor:hud:begin-move'),
    endMove: () => ipcRenderer.send('thor:hud:end-move'),
    moveBy: delta => ipcRenderer.send('thor:hud:move-by', delta),
    setWorkspaceTransfer: transferring => ipcRenderer.send('thor:hud:workspace-transfer', transferring),
    setBounds: bounds => ipcRenderer.send('thor:hud:set-bounds', bounds),
    resetLayout: () => ipcRenderer.invoke('thor:hud:reset-layout'),
    // Whether the band covers the window below the bar. Main pairs it with the
    // user's translucency setting to decide the native frost (macOS vibrancy /
    // Windows 11 DWM backdrop) — see hudFrostFor.
    setFrost: showing => ipcRenderer.invoke('thor:hud:frost', showing),
    // The HUD tells main which session it is on; main hands that back to the
    // app window when the HUD closes, so the app can re-home onto it.
    setSession: sessionId => ipcRenderer.send('thor:hud:session', sessionId),
    onGoto: callback => {
      const listener = (_event, sessionId) => callback(sessionId)
      ipcRenderer.on('thor:hud:goto', listener)

      return () => ipcRenderer.removeListener('thor:hud:goto', listener)
    },
    onChanged: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('thor:hud:changed', listener)

      return () => ipcRenderer.removeListener('thor:hud:changed', listener)
    },
    // Linux only, and silent elsewhere: where the cursor is, in page
    // coordinates, or null when it has left the window. Stands in for the
    // mousemove that `setIgnoreMouseEvents(true, { forward: true })` delivers on
    // macOS and Windows but not here.
    onCursor: callback => {
      const listener = (_event, point) => callback(point)
      ipcRenderer.on('thor:hud:cursor', listener)

      return () => ipcRenderer.removeListener('thor:hud:cursor', listener)
    },
    // Main's game-overlay watch: whether a fullscreen app (a game) is under
    // the HUD, so the renderer can step back to the low-opacity overlay
    // treatment while one owns the screen.
    onGameOverlay: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('thor:hud:game-overlay', listener)

      return () => ipcRenderer.removeListener('thor:hud:game-overlay', listener)
    }
  },
  hudModifier: {
    getSettings: () => ipcRenderer.invoke('thor:hud-modifier:settings:get'),
    setEnabled: enabled => ipcRenderer.invoke('thor:hud-modifier:settings:set', enabled),
    openPermissionSettings: () => ipcRenderer.invoke('thor:hud-modifier:permission'),
    onStatus: callback => {
      const listener = (_event: Electron.IpcRendererEvent, status: HudModifierStatus) => callback(status)
      ipcRenderer.on('thor:hud-modifier:status', listener)

      return () => ipcRenderer.removeListener('thor:hud-modifier:status', listener)
    }
  } satisfies HudModifierApi,
  // macOS native screenshot gesture; captures require a main-issued request.
  screenshot:
    process.platform === 'darwin'
      ? {
          getSettings: () => ipcRenderer.invoke('thor:screenshot:settings:get'),
          setEnabled: enabled => ipcRenderer.invoke('thor:screenshot:settings:set', enabled),
          openPermissionSettings: kind => ipcRenderer.invoke('thor:screenshot:permission', kind),
          capture: requestId => ipcRenderer.invoke('thor:screenshot:capture', requestId),
          onStatus: callback => {
            const listener = (_event, status) => callback(status)
            ipcRenderer.on('thor:screenshot:status', listener)

            return () => ipcRenderer.removeListener('thor:screenshot:status', listener)
          },
          onRequest: callback => {
            const channel = 'thor:screenshot:request'
            const listener = (_event, requestId) => callback(requestId)

            if (ipcRenderer.listenerCount(channel) === 0) {
              ipcRenderer.send('thor:screenshot:subscribe', true)
            }

            ipcRenderer.on(channel, listener)

            return () => {
              ipcRenderer.removeListener(channel, listener)

              if (ipcRenderer.listenerCount(channel) === 0) {
                ipcRenderer.send('thor:screenshot:subscribe', false)
              }
            }
          }
        }
      : undefined,
  // Quick Entry: the global-hotkey mini composer window. Main owns the OS
  // shortcut + the persisted preference; the quick window only captures text
  // and hands it back, and the primary renderer submits it through the normal
  // prompt path.
  quickEntry: {
    getSettings: () => ipcRenderer.invoke('thor:quick-entry:settings:get'),
    setSettings: patch => ipcRenderer.invoke('thor:quick-entry:settings:set', patch),
    // Invoke returns the delivery result so the draft is not lost (#85590).
    submit: payload => ipcRenderer.invoke('thor:quick-entry:submit', payload),
    // Main cannot invoke the primary renderer, so it receives this ack (#85590).
    ackSubmit: (correlationId, result) => ipcRenderer.send('thor:quick-entry:ack', { correlationId, result }),
    dismiss: () => ipcRenderer.send('thor:quick-entry:dismiss'),
    // Primary renderer → main → quick window: gateway connection state + the
    // recent-session options the target picker offers. Main caches the latest
    // payload so a freshly spawned quick window starts from truth.
    pushState: payload => ipcRenderer.send('thor:quick-entry:state', payload),
    // Quick window subscribes to those pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:quick-entry:state', listener)

      return () => ipcRenderer.removeListener('thor:quick-entry:state', listener)
    },
    // Main → primary renderer: a submit captured by the quick window.
    onSubmit: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:quick-entry:submit', listener)

      return () => ipcRenderer.removeListener('thor:quick-entry:submit', listener)
    },
    // Main → quick window: you were just summoned (reset draft + refocus).
    onShown: callback => {
      const listener = () => callback()
      ipcRenderer.on('thor:quick-entry:shown', listener)

      return () => ipcRenderer.removeListener('thor:quick-entry:shown', listener)
    },
    // Main → quick window: the outcome of a submit whose relay already timed
    // out. Delivery is now KNOWN — reconcile the unknown state instead of
    // leaving the user to resend a prompt that may already be delivered.
    onLateResult: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:quick-entry:late-result', listener)

      return () => ipcRenderer.removeListener('thor:quick-entry:late-result', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('thor:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('thor:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('thor:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('thor:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('thor:connection-config:test', payload),
  // Opt-in OS-keychain encryption for stored gateway secrets (default off —
  // see secret-storage-policy.ts). get never touches the OS keychain.
  getSecretStorageEncryption: () => ipcRenderer.invoke('thor:secret-storage:get'),
  setSecretStorageEncryption: (on: boolean) => ipcRenderer.invoke('thor:secret-storage:set', on),
  // v2 multi-connection registry: named agent sources (local / remote / cloud / ssh).
  connections: {
    list: () => ipcRenderer.invoke('thor:connections:list'),
    save: payload => ipcRenderer.invoke('thor:connections:save', payload),
    remove: id => ipcRenderer.invoke('thor:connections:remove', id),
    setPrimary: id => ipcRenderer.invoke('thor:connections:set-primary', id),
    setLaunchMode: mode => ipcRenderer.invoke('thor:connections:set-launch-mode', mode),
    setLastUsed: id => ipcRenderer.invoke('thor:connections:set-last-used', id),
    test: id => ipcRenderer.invoke('thor:connections:test', id),
    updateManaged: id => ipcRenderer.invoke('thor:connections:update-managed', id),
    // Fan out `thor update` to every eligible registered connection.
    // Optional excludeIds skips rows the caller updates through another path.
    updateAll: options => ipcRenderer.invoke('thor:connections:update-all', options),
    // Registry lifecycle push (main → renderer): a connection was removed or
    // materially edited, so secondaries scoped to it must be disposed (and,
    // for edits, re-dialed at the new target).
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:connections:changed', listener)

      return () => ipcRenderer.removeListener('thor:connections:changed', listener)
    }
  },
  sshConfigHosts: () => ipcRenderer.invoke('thor:ssh-config:hosts'),
  sshResolveHost: host => ipcRenderer.invoke('thor:ssh-config:resolve', host),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('thor:connection-config:probe', remoteUrl),
  // `options` lets a registry-editor draft sign in BEFORE it is saved: the
  // main process settles the draft's connection id up front so the login
  // window writes into the per-connection cookie jar the saved entry will
  // read (not the legacy shared jar an unsaved URL would fall back to).
  oauthLoginConnectionConfig: (remoteUrl, options) =>
    ipcRenderer.invoke('thor:connection-config:oauth-login', remoteUrl, options),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('thor:connection-config:oauth-logout', remoteUrl),
  // Thor Cloud: one portal login powers discovery + silent per-agent sign-in
  // (cloud-auto-discovery Phase 3).
  cloud: {
    status: () => ipcRenderer.invoke('thor:cloud:status'),
    login: () => ipcRenderer.invoke('thor:cloud:login'),
    logout: () => ipcRenderer.invoke('thor:cloud:logout'),
    discover: org => ipcRenderer.invoke('thor:cloud:discover', org),
    agentSignIn: dashboardUrl => ipcRenderer.invoke('thor:cloud:agent-sign-in', dashboardUrl)
  },
  profile: {
    getDefault: () => ipcRenderer.invoke('thor:profile:default:get'),
    setDefault: (route: DesktopProfileRoute) => ipcRenderer.invoke('thor:profile:default:set', route),
    onDefaultChanged: (callback: (route: DesktopProfileRoute | null) => void) => {
      const listener = (_event: Electron.IpcRendererEvent, route: DesktopProfileRoute | null) => callback(route)
      ipcRenderer.on('thor:profile:default:changed', listener)

      return () => ipcRenderer.removeListener('thor:profile:default:changed', listener)
    },
    get: () => ipcRenderer.invoke('thor:profile:get'),
    remember: name => ipcRenderer.invoke('thor:profile:remember', name),
    importConnections: (record: Record<string, string>) =>
      ipcRenderer.invoke('thor:profile:connections:import', record),
    rememberConnection: (connectionId: string, profile: string) =>
      ipcRenderer.invoke('thor:profile:connections:remember', connectionId, profile),
    set: name => ipcRenderer.invoke('thor:profile:set', name)
  },
  // The handler resolves an expected 404 with a sentinel instead of rejecting
  // (Electron logs a stack for every rejected invoke). Turn it back into the
  // rejection the renderer expects — see electron/api-expected-404.ts.
  api: request => ipcRenderer.invoke('thor:api', request).then(unwrapExpectedNotFound),
  notify: payload => ipcRenderer.invoke('thor:notify', payload),
  claimStartupLatency: () => ipcRenderer.invoke('thor:startup-latency:claim'),
  requestMicrophoneAccess: () => ipcRenderer.invoke('thor:requestMicrophoneAccess'),
  readWindowBelow: () => ipcRenderer.invoke('thor:window:readBelow'),
  readFileDataUrl: filePath => ipcRenderer.invoke('thor:readFileDataUrl', filePath),
  readFileDataUrlForAttach: filePath => ipcRenderer.invoke('thor:readFileDataUrlForAttach', filePath),
  dataUrlReadMax: {
    get: () => ipcRenderer.invoke('thor:data-url-read-max:get'),
    set: maxMb => ipcRenderer.invoke('thor:data-url-read-max:set', maxMb)
  },
  readFileText: filePath => ipcRenderer.invoke('thor:readFileText', filePath),
  readPluginSource: (filePath: string) => ipcRenderer.invoke('thor:readPluginSource', filePath),
  selectPaths: options => ipcRenderer.invoke('thor:selectPaths', options),
  selectSavePath: options => ipcRenderer.invoke('thor:selectSavePath', options),
  saveTextFileAs: request => ipcRenderer.invoke('thor:saveTextFileAs', request),
  writeClipboard: text => ipcRenderer.invoke('thor:writeClipboard', text),
  readClipboard: () => ipcRenderer.invoke('thor:readClipboard'),
  saveGatewayFile: payload => ipcRenderer.invoke('thor:saveGatewayFile', payload),
  saveImageFromUrl: url => ipcRenderer.invoke('thor:saveImageFromUrl', url),
  contextMenuEdit: command => ipcRenderer.invoke('thor:context-menu:edit', command),
  contextMenuCopyImage: () => ipcRenderer.invoke('thor:context-menu:copy-image'),
  contextMenuSpellcheck: action => ipcRenderer.invoke('thor:context-menu:spellcheck', action),
  contextMenuGuestAddWord: payload => ipcRenderer.invoke('thor:context-menu:guest-add-word', payload),
  spellcheckDictionary: (op, word) => ipcRenderer.invoke('thor:spellcheck:dictionary', { op, word }),
  onContextMenuSpellcheck: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:context-menu-spellcheck', listener)

    return () => ipcRenderer.removeListener('thor:context-menu-spellcheck', listener)
  },
  saveImageBuffer: (data, ext, name) => ipcRenderer.invoke('thor:saveImageBuffer', { data, ext, name }),
  capturePreview: payload => ipcRenderer.invoke('thor:capturePreview', payload),
  savePastedText: text => ipcRenderer.invoke('thor:savePastedText', { text }),
  saveClipboardImage: () => ipcRenderer.invoke('thor:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('thor:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('thor:watchPreviewFile', url),
  watchDirectory: dir => ipcRenderer.invoke('thor:watchDirectory', dir),
  stopPreviewFileWatch: id => ipcRenderer.invoke('thor:stopPreviewFileWatch', id),
  setActiveWork: payload => ipcRenderer.send('thor:active-work', payload),
  scheduleStreamWorkWake: (token, delayMs) => ipcRenderer.send('thor:stream-work-wake', { token, delayMs }),
  onStreamWorkWake: callback => {
    const listener = (_event, token) => callback(token)
    ipcRenderer.on('thor:stream-work-ready', listener)

    return () => ipcRenderer.removeListener('thor:stream-work-ready', listener)
  },
  setTitleBarTheme: payload => ipcRenderer.send('thor:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('thor:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('thor:translucency', payload),
  setKeepAwake: mode => ipcRenderer.send('thor:keep-awake', mode),
  // Once per computer, after a timed sleep interrupted a turn with keep-awake off.
  onKeepAwakeOffer: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:keep-awake-offer', listener)

    return () => ipcRenderer.removeListener('thor:keep-awake-offer', listener)
  },
  minimizeToTray: {
    get: () => ipcRenderer.invoke('thor:minimize-to-tray:get'),
    set: on => ipcRenderer.invoke('thor:minimize-to-tray:set', on),
    onChanged: callback => {
      const listener = (_event, status) => callback(status)
      ipcRenderer.on('thor:minimize-to-tray:changed', listener)

      return () => ipcRenderer.removeListener('thor:minimize-to-tray:changed', listener)
    }
  },
  setDisableF12: blocked => ipcRenderer.send('thor:devtools:disable-f12', blocked),
  setF12ShortcutActive: active => ipcRenderer.send('thor:f12ShortcutActive', Boolean(active)),
  onF12Shortcut: callback => {
    const listener = (_event, input) => callback(input)
    ipcRenderer.on('thor:f12-shortcut', listener)

    return () => ipcRenderer.removeListener('thor:f12-shortcut', listener)
  },
  setPreviewShortcutActive: active => ipcRenderer.send('thor:previewShortcutActive', Boolean(active)),
  setPreviewGuestHidden: (webContentsId, hidden) =>
    ipcRenderer.send('thor:preview-guest-hidden', { webContentsId, hidden: Boolean(hidden) }),
  beginPreviewGuestActivity: webContentsId => ipcRenderer.invoke('thor:preview-guest-activity:begin', webContentsId),
  endPreviewGuestActivity: token => ipcRenderer.invoke('thor:preview-guest-activity:end', token),
  executePreviewGuestScript: (token, code) => ipcRenderer.invoke('thor:preview-guest-activity:script', token, code),
  syncPreviewSignins: request => ipcRenderer.invoke('thor:preview-signins:sync', request),
  migratePreviewSigninsForProfile: (request: { oldProfile: string; newProfile: string }) =>
    ipcRenderer.invoke('thor:preview-signins:profile-renamed', request),
  dropPreviewSigninsForProfile: (request: { profile: string }) =>
    ipcRenderer.invoke('thor:preview-signins:profile-deleted', request),
  openExternal: url => ipcRenderer.invoke('thor:openExternal', url),
  freeTierChallenge: {
    // Load the account service's challenge page in a hidden window (revealed
    // only if the page asks for the human). Resolves with how it ended.
    run: request => ipcRenderer.invoke('thor:freeTierChallenge:run', request)
  },
  mcpOauth: {
    // One-shot loopback listener for MCP OAuth against remote backends: bind
    // on this machine, hand redirectUri to mcp.servers.oauth.start, then wait
    // for the provider redirect and relay code/state via oauth.callback.
    listen: () => ipcRenderer.invoke('thor:mcp-oauth:listen'),
    wait: (id, timeoutMs) => ipcRenderer.invoke('thor:mcp-oauth:wait', id, timeoutMs),
    cancel: id => ipcRenderer.invoke('thor:mcp-oauth:cancel', id)
  },
  openPreviewInBrowser: url => ipcRenderer.invoke('thor:openPreviewInBrowser', url),
  reachPreviewUrl: url => ipcRenderer.invoke('thor:preview:reach', url),
  setActiveConnectionRoute: route => ipcRenderer.send('thor:connection:active-route', route),
  fetchLinkTitle: url => ipcRenderer.invoke('thor:fetchLinkTitle', url),
  resolveFavicon: url => ipcRenderer.invoke('thor:resolveFavicon', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('thor:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('thor:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('thor:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('thor:setting:defaultProjectDir:pick')
  },
  preparedSubmissions: {
    read: () => ipcRenderer.invoke('thor:prepared-submissions:read'),
    update: (key, entry) => ipcRenderer.invoke('thor:prepared-submissions:update', key, entry),
    compareAndSet: (key, expected, entry) =>
      ipcRenderer.invoke('thor:prepared-submissions:compare-and-set', key, expected, entry)
  },
  zoom: {
    // Current zoom of this window, as { level, percent }.
    get: () => ipcRenderer.invoke('thor:zoom:get'),
    // Synchronous zoom factor (1 = 100%). Coordinate math needs it in the
    // same tick as the event it converts, so no IPC round-trip here.
    factor: () => webFrame.getZoomFactor(),
    setPercent: percent => ipcRenderer.send('thor:zoom:set-percent', percent),
    // Fires on every zoom change, including the Ctrl/Cmd +/-/0 shortcuts,
    // so the settings UI can stay in sync with the keyboard.
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:zoom:changed', listener)

      return () => ipcRenderer.removeListener('thor:zoom:changed', listener)
    }
  },
  revealLogs: () => ipcRenderer.invoke('thor:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('thor:logs:recent'),
  // Fire-and-forget: persists a renderer error-boundary catch (with component
  // stack) to desktop.log so crashes survive the window (#79428).
  reportRendererError: report => ipcRenderer.send('thor:logs:renderer-error', report),
  logLine: (line: string): void => ipcRenderer.send('thor:logs:renderer-line', line),
  readDir: dirPath => ipcRenderer.invoke('thor:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('thor:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('thor:fs:reveal', targetPath),
  openDir: dirPath => ipcRenderer.invoke('thor:fs:openDir', dirPath),
  desktopPluginsRoot: () => ipcRenderer.invoke('thor:fs:desktopPluginsRoot'),
  reconcileDesktopPlugins: async () => (await ipcRenderer.invoke('thor:fs:reconcileDesktopPlugins')).published,
  reconcileDesktopPluginsReport: () => ipcRenderer.invoke('thor:fs:reconcileDesktopPlugins'),
  logsRoot: (profile?: string) => ipcRenderer.invoke('thor:fs:logsRoot', profile),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('thor:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('thor:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('thor:fs:trash', targetPath),
  pluginFiles: {
    request: (pluginId, labels) => ipcRenderer.invoke('thor:pluginFiles:request', pluginId, labels),
    grants: pluginId => ipcRenderer.invoke('thor:pluginFiles:grants', pluginId),
    revoke: (pluginId, folderId) => ipcRenderer.invoke('thor:pluginFiles:revoke', pluginId, folderId),
    op: (pluginId, request) => ipcRenderer.invoke('thor:pluginFiles:op', pluginId, request),
    onChanged: callback => {
      const listener = (_event, change) => callback(change)
      ipcRenderer.on('thor:pluginFiles:changed', listener)

      return () => ipcRenderer.removeListener('thor:pluginFiles:changed', listener)
    }
  },
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('thor:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('thor:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('thor:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('thor:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('thor:git:branchList', repoPath),
    baseBranchList: repoPath => ipcRenderer.invoke('thor:git:baseBranchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('thor:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('thor:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('thor:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('thor:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('thor:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('thor:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('thor:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('thor:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('thor:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('thor:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('thor:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('thor:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('thor:git:review:shipInfo', repoPath),
      prList: (repoPath, branches, numbers) =>
        ipcRenderer.invoke('thor:git:review:prList', repoPath, branches, numbers),
      createPr: repoPath => ipcRenderer.invoke('thor:git:review:createPr', repoPath)
    }
  },
  terminal: {
    attach: id => ipcRenderer.invoke('thor:terminal:attach', id),
    cwd: id => ipcRenderer.invoke('thor:terminal:cwd', id),
    dispose: id => ipcRenderer.invoke('thor:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('thor:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('thor:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('thor:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `thor:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `thor:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:close-preview-requested', listener)

    return () => ipcRenderer.removeListener('thor:close-preview-requested', listener)
  },
  onPreviewNav: callback => {
    const listener = (_event, command) => callback(command)
    ipcRenderer.on('thor:preview-nav', listener)

    return () => ipcRenderer.removeListener('thor:preview-nav', listener)
  },
  onOpenFolderRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:open-folder-requested', listener)

    return () => ipcRenderer.removeListener('thor:open-folder-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:open-updates', listener)

    return () => ipcRenderer.removeListener('thor:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:deep-link', listener)

    return () => ipcRenderer.removeListener('thor:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('thor:deep-link-ready'),
  probePluginRepo: payload => ipcRenderer.invoke('thor:plugin:probe', payload),
  installDesktopPlugin: payload => ipcRenderer.invoke('thor:plugin:installDesktop', payload),
  removeDesktopPlugin: payload => ipcRenderer.invoke('thor:plugin:removeDesktop', payload),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:window-state-changed', listener)

    return () => ipcRenderer.removeListener('thor:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('thor:focus-session', listener)

    return () => ipcRenderer.removeListener('thor:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:notification-action', listener)

    return () => ipcRenderer.removeListener('thor:notification-action', listener)
  },
  onNotificationActivate: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:notification-activate', listener)

    return () => ipcRenderer.removeListener('thor:notification-activate', listener)
  },
  onExternalOpenFailed: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:external-open-failed', listener)

    return () => ipcRenderer.removeListener('thor:external-open-failed', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:preview-file-changed', listener)

    return () => ipcRenderer.removeListener('thor:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:backend-exit', listener)

    return () => ipcRenderer.removeListener('thor:backend-exit', listener)
  },
  // Soft gateway-mode apply finished tearing down the primary backend. Renderer
  // should wipe session lists + re-dial without a window reload.
  onConnectionApplied: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:connection:applied', listener)

    return () => ipcRenderer.removeListener('thor:connection:applied', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:power-resume', listener)

    return () => ipcRenderer.removeListener('thor:power-resume', listener)
  },
  // AC ↔ battery transitions; renderers slow their backstop polls on battery.
  getOnBattery: () => ipcRenderer.invoke('thor:power-battery:get'),
  onBatteryChanged: callback => {
    const listener = (_event, onBattery) => callback(Boolean(onBattery))
    ipcRenderer.on('thor:power-battery', listener)

    return () => ipcRenderer.removeListener('thor:power-battery', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:boot-progress', listener)

    return () => ipcRenderer.removeListener('thor:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.ts (apps/desktop/electron/bootstrap-runner.ts).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('thor:bootstrap:get'),
  probeLocalBackend: () => ipcRenderer.invoke('thor:local-backend:probe'),
  continueBootstrapLocal: () => ipcRenderer.invoke('thor:bootstrap:continue-local'),
  recycleBackend: profile => ipcRenderer.invoke('thor:backend:recycle', profile),
  resetBootstrap: () => ipcRenderer.invoke('thor:bootstrap:reset'),
  updateHold: {
    recheck: () => ipcRenderer.invoke('thor:update-hold:recheck'),
    quit: () => ipcRenderer.invoke('thor:update-hold:quit'),
    startAnyway: (request: { holdId: string; confirmed: true }) =>
      ipcRenderer.invoke('thor:update-hold:start-anyway', request)
  },
  repairBootstrap: () => ipcRenderer.invoke('thor:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('thor:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('thor:bootstrap:event', listener)

    return () => ipcRenderer.removeListener('thor:bootstrap:event', listener)
  },
  getVersion: (scope?: { connectionId?: string; profile?: string }) => ipcRenderer.invoke('thor:version', scope),
  relaunchApp: () => ipcRenderer.invoke('thor:app:relaunch'),
  getMachineProfile: () => ipcRenderer.invoke('thor:machine:profile'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('thor:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('thor:uninstall:summary'),
    run: mode => ipcRenderer.invoke('thor:uninstall:run', { mode }),
    openAppsSettings: () => ipcRenderer.invoke('thor:uninstall:openAppsSettings')
  },
  updates: {
    check: opts => ipcRenderer.invoke('thor:updates:check', opts),
    apply: opts => ipcRenderer.invoke('thor:updates:apply', opts),
    setChannel: name => ipcRenderer.invoke('thor:updates:channel:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('thor:updates:progress', listener)

      return () => ipcRenderer.removeListener('thor:updates:progress', listener)
    },
    takePendingRun: () => ipcRenderer.invoke('thor:updates:metric:take'),
    ackPendingRun: sent => ipcRenderer.invoke('thor:updates:metric:ack', sent),
    onPendingRun: callback => {
      const listener = () => callback()
      ipcRenderer.on('thor:updates:metric:pending', listener)

      return () => ipcRenderer.removeListener('thor:updates:metric:pending', listener)
    }
  },
  desktopMetrics: {
    setEnabled: (on, profile) => ipcRenderer.invoke('thor:desktop-metrics:set-enabled', on, profile),
    takeRendererCrashes: () => ipcRenderer.invoke('thor:desktop-metrics:crash:take'),
    ackRendererCrashes: sent => ipcRenderer.invoke('thor:desktop-metrics:crash:ack', sent)
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('thor:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('thor:vscode-theme:search', query)
  },
  // Find-in-page (Ctrl/Cmd+F): delegates to Electron's
  // webContents.findInPage on the IPC sender's window so a Cmd+F pressed
  // in a secondary session window searches THAT window, not the primary.
  // `onFoundInPage` returns the unsubscribe fn; the renderer wires it via
  // `initFindInPageListener` in store/find-in-page.ts and tears it down
  // when the FindBar unmounts.
  findInPage: (query, options) => ipcRenderer.invoke('thor:find-in-page', query, options),
  stopFindInPage: () => ipcRenderer.invoke('thor:stop-find-in-page'),
  onFoundInPage: callback => {
    const listener = (_event, result) => callback(result)
    ipcRenderer.on('thor:found-in-page', listener)

    return () => ipcRenderer.removeListener('thor:found-in-page', listener)
  },
  // Main-process `before-input-event` forwards Ctrl/Cmd+F here so renderer
  // can open the FindBar even when the GTK compositor has already grabbed
  // the chord at the windowing layer (#81727).
  onOpenFindBarRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('thor:open-find-bar', listener)

    return () => ipcRenderer.removeListener('thor:open-find-bar', listener)
  }
})
