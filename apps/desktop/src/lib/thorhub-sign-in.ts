/** ThorHub sign-in lives in Settings → Providers: the ThorHub card is an
 *  external flow (`thor auth add thor`) with copy + re-check. There is no
 *  in-app OAuth dialog for it — the Nous free-tier sign-in dialog is retired
 *  with the provider, so every surface that used to open it sends the user
 *  to the ThorHub card instead. */
export function openThorHubSignIn() {
  window.location.hash = '#/settings?tab=providers'
}
