'use client'

import { cn } from '../../utils'

import { Button } from './button'
import { ImageDistortion } from './image-distortion'
import { Typography } from './typography'

/**
 * Selectable tier / pricing card. Full-bleed distorted image background,
 * readable overlay text, and an animated `.arc-border` shimmer on the
 * selected state. Fully presentational — the consumer owns the data
 * (tier schema, price formatting, tier imagery / tints).
 *
 * Visual states:
 * - `selected`: brightens the distortion, activates `.arc-border`, and
 *   composites the headline / price with `mix-blend-mode: plus-lighter`
 *   so the text lifts off the image regardless of tint.
 * - `isCurrent`: subtle midground-tinted border hint (suppressed when
 *   `selected` wins).
 * - `overlay`: optional top-layer color blended with `mix-blend-mode:
 *   color` — used for the "highest tier" red treatment on top of any
 *   base tint.
 *
 * Selection affordances (opt-in):
 * - `showSelector`: renders a radio indicator in the top-right corner and
 *   exposes the card as `role="radio"` reflecting `selected`.
 * - `actionLabel` / `onAction`: renders a full-width action button beneath
 *   the card. Its variant is derived from `selected` / `isCurrent` (solid
 *   when selected, subtle otherwise, disabled for the current plan) unless
 *   overridden via `actionDisabled`.
 */
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
}: TierCardProps) {
  return (
    <div className={cn('flex flex-col', className)}>
      <button
        aria-checked={showSelector ? selected : undefined}
        className={cn(
          'group relative flex w-full cursor-pointer flex-col border border-current/20',
          'text-left transition-colors duration-300',
          selected && 'border-midground/60',
          isCurrent && !selected && 'border-midground/30'
        )}
        onClick={onSelect}
        role={showSelector ? 'radio' : undefined}
        type="button"
      >
        <span
          aria-hidden
          className={cn(
            'arc-border transition-opacity duration-200',
            selected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
          )}
        />

        {showSelector && (
          <span
            aria-hidden
            className="bg-background-base/80 absolute top-3 right-3 z-[2] rounded-full p-1 backdrop-blur-sm"
          >
            <span
              className={cn(
                'block h-5 w-5 rounded-full border-2 transition-all',
                selected
                  ? 'border-midground bg-midground'
                  : 'border-midground/50 group-hover:border-midground/80 bg-transparent'
              )}
            />
          </span>
        )}

        <div
          className="relative aspect-[3/4] min-h-0 w-full flex-1 overflow-hidden"
          style={{ backgroundColor: 'var(--background)' }}
        >
          <ImageDistortion
            active={selected}
            src={image}
            tint={tint}
            tintStrength={tintStrength}
          />

          {overlay && (
            <div
              className="pointer-events-none absolute inset-0"
              style={{ backgroundColor: overlay, mixBlendMode: 'color' }}
            />
          )}

          <div className="pointer-events-none absolute inset-0 z-[1] flex flex-col justify-between p-3">
            <div className="flex flex-col gap-0.5">
              <Typography
                variant="sm"
                className={cn(
                  'block drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)] text-[1.2rem]',
                  'transition-colors',
                  selected && 'text-midground'
                )}
                style={selected ? { mixBlendMode: 'plus-lighter' } : undefined}
              >
                {title}
                {badge && <span className="ml-1 opacity-50">{badge}</span>}
              </Typography>

              {price.secondary ? (
                <>
                  <Typography
                    className="block text-md line-through opacity-50 drop-shadow-[0_1px_3px_rgba(0,0,0,0.6)]"
                    expanded
                    style={{ mixBlendMode: 'plus-lighter' }}
                  >
                    {price.secondary}
                    {price.secondarySuffix && (
                      <span className="text-[1rem]">
                        {price.secondarySuffix}
                      </span>
                    )}
                  </Typography>

                  <Typography
                    className="block text-xl font-bold drop-shadow-[0_1px_3px_rgba(0,0,0,0.6)]"
                    expanded
                    style={{ mixBlendMode: 'plus-lighter' }}
                  >
                    {price.primary}
                    {price.primarySuffix && (
                      <span className="text-[1rem] opacity-60">
                        {' '}
                        {price.primarySuffix}
                      </span>
                    )}
                  </Typography>
                </>
              ) : (
                <Typography
                  className="block text-xl font-bold drop-shadow-[0_1px_3px_rgba(0,0,0,0.6)]"
                  expanded
                  style={{ mixBlendMode: 'plus-lighter' }}
                >
                  {price.primary}
                  {price.primarySuffix && (
                    <span className="text-[1rem] opacity-60">
                      {price.primarySuffix}
                    </span>
                  )}
                </Typography>
              )}
            </div>

            {bullets.length > 0 && (
              <ul className="flex flex-col gap-1">
                {bullets.map((bullet, i) => (
                  <li
                    className={cn(
                      'font-courier text-display text-[1rem] leading-tight tracking-tight',
                      'drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]'
                    )}
                    key={typeof bullet === 'string' ? bullet : i}
                  >
                    · {bullet}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </button>

      {actionLabel != null && (
        <Button
          className="mt-3 w-full"
          disabled={actionDisabled ?? isCurrent}
          invert={!selected && !isCurrent}
          onClick={onAction}
          outlined={!selected && !isCurrent}
        >
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

export interface TierCardPrice {
  /** Headline price, e.g. `"$20"` or `"Free"`. */
  primary: string
  /** Small suffix rendered after `primary`, e.g. `"/mo"` or `"first payment"`. */
  primarySuffix?: string
  /** Optional struck-through comparison price rendered above `primary`, e.g. `"$30"`. */
  secondary?: string
  /** Small suffix rendered after `secondary`. */
  secondarySuffix?: string
}

export interface TierCardProps {
  /**
   * Overrides the action button's disabled state. When omitted, the button
   * is disabled for the current plan (`isCurrent`).
   */
  actionDisabled?: boolean
  /**
   * Label for the action button rendered beneath the card. When `null` /
   * `undefined`, no action button is rendered.
   */
  actionLabel?: React.ReactNode
  /** Small annotation after the title, e.g. `"(current)"`. */
  badge?: React.ReactNode
  /** Feature list rendered under the price. */
  bullets: React.ReactNode[]
  className?: string
  /** Background image URL. */
  image: string
  /** Applies the "current plan" border hint when not `selected`. */
  isCurrent?: boolean
  /** Click handler for the action button rendered beneath the card. */
  onAction?: () => void
  onSelect?: () => void
  /** Color blended with `mix-blend-mode: color` over the image (used for the highest-tier red treatment). */
  overlay?: string
  price: TierCardPrice
  /** Applies selected chrome (arc-border shimmer, active distortion, plus-lighter text blend). */
  selected?: boolean
  /** Renders a radio selection indicator and exposes the card as `role="radio"`. */
  showSelector?: boolean
  /** Shader tint passed through to `ImageDistortion`. */
  tint?: string
  /** Active / inactive tint strength passed through to `ImageDistortion`. */
  tintStrength?: { active: number; inactive: number }
  /** Tier name / headline. */
  title: React.ReactNode
}
