import { describe, expect, it, vi } from "vitest";

import { createMobileImeRescue } from "./pty-mobile-ime-rescue";

/** Minimal textarea stand-in: only what the guard touches. */
function makeTextarea(initial = "") {
  const listeners = new Map<string, EventListener[]>();
  let value = initial;
  return {
    get value() {
      return value;
    },
    set value(next: string) {
      value = next;
    },
    addEventListener(type: string, fn: EventListener) {
      listeners.set(type, [...(listeners.get(type) ?? []), fn]);
    },
    removeEventListener(type: string, fn: EventListener) {
      listeners.set(type, (listeners.get(type) ?? []).filter((l) => l !== fn));
    },
    dispatch(type: string, event: Partial<InputEvent>) {
      for (const fn of listeners.get(type) ?? []) fn(event as unknown as Event);
    },
  } as unknown as HTMLTextAreaElement & {
    value: string;
    dispatch(type: string, event: Partial<InputEvent>): void;
  };
}

/** Runs the setTimeout(..., 0) the guard schedules. */
const tick = () => new Promise((resolve) => setTimeout(resolve, 1));

describe("createMobileImeRescue", () => {
  const setup = (initial = "") => {
    const el = makeTextarea(initial);
    const onData = vi.fn();
    let composing = false;
    const rescue = createMobileImeRescue({
      onData,
      getValue: () => el.value,
      isComposing: () => composing,
      isMobileLike: true,
    });
    const detach = rescue.attach(el);
    return {
      el,
      onData,
      detach,
      setComposing: (v: boolean) => {
        composing = v;
      },
    };
  };

  it("forwards insertCompositionText, which xterm 6.0.0 drops", async () => {
    const { el, onData } = setup();
    el.value = "h";
    el.dispatch("beforeinput", { inputType: "insertCompositionText", data: "h" });
    el.dispatch("input", { inputType: "insertCompositionText", data: "h" });
    await tick();
    expect(onData).toHaveBeenCalledWith("h");
  });

  it("forwards insertReplacementText", async () => {
    const { el, onData } = setup();
    el.value = "k";
    el.dispatch("beforeinput", { inputType: "insertReplacementText", data: "k" });
    el.dispatch("input", { inputType: "insertReplacementText", data: "k" });
    await tick();
    expect(onData).toHaveBeenCalledWith("k");
  });

  it("does not forward insertText — xterm already delivers it", async () => {
    const { el, onData } = setup();
    el.value = "a";
    el.dispatch("beforeinput", { inputType: "insertText", data: "a" });
    el.dispatch("input", { inputType: "insertText", data: "a" });
    await tick();
    expect(onData).not.toHaveBeenCalled();
  });

  it("delivers each character exactly once across a burst", async () => {
    const { el, onData } = setup();
    for (const ch of "tes") {
      el.value += ch;
      el.dispatch("beforeinput", { inputType: "insertCompositionText", data: ch });
      el.dispatch("input", { inputType: "insertCompositionText", data: ch });
      await tick();
    }
    expect(onData.mock.calls.map((c) => c[0]).join("")).toBe("tes");
  });

  it("stays silent while a composition is open (compositionend owns it)", async () => {
    const { el, onData, setComposing } = setup();
    setComposing(true);
    el.value = "あ";
    el.dispatch("beforeinput", { inputType: "insertCompositionText", data: "あ" });
    el.dispatch("input", { inputType: "insertCompositionText", data: "あ" });
    await tick();
    expect(onData).not.toHaveBeenCalled();
  });

  it("sends only the new suffix when the IME extends the buffer", async () => {
    const { el, onData } = setup("ab");
    el.value = "abc";
    el.dispatch("input", { inputType: "insertCompositionText", data: "c" });
    await tick();
    expect(onData).toHaveBeenCalledTimes(1);
    expect(onData).toHaveBeenCalledWith("c");
  });

  it("resyncs without re-sending when the IME rewrites the buffer", async () => {
    const { el, onData } = setup("hello");
    el.value = "help"; // auto-correct replaced the tail
    el.dispatch("input", { inputType: "insertReplacementText", data: "help" });
    await tick();
    expect(onData).not.toHaveBeenCalled();
    // A later clean append still works from the new baseline.
    el.value = "help!";
    el.dispatch("input", { inputType: "insertCompositionText", data: "!" });
    await tick();
    expect(onData).toHaveBeenCalledWith("!");
  });

  it("attaches nothing on a non-mobile browser", async () => {
    const el = makeTextarea();
    const onData = vi.fn();
    const rescue = createMobileImeRescue({
      onData,
      getValue: () => el.value,
      isComposing: () => false,
      isMobileLike: false,
    });
    rescue.attach(el);
    el.value = "h";
    el.dispatch("input", { inputType: "insertCompositionText", data: "h" });
    await tick();
    expect(onData).not.toHaveBeenCalled();
  });

  it("stops forwarding after detach", async () => {
    const { el, onData, detach } = setup();
    detach();
    el.value = "z";
    el.dispatch("input", { inputType: "insertCompositionText", data: "z" });
    await tick();
    expect(onData).not.toHaveBeenCalled();
  });
});
