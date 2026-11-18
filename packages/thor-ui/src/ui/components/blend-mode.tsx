'use client'

import { useStore } from '@nanostores/react'
import { atom } from 'nanostores'
import { createElement, useMemo } from 'react'

import { getControlAtom } from '../../hooks/use-smooth-controls'
import { cn, type PolyProps, polyRef } from '../../utils'
import { colorDodge, colorMix } from '../../utils/color'

const LAYER_KEYS = { bg: 'bgColor', fg: 'fgColor', mg: 'mgColor' } as const
type Layer = keyof typeof LAYER_KEYS
type LayerSpec = `${Layer}/${number}` | Layer

const parseSpec = (spec: LayerSpec): [Layer, number?] => {
  const [layer, alpha] = spec.split('/') as [Layer, string?]

  return [layer, alpha ? parseFloat(alpha) : undefined]
}

// Stable sentinel atom subscribed to when no Lens control atom exists yet.
// `getControlAtom` returns `undefined` until a `useSmoothControls('Lens', …)`
// consumer lazily registers the Lens atoms during render — so the lookup can
// flip from `undefined` to a real atom *between* two renders of the same
// component. Subscribing to this sentinel keeps the `useStore` hook call
// unconditional (same hook count every render) and avoids React error #310
// ("Rendered more hooks than during the previous render"). nanostores'
// useStore re-subscribes safely when the atom argument changes.
const EMPTY_ATOM = atom<string | undefined>(undefined)

const useControlColor = (key: string, fallback: string) => {
  const controlAtom = getControlAtom<string>('Lens', key)

  return useStore(controlAtom ?? EMPTY_ATOM) ?? fallback
}

const useBlend = (against: Layer, spec?: LayerSpec | string) => {
  const layerKey = spec?.split('/')[0]
  const isLayerSpec = layerKey && layerKey in LAYER_KEYS

  const [target, alpha] = isLayerSpec
    ? parseSpec(spec as LayerSpec)
    : [undefined, undefined]

  const againstColor = useControlColor(LAYER_KEYS[against], '#041c1c')
  const fgColor = useControlColor(LAYER_KEYS.fg, '#ffe6cb')
  const mgColor = useControlColor(LAYER_KEYS.mg, '#ffe6cb')
  const bgColor = useControlColor(LAYER_KEYS.bg, '#ffe6cb')

  const targetColor = target
    ? target === 'fg'
      ? fgColor
      : target === 'mg'
        ? mgColor
        : bgColor
    : spec

  return useMemo(() => {
    if (!spec || !targetColor) {
      return undefined
    }

    const result = colorDodge(againstColor, targetColor)

    return alpha != null ? colorMix(result, alpha) : result
  }, [spec, againstColor, targetColor, alpha])
}

export const useBlendMode = (opts: BlendModeOpts = {}): BlendColors => {
  const { against = 'bg', background, color } = opts

  return {
    backgroundColor: useBlend(against, background),
    color: useBlend(against, color)
  }
}

export const withBlendMode = <P extends BlendColors>(
  Component: React.ComponentType<P>,
  opts?: BlendModeOpts
) => {
  const Wrapped = (
    props: Omit<P, keyof BlendColors> & Partial<BlendModeOpts>
  ) => {
    const { against, background, color, ...rest } = props as P & BlendModeOpts

    const colors = useBlendMode({
      against: against ?? opts?.against,
      background: background ?? opts?.background,
      color: color ?? opts?.color
    })

    return <Component {...(rest as P)} {...colors} />
  }

  Wrapped.displayName = `withBlendMode(${Component.displayName ?? Component.name ?? 'Component'})`

  return Wrapped
}

export const BlendMode = polyRef<'div', BlendModeOwnProps>(
  (
    { against, as, background, children, className, color, style, ...rest },
    ref
  ) => {
    const colors = useBlendMode({ against, background, color })

    if (typeof children === 'function') {
      return <>{children(colors)}</>
    }

    return createElement((as ?? 'div') as React.ElementType, {
      ...rest,
      children,
      className: cn(className),
      ref,
      style: { ...colors, ...style }
    })
  }
)

interface BlendModeOwnProps extends BlendModeOpts {
  children?: ((colors: BlendColors) => React.ReactNode) | React.ReactNode
}

export interface BlendColors {
  backgroundColor?: string
  color?: string
}

interface BlendModeOpts {
  against?: Layer
  background?: LayerSpec | string
  color?: LayerSpec | string
}

export type BlendModeProps<T extends React.ElementType = 'div'> = PolyProps<
  T,
  BlendModeOwnProps
>
