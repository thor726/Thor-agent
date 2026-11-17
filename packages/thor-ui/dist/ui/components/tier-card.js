"use client";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
import { cn } from "../../utils/index.js";
import { Button } from "./button.js";
import { ImageDistortion } from "./image-distortion.js";
import { Typography } from "./typography/index.js";
export function TierCard({
  actionDisabled,
  actionLabel,
  badge,
  bullets,
  className,
  image,
  isCurrent = false,
  onAction,
  onSelect,
  overlay,
  price,
  selected = false,
  showSelector = false,
  tint,
  tintStrength,
  title
}) {
  return /* @__PURE__ */ jsxs("div", { className: cn("flex flex-col", className), children: [
    /* @__PURE__ */ jsxs(
      "button",
      {
        "aria-checked": showSelector ? selected : void 0,
        className: cn(
          "group relative flex w-full cursor-pointer flex-col border border-current/20",
          "text-left transition-colors duration-300",
          selected && "border-midground/60",
          isCurrent && !selected && "border-midground/30"
        ),
        onClick: onSelect,
        role: showSelector ? "radio" : void 0,
        type: "button",
        children: [
          /* @__PURE__ */ jsx(
            "span",
            {
              "aria-hidden": true,
              className: cn(
                "arc-border transition-opacity duration-200",
                selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              )
            }
          ),
          showSelector && /* @__PURE__ */ jsx(
            "span",
            {
              "aria-hidden": true,
              className: "bg-background-base/80 absolute top-3 right-3 z-[2] rounded-full p-1 backdrop-blur-sm",
              children: /* @__PURE__ */ jsx(
                "span",
                {
                  className: cn(
                    "block h-5 w-5 rounded-full border-2 transition-all",
                    selected ? "border-midground bg-midground" : "border-midground/50 group-hover:border-midground/80 bg-transparent"
                  )
                }
              )
            }
          ),
          /* @__PURE__ */ jsxs(
            "div",
            {
              className: "relative aspect-[3/4] min-h-0 w-full flex-1 overflow-hidden",
              style: { backgroundColor: "var(--background)" },
              children: [
                /* @__PURE__ */ jsx(
                  ImageDistortion,
                  {
                    active: selected,
                    src: image,
                    tint,
                    tintStrength
                  }
                ),
                overlay && /* @__PURE__ */ jsx(
                  "div",
                  {
                    className: "pointer-events-none absolute inset-0",
                    style: { backgroundColor: overlay, mixBlendMode: "color" }
                  }
                ),
                /* @__PURE__ */ jsxs("div", { className: "pointer-events-none absolute inset-0 z-[1] flex flex-col justify-between p-3", children: [
                  /* @__PURE__ */ jsxs("div", { className: "flex flex-col gap-0.5", children: [
                    /* @__PURE__ */ jsxs(
                      Typography,
                      {
                        variant: "sm",
                        className: cn(
                          "block drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)] text-[1.2rem]",
                          "transition-colors",
                          selected && "text-midground"
                        ),
                        style: selected ? { mixBlendMode: "plus-lighter" } : void 0,
                        children: [
                          title,
                          badge && /* @__PURE__ */ jsx("span", { className: "ml-1 opacity-50", children: badge })
                        ]
                      }
                    ),
                    price.secondary ? /* @__PURE__ */ jsxs(Fragment, { children: [
                      /* @__PURE__ */ jsxs(
                        Typography,
                        {
                          className: "block text-md line-through opacity-50 drop-shadow-[0_1px_3px_rgba(0,0,0,0.6)]",
                          expanded: true,
                          style: { mixBlendMode: "plus-lighter" },
                          children: [
                            price.secondary,
                            price.secondarySuffix && /* @__PURE__ */ jsx("span", { className: "text-[1rem]", children: price.secondarySuffix })
                          ]
                        }
                      ),
                      /* @__PURE__ */ jsxs(
                        Typography,
                        {
                          className: "block text-xl font-bold drop-shadow-[0_1px_3px_rgba(0,0,0,0.6)]",
                          expanded: true,
                          style: { mixBlendMode: "plus-lighter" },
                          children: [
                            price.primary,
                            price.primarySuffix && /* @__PURE__ */ jsxs("span", { className: "text-[1rem] opacity-60", children: [
                              " ",
                              price.primarySuffix
                            ] })
                          ]
                        }
                      )
                    ] }) : /* @__PURE__ */ jsxs(
                      Typography,
                      {
                        className: "block text-xl font-bold drop-shadow-[0_1px_3px_rgba(0,0,0,0.6)]",
                        expanded: true,
                        style: { mixBlendMode: "plus-lighter" },
                        children: [
                          price.primary,
                          price.primarySuffix && /* @__PURE__ */ jsx("span", { className: "text-[1rem] opacity-60", children: price.primarySuffix })
                        ]
                      }
                    )
                  ] }),
                  bullets.length > 0 && /* @__PURE__ */ jsx("ul", { className: "flex flex-col gap-1", children: bullets.map((bullet, i) => /* @__PURE__ */ jsxs(
                    "li",
                    {
                      className: cn(
                        "font-courier text-display text-[1rem] leading-tight tracking-tight",
                        "drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]"
                      ),
                      children: [
                        "\xB7 ",
                        bullet
                      ]
                    },
                    typeof bullet === "string" ? bullet : i
                  )) })
                ] })
              ]
            }
          )
        ]
      }
    ),
    actionLabel != null && /* @__PURE__ */ jsx(
      Button,
      {
        className: "mt-3 w-full",
        disabled: actionDisabled ?? isCurrent,
        invert: !selected && !isCurrent,
        onClick: onAction,
        outlined: !selected && !isCurrent,
        children: actionLabel
      }
    )
  ] });
}
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiPHN0ZGluPiJdLAogICJzb3VyY2VzQ29udGVudCI6IFsiJ3VzZSBjbGllbnQnXG5cbmltcG9ydCB7IGNuIH0gZnJvbSAnLi4vLi4vdXRpbHMnXG5cbmltcG9ydCB7IEJ1dHRvbiB9IGZyb20gJy4vYnV0dG9uJ1xuaW1wb3J0IHsgSW1hZ2VEaXN0b3J0aW9uIH0gZnJvbSAnLi9pbWFnZS1kaXN0b3J0aW9uJ1xuaW1wb3J0IHsgVHlwb2dyYXBoeSB9IGZyb20gJy4vdHlwb2dyYXBoeSdcblxuLyoqXG4gKiBTZWxlY3RhYmxlIHRpZXIgLyBwcmljaW5nIGNhcmQuIEZ1bGwtYmxlZWQgZGlzdG9ydGVkIGltYWdlIGJhY2tncm91bmQsXG4gKiByZWFkYWJsZSBvdmVybGF5IHRleHQsIGFuZCBhbiBhbmltYXRlZCBgLmFyYy1ib3JkZXJgIHNoaW1tZXIgb24gdGhlXG4gKiBzZWxlY3RlZCBzdGF0ZS4gRnVsbHkgcHJlc2VudGF0aW9uYWwgXHUyMDE0IHRoZSBjb25zdW1lciBvd25zIHRoZSBkYXRhXG4gKiAodGllciBzY2hlbWEsIHByaWNlIGZvcm1hdHRpbmcsIHRpZXIgaW1hZ2VyeSAvIHRpbnRzKS5cbiAqXG4gKiBWaXN1YWwgc3RhdGVzOlxuICogLSBgc2VsZWN0ZWRgOiBicmlnaHRlbnMgdGhlIGRpc3RvcnRpb24sIGFjdGl2YXRlcyBgLmFyYy1ib3JkZXJgLCBhbmRcbiAqICAgY29tcG9zaXRlcyB0aGUgaGVhZGxpbmUgLyBwcmljZSB3aXRoIGBtaXgtYmxlbmQtbW9kZTogcGx1cy1saWdodGVyYFxuICogICBzbyB0aGUgdGV4dCBsaWZ0cyBvZmYgdGhlIGltYWdlIHJlZ2FyZGxlc3Mgb2YgdGludC5cbiAqIC0gYGlzQ3VycmVudGA6IHN1YnRsZSBtaWRncm91bmQtdGludGVkIGJvcmRlciBoaW50IChzdXBwcmVzc2VkIHdoZW5cbiAqICAgYHNlbGVjdGVkYCB3aW5zKS5cbiAqIC0gYG92ZXJsYXlgOiBvcHRpb25hbCB0b3AtbGF5ZXIgY29sb3IgYmxlbmRlZCB3aXRoIGBtaXgtYmxlbmQtbW9kZTpcbiAqICAgY29sb3JgIFx1MjAxNCB1c2VkIGZvciB0aGUgXCJoaWdoZXN0IHRpZXJcIiByZWQgdHJlYXRtZW50IG9uIHRvcCBvZiBhbnlcbiAqICAgYmFzZSB0aW50LlxuICpcbiAqIFNlbGVjdGlvbiBhZmZvcmRhbmNlcyAob3B0LWluKTpcbiAqIC0gYHNob3dTZWxlY3RvcmA6IHJlbmRlcnMgYSByYWRpbyBpbmRpY2F0b3IgaW4gdGhlIHRvcC1yaWdodCBjb3JuZXIgYW5kXG4gKiAgIGV4cG9zZXMgdGhlIGNhcmQgYXMgYHJvbGU9XCJyYWRpb1wiYCByZWZsZWN0aW5nIGBzZWxlY3RlZGAuXG4gKiAtIGBhY3Rpb25MYWJlbGAgLyBgb25BY3Rpb25gOiByZW5kZXJzIGEgZnVsbC13aWR0aCBhY3Rpb24gYnV0dG9uIGJlbmVhdGhcbiAqICAgdGhlIGNhcmQuIEl0cyB2YXJpYW50IGlzIGRlcml2ZWQgZnJvbSBgc2VsZWN0ZWRgIC8gYGlzQ3VycmVudGAgKHNvbGlkXG4gKiAgIHdoZW4gc2VsZWN0ZWQsIHN1YnRsZSBvdGhlcndpc2UsIGRpc2FibGVkIGZvciB0aGUgY3VycmVudCBwbGFuKSB1bmxlc3NcbiAqICAgb3ZlcnJpZGRlbiB2aWEgYGFjdGlvbkRpc2FibGVkYC5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIFRpZXJDYXJkKHtcbiAgYWN0aW9uRGlzYWJsZWQsXG4gIGFjdGlvbkxhYmVsLFxuICBiYWRnZSxcbiAgYnVsbGV0cyxcbiAgY2xhc3NOYW1lLFxuICBpbWFnZSxcbiAgaXNDdXJyZW50ID0gZmFsc2UsXG4gIG9uQWN0aW9uLFxuICBvblNlbGVjdCxcbiAgb3ZlcmxheSxcbiAgcHJpY2UsXG4gIHNlbGVjdGVkID0gZmFsc2UsXG4gIHNob3dTZWxlY3RvciA9IGZhbHNlLFxuICB0aW50LFxuICB0aW50U3RyZW5ndGgsXG4gIHRpdGxlXG59OiBUaWVyQ2FyZFByb3BzKSB7XG4gIHJldHVybiAoXG4gICAgPGRpdiBjbGFzc05hbWU9e2NuKCdmbGV4IGZsZXgtY29sJywgY2xhc3NOYW1lKX0+XG4gICAgICA8YnV0dG9uXG4gICAgICAgIGFyaWEtY2hlY2tlZD17c2hvd1NlbGVjdG9yID8gc2VsZWN0ZWQgOiB1bmRlZmluZWR9XG4gICAgICAgIGNsYXNzTmFtZT17Y24oXG4gICAgICAgICAgJ2dyb3VwIHJlbGF0aXZlIGZsZXggdy1mdWxsIGN1cnNvci1wb2ludGVyIGZsZXgtY29sIGJvcmRlciBib3JkZXItY3VycmVudC8yMCcsXG4gICAgICAgICAgJ3RleHQtbGVmdCB0cmFuc2l0aW9uLWNvbG9ycyBkdXJhdGlvbi0zMDAnLFxuICAgICAgICAgIHNlbGVjdGVkICYmICdib3JkZXItbWlkZ3JvdW5kLzYwJyxcbiAgICAgICAgICBpc0N1cnJlbnQgJiYgIXNlbGVjdGVkICYmICdib3JkZXItbWlkZ3JvdW5kLzMwJ1xuICAgICAgICApfVxuICAgICAgICBvbkNsaWNrPXtvblNlbGVjdH1cbiAgICAgICAgcm9sZT17c2hvd1NlbGVjdG9yID8gJ3JhZGlvJyA6IHVuZGVmaW5lZH1cbiAgICAgICAgdHlwZT1cImJ1dHRvblwiXG4gICAgICA+XG4gICAgICAgIDxzcGFuXG4gICAgICAgICAgYXJpYS1oaWRkZW5cbiAgICAgICAgICBjbGFzc05hbWU9e2NuKFxuICAgICAgICAgICAgJ2FyYy1ib3JkZXIgdHJhbnNpdGlvbi1vcGFjaXR5IGR1cmF0aW9uLTIwMCcsXG4gICAgICAgICAgICBzZWxlY3RlZCA/ICdvcGFjaXR5LTEwMCcgOiAnb3BhY2l0eS0wIGdyb3VwLWhvdmVyOm9wYWNpdHktMTAwJ1xuICAgICAgICAgICl9XG4gICAgICAgIC8+XG5cbiAgICAgICAge3Nob3dTZWxlY3RvciAmJiAoXG4gICAgICAgICAgPHNwYW5cbiAgICAgICAgICAgIGFyaWEtaGlkZGVuXG4gICAgICAgICAgICBjbGFzc05hbWU9XCJiZy1iYWNrZ3JvdW5kLWJhc2UvODAgYWJzb2x1dGUgdG9wLTMgcmlnaHQtMyB6LVsyXSByb3VuZGVkLWZ1bGwgcC0xIGJhY2tkcm9wLWJsdXItc21cIlxuICAgICAgICAgID5cbiAgICAgICAgICAgIDxzcGFuXG4gICAgICAgICAgICAgIGNsYXNzTmFtZT17Y24oXG4gICAgICAgICAgICAgICAgJ2Jsb2NrIGgtNSB3LTUgcm91bmRlZC1mdWxsIGJvcmRlci0yIHRyYW5zaXRpb24tYWxsJyxcbiAgICAgICAgICAgICAgICBzZWxlY3RlZFxuICAgICAgICAgICAgICAgICAgPyAnYm9yZGVyLW1pZGdyb3VuZCBiZy1taWRncm91bmQnXG4gICAgICAgICAgICAgICAgICA6ICdib3JkZXItbWlkZ3JvdW5kLzUwIGdyb3VwLWhvdmVyOmJvcmRlci1taWRncm91bmQvODAgYmctdHJhbnNwYXJlbnQnXG4gICAgICAgICAgICAgICl9XG4gICAgICAgICAgICAvPlxuICAgICAgICAgIDwvc3Bhbj5cbiAgICAgICAgKX1cblxuICAgICAgICA8ZGl2XG4gICAgICAgICAgY2xhc3NOYW1lPVwicmVsYXRpdmUgYXNwZWN0LVszLzRdIG1pbi1oLTAgdy1mdWxsIGZsZXgtMSBvdmVyZmxvdy1oaWRkZW5cIlxuICAgICAgICAgIHN0eWxlPXt7IGJhY2tncm91bmRDb2xvcjogJ3ZhcigtLWJhY2tncm91bmQpJyB9fVxuICAgICAgICA+XG4gICAgICAgICAgPEltYWdlRGlzdG9ydGlvblxuICAgICAgICAgICAgYWN0aXZlPXtzZWxlY3RlZH1cbiAgICAgICAgICAgIHNyYz17aW1hZ2V9XG4gICAgICAgICAgICB0aW50PXt0aW50fVxuICAgICAgICAgICAgdGludFN0cmVuZ3RoPXt0aW50U3RyZW5ndGh9XG4gICAgICAgICAgLz5cblxuICAgICAgICAgIHtvdmVybGF5ICYmIChcbiAgICAgICAgICAgIDxkaXZcbiAgICAgICAgICAgICAgY2xhc3NOYW1lPVwicG9pbnRlci1ldmVudHMtbm9uZSBhYnNvbHV0ZSBpbnNldC0wXCJcbiAgICAgICAgICAgICAgc3R5bGU9e3sgYmFja2dyb3VuZENvbG9yOiBvdmVybGF5LCBtaXhCbGVuZE1vZGU6ICdjb2xvcicgfX1cbiAgICAgICAgICAgIC8+XG4gICAgICAgICAgKX1cblxuICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPVwicG9pbnRlci1ldmVudHMtbm9uZSBhYnNvbHV0ZSBpbnNldC0wIHotWzFdIGZsZXggZmxleC1jb2wganVzdGlmeS1iZXR3ZWVuIHAtM1wiPlxuICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJmbGV4IGZsZXgtY29sIGdhcC0wLjVcIj5cbiAgICAgICAgICAgICAgPFR5cG9ncmFwaHlcbiAgICAgICAgICAgICAgICB2YXJpYW50PVwic21cIlxuICAgICAgICAgICAgICAgIGNsYXNzTmFtZT17Y24oXG4gICAgICAgICAgICAgICAgICAnYmxvY2sgZHJvcC1zaGFkb3ctWzBfMXB4XzJweF9yZ2JhKDAsMCwwLDAuNSldIHRleHQtWzEuMnJlbV0nLFxuICAgICAgICAgICAgICAgICAgJ3RyYW5zaXRpb24tY29sb3JzJyxcbiAgICAgICAgICAgICAgICAgIHNlbGVjdGVkICYmICd0ZXh0LW1pZGdyb3VuZCdcbiAgICAgICAgICAgICAgICApfVxuICAgICAgICAgICAgICAgIHN0eWxlPXtzZWxlY3RlZCA/IHsgbWl4QmxlbmRNb2RlOiAncGx1cy1saWdodGVyJyB9IDogdW5kZWZpbmVkfVxuICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAge3RpdGxlfVxuICAgICAgICAgICAgICAgIHtiYWRnZSAmJiA8c3BhbiBjbGFzc05hbWU9XCJtbC0xIG9wYWNpdHktNTBcIj57YmFkZ2V9PC9zcGFuPn1cbiAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuXG4gICAgICAgICAgICAgIHtwcmljZS5zZWNvbmRhcnkgPyAoXG4gICAgICAgICAgICAgICAgPD5cbiAgICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5XG4gICAgICAgICAgICAgICAgICAgIGNsYXNzTmFtZT1cImJsb2NrIHRleHQtbWQgbGluZS10aHJvdWdoIG9wYWNpdHktNTAgZHJvcC1zaGFkb3ctWzBfMXB4XzNweF9yZ2JhKDAsMCwwLDAuNildXCJcbiAgICAgICAgICAgICAgICAgICAgZXhwYW5kZWRcbiAgICAgICAgICAgICAgICAgICAgc3R5bGU9e3sgbWl4QmxlbmRNb2RlOiAncGx1cy1saWdodGVyJyB9fVxuICAgICAgICAgICAgICAgICAgPlxuICAgICAgICAgICAgICAgICAgICB7cHJpY2Uuc2Vjb25kYXJ5fVxuICAgICAgICAgICAgICAgICAgICB7cHJpY2Uuc2Vjb25kYXJ5U3VmZml4ICYmIChcbiAgICAgICAgICAgICAgICAgICAgICA8c3BhbiBjbGFzc05hbWU9XCJ0ZXh0LVsxcmVtXVwiPlxuICAgICAgICAgICAgICAgICAgICAgICAge3ByaWNlLnNlY29uZGFyeVN1ZmZpeH1cbiAgICAgICAgICAgICAgICAgICAgICA8L3NwYW4+XG4gICAgICAgICAgICAgICAgICAgICl9XG4gICAgICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG5cbiAgICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5XG4gICAgICAgICAgICAgICAgICAgIGNsYXNzTmFtZT1cImJsb2NrIHRleHQteGwgZm9udC1ib2xkIGRyb3Atc2hhZG93LVswXzFweF8zcHhfcmdiYSgwLDAsMCwwLjYpXVwiXG4gICAgICAgICAgICAgICAgICAgIGV4cGFuZGVkXG4gICAgICAgICAgICAgICAgICAgIHN0eWxlPXt7IG1peEJsZW5kTW9kZTogJ3BsdXMtbGlnaHRlcicgfX1cbiAgICAgICAgICAgICAgICAgID5cbiAgICAgICAgICAgICAgICAgICAge3ByaWNlLnByaW1hcnl9XG4gICAgICAgICAgICAgICAgICAgIHtwcmljZS5wcmltYXJ5U3VmZml4ICYmIChcbiAgICAgICAgICAgICAgICAgICAgICA8c3BhbiBjbGFzc05hbWU9XCJ0ZXh0LVsxcmVtXSBvcGFjaXR5LTYwXCI+XG4gICAgICAgICAgICAgICAgICAgICAgICB7JyAnfVxuICAgICAgICAgICAgICAgICAgICAgICAge3ByaWNlLnByaW1hcnlTdWZmaXh9XG4gICAgICAgICAgICAgICAgICAgICAgPC9zcGFuPlxuICAgICAgICAgICAgICAgICAgICApfVxuICAgICAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICAgIDwvPlxuICAgICAgICAgICAgICApIDogKFxuICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5XG4gICAgICAgICAgICAgICAgICBjbGFzc05hbWU9XCJibG9jayB0ZXh0LXhsIGZvbnQtYm9sZCBkcm9wLXNoYWRvdy1bMF8xcHhfM3B4X3JnYmEoMCwwLDAsMC42KV1cIlxuICAgICAgICAgICAgICAgICAgZXhwYW5kZWRcbiAgICAgICAgICAgICAgICAgIHN0eWxlPXt7IG1peEJsZW5kTW9kZTogJ3BsdXMtbGlnaHRlcicgfX1cbiAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICB7cHJpY2UucHJpbWFyeX1cbiAgICAgICAgICAgICAgICAgIHtwcmljZS5wcmltYXJ5U3VmZml4ICYmIChcbiAgICAgICAgICAgICAgICAgICAgPHNwYW4gY2xhc3NOYW1lPVwidGV4dC1bMXJlbV0gb3BhY2l0eS02MFwiPlxuICAgICAgICAgICAgICAgICAgICAgIHtwcmljZS5wcmltYXJ5U3VmZml4fVxuICAgICAgICAgICAgICAgICAgICA8L3NwYW4+XG4gICAgICAgICAgICAgICAgICApfVxuICAgICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgIDwvZGl2PlxuXG4gICAgICAgICAgICB7YnVsbGV0cy5sZW5ndGggPiAwICYmIChcbiAgICAgICAgICAgICAgPHVsIGNsYXNzTmFtZT1cImZsZXggZmxleC1jb2wgZ2FwLTFcIj5cbiAgICAgICAgICAgICAgICB7YnVsbGV0cy5tYXAoKGJ1bGxldCwgaSkgPT4gKFxuICAgICAgICAgICAgICAgICAgPGxpXG4gICAgICAgICAgICAgICAgICAgIGNsYXNzTmFtZT17Y24oXG4gICAgICAgICAgICAgICAgICAgICAgJ2ZvbnQtY291cmllciB0ZXh0LWRpc3BsYXkgdGV4dC1bMXJlbV0gbGVhZGluZy10aWdodCB0cmFja2luZy10aWdodCcsXG4gICAgICAgICAgICAgICAgICAgICAgJ2Ryb3Atc2hhZG93LVswXzFweF8ycHhfcmdiYSgwLDAsMCwwLjUpXSdcbiAgICAgICAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgICAgICAgICAga2V5PXt0eXBlb2YgYnVsbGV0ID09PSAnc3RyaW5nJyA/IGJ1bGxldCA6IGl9XG4gICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgIFx1MDBCNyB7YnVsbGV0fVxuICAgICAgICAgICAgICAgICAgPC9saT5cbiAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgPC91bD5cbiAgICAgICAgICAgICl9XG4gICAgICAgICAgPC9kaXY+XG4gICAgICAgIDwvZGl2PlxuICAgICAgPC9idXR0b24+XG5cbiAgICAgIHthY3Rpb25MYWJlbCAhPSBudWxsICYmIChcbiAgICAgICAgPEJ1dHRvblxuICAgICAgICAgIGNsYXNzTmFtZT1cIm10LTMgdy1mdWxsXCJcbiAgICAgICAgICBkaXNhYmxlZD17YWN0aW9uRGlzYWJsZWQgPz8gaXNDdXJyZW50fVxuICAgICAgICAgIGludmVydD17IXNlbGVjdGVkICYmICFpc0N1cnJlbnR9XG4gICAgICAgICAgb25DbGljaz17b25BY3Rpb259XG4gICAgICAgICAgb3V0bGluZWQ9eyFzZWxlY3RlZCAmJiAhaXNDdXJyZW50fVxuICAgICAgICA+XG4gICAgICAgICAge2FjdGlvbkxhYmVsfVxuICAgICAgICA8L0J1dHRvbj5cbiAgICAgICl9XG4gICAgPC9kaXY+XG4gIClcbn1cblxuZXhwb3J0IGludGVyZmFjZSBUaWVyQ2FyZFByaWNlIHtcbiAgLyoqIEhlYWRsaW5lIHByaWNlLCBlLmcuIGBcIiQyMFwiYCBvciBgXCJGcmVlXCJgLiAqL1xuICBwcmltYXJ5OiBzdHJpbmdcbiAgLyoqIFNtYWxsIHN1ZmZpeCByZW5kZXJlZCBhZnRlciBgcHJpbWFyeWAsIGUuZy4gYFwiL21vXCJgIG9yIGBcImZpcnN0IHBheW1lbnRcImAuICovXG4gIHByaW1hcnlTdWZmaXg/OiBzdHJpbmdcbiAgLyoqIE9wdGlvbmFsIHN0cnVjay10aHJvdWdoIGNvbXBhcmlzb24gcHJpY2UgcmVuZGVyZWQgYWJvdmUgYHByaW1hcnlgLCBlLmcuIGBcIiQzMFwiYC4gKi9cbiAgc2Vjb25kYXJ5Pzogc3RyaW5nXG4gIC8qKiBTbWFsbCBzdWZmaXggcmVuZGVyZWQgYWZ0ZXIgYHNlY29uZGFyeWAuICovXG4gIHNlY29uZGFyeVN1ZmZpeD86IHN0cmluZ1xufVxuXG5leHBvcnQgaW50ZXJmYWNlIFRpZXJDYXJkUHJvcHMge1xuICAvKipcbiAgICogT3ZlcnJpZGVzIHRoZSBhY3Rpb24gYnV0dG9uJ3MgZGlzYWJsZWQgc3RhdGUuIFdoZW4gb21pdHRlZCwgdGhlIGJ1dHRvblxuICAgKiBpcyBkaXNhYmxlZCBmb3IgdGhlIGN1cnJlbnQgcGxhbiAoYGlzQ3VycmVudGApLlxuICAgKi9cbiAgYWN0aW9uRGlzYWJsZWQ/OiBib29sZWFuXG4gIC8qKlxuICAgKiBMYWJlbCBmb3IgdGhlIGFjdGlvbiBidXR0b24gcmVuZGVyZWQgYmVuZWF0aCB0aGUgY2FyZC4gV2hlbiBgbnVsbGAgL1xuICAgKiBgdW5kZWZpbmVkYCwgbm8gYWN0aW9uIGJ1dHRvbiBpcyByZW5kZXJlZC5cbiAgICovXG4gIGFjdGlvbkxhYmVsPzogUmVhY3QuUmVhY3ROb2RlXG4gIC8qKiBTbWFsbCBhbm5vdGF0aW9uIGFmdGVyIHRoZSB0aXRsZSwgZS5nLiBgXCIoY3VycmVudClcImAuICovXG4gIGJhZGdlPzogUmVhY3QuUmVhY3ROb2RlXG4gIC8qKiBGZWF0dXJlIGxpc3QgcmVuZGVyZWQgdW5kZXIgdGhlIHByaWNlLiAqL1xuICBidWxsZXRzOiBSZWFjdC5SZWFjdE5vZGVbXVxuICBjbGFzc05hbWU/OiBzdHJpbmdcbiAgLyoqIEJhY2tncm91bmQgaW1hZ2UgVVJMLiAqL1xuICBpbWFnZTogc3RyaW5nXG4gIC8qKiBBcHBsaWVzIHRoZSBcImN1cnJlbnQgcGxhblwiIGJvcmRlciBoaW50IHdoZW4gbm90IGBzZWxlY3RlZGAuICovXG4gIGlzQ3VycmVudD86IGJvb2xlYW5cbiAgLyoqIENsaWNrIGhhbmRsZXIgZm9yIHRoZSBhY3Rpb24gYnV0dG9uIHJlbmRlcmVkIGJlbmVhdGggdGhlIGNhcmQuICovXG4gIG9uQWN0aW9uPzogKCkgPT4gdm9pZFxuICBvblNlbGVjdD86ICgpID0+IHZvaWRcbiAgLyoqIENvbG9yIGJsZW5kZWQgd2l0aCBgbWl4LWJsZW5kLW1vZGU6IGNvbG9yYCBvdmVyIHRoZSBpbWFnZSAodXNlZCBmb3IgdGhlIGhpZ2hlc3QtdGllciByZWQgdHJlYXRtZW50KS4gKi9cbiAgb3ZlcmxheT86IHN0cmluZ1xuICBwcmljZTogVGllckNhcmRQcmljZVxuICAvKiogQXBwbGllcyBzZWxlY3RlZCBjaHJvbWUgKGFyYy1ib3JkZXIgc2hpbW1lciwgYWN0aXZlIGRpc3RvcnRpb24sIHBsdXMtbGlnaHRlciB0ZXh0IGJsZW5kKS4gKi9cbiAgc2VsZWN0ZWQ/OiBib29sZWFuXG4gIC8qKiBSZW5kZXJzIGEgcmFkaW8gc2VsZWN0aW9uIGluZGljYXRvciBhbmQgZXhwb3NlcyB0aGUgY2FyZCBhcyBgcm9sZT1cInJhZGlvXCJgLiAqL1xuICBzaG93U2VsZWN0b3I/OiBib29sZWFuXG4gIC8qKiBTaGFkZXIgdGludCBwYXNzZWQgdGhyb3VnaCB0byBgSW1hZ2VEaXN0b3J0aW9uYC4gKi9cbiAgdGludD86IHN0cmluZ1xuICAvKiogQWN0aXZlIC8gaW5hY3RpdmUgdGludCBzdHJlbmd0aCBwYXNzZWQgdGhyb3VnaCB0byBgSW1hZ2VEaXN0b3J0aW9uYC4gKi9cbiAgdGludFN0cmVuZ3RoPzogeyBhY3RpdmU6IG51bWJlcjsgaW5hY3RpdmU6IG51bWJlciB9XG4gIC8qKiBUaWVyIG5hbWUgLyBoZWFkbGluZS4gKi9cbiAgdGl0bGU6IFJlYWN0LlJlYWN0Tm9kZVxufVxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQWdFUSxTQTBEUSxVQTFE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
