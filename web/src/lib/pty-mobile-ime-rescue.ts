/**
 * Mobile-IME keystroke rescue.
 *
 * xterm.js 6.0.0's `_inputEvent` only accepts `inputType === "insertText"`
 * (see `lib/xterm.js`, `_inputEvent`). Android soft keyboards deliver most
 * typing as `insertCompositionText` or `insertReplacementText` instead, and
 * some builds commit that way *without ever firing `compositionend`* — so
 * xterm's own IME path and ChatPage's compositionend forwarder both stay
 * silent and the keystroke is lost before it reaches the PTY.
 *
 * This guard sits on xterm's hidden textarea and forwards those committed
 * characters itself, while suppressing the cases xterm already handles so a
 * character can never be delivered twice:
 *
 *   - `insertText`                        -> xterm handles it (skip here)
 *   - `insertCompositionText`/`Replacement` -> forwarded by this guard
 *   - composition in progress (`isComposing`) -> left to `compositionend`
 *
 * The tracker remembers the textarea value it last accounted for, so a
 * keystroke is forwarded exactly once regardless of how many events the IME
 * emits for it.
 */

/** Input types whose committed text xterm.js 6.0.0 drops on the floor. */
const RESCUED_INPUT_TYPES = new Set([
  "insertCompositionText",
  "insertReplacementText",
]);

export interface MobileImeRescueOptions {
  /** Called with the characters that xterm failed to deliver. */
  onData: (data: string) => void;
  /** Read the textarea whose value tracks what the user committed. */
  getValue: () => string;
  /** True while an IME composition is open (defer to compositionend). */
  isComposing: () => boolean;
  /** True when this browser is a mobile/touch device. */
  isMobileLike: boolean;
}

export function createMobileImeRescue(options: MobileImeRescueOptions) {
  const { onData, getValue, isComposing, isMobileLike } = options;
  // Longest textarea value already accounted for; anything beyond it is new.
  let accounted = "";
  let disposed = false;

  /** Characters present in the textarea but not yet sent to the PTY. */
  const takeNewText = (value: string): string => {
    if (value === accounted) return "";
    if (value.startsWith(accounted)) {
      const fresh = value.slice(accounted.length);
      accounted = value;
      return fresh;
    }
    // The IME rewrote the buffer (auto-correct, suggestion replace). Sending
    // the whole value again would duplicate what the PTY already has, and we
    // cannot tell how much of the line to erase — so resync silently and let
    // the compositionend path own that gesture.
    accounted = value;
    return "";
  };

  const flush = (): void => {
    if (disposed || isComposing()) return;
    const fresh = takeNewText(getValue());
    if (fresh) onData(fresh);
  };

  /** A committed character the IME will not report through compositionend. */
  const onBeforeInput = (ev: Event): void => {
    const input = ev as InputEvent;
    if (!input.inputType || !RESCUED_INPUT_TYPES.has(input.inputType)) return;
    // Defer to compositionend when the IME is mid-composition; Android's
    // non-composition commit (the case this rescues) never fires it.
    if (isComposing()) return;
    // Let xterm's own handler run first so its internal bookkeeping stays in
    // sync, then forward whatever it did not emit.
    setTimeout(flush, 0);
  };

  /** With no compositionend coming, this is the only signal we get. */
  const onInput = (ev: Event): void => {
    const input = ev as InputEvent;
    if (input.inputType && input.inputType !== "insertText" && !isComposing()) {
      setTimeout(flush, 0);
    }
  };

  const attach = (textarea: HTMLTextAreaElement): (() => void) => {
    if (!isMobileLike) return () => undefined;
    // Baseline: whatever is already in the textarea belongs to earlier input.
    accounted = getValue();
    textarea.addEventListener("beforeinput", onBeforeInput, true);
    textarea.addEventListener("input", onInput, true);
    return () => {
      disposed = true;
      textarea.removeEventListener("beforeinput", onBeforeInput, true);
      textarea.removeEventListener("input", onInput, true);
    };
  };

  return { attach, flush };
}
