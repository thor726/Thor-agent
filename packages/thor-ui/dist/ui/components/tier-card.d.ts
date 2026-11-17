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
export declare function TierCard({ actionDisabled, actionLabel, badge, bullets, className, image, isCurrent, onAction, onSelect, overlay, price, selected, showSelector, tint, tintStrength, title }: TierCardProps): import("react").JSX.Element;
export interface TierCardPrice {
    /** Headline price, e.g. `"$20"` or `"Free"`. */
    primary: string;
    /** Small suffix rendered after `primary`, e.g. `"/mo"` or `"first payment"`. */
    primarySuffix?: string;
    /** Optional struck-through comparison price rendered above `primary`, e.g. `"$30"`. */
    secondary?: string;
    /** Small suffix rendered after `secondary`. */
    secondarySuffix?: string;
}
export interface TierCardProps {
    /**
     * Overrides the action button's disabled state. When omitted, the button
     * is disabled for the current plan (`isCurrent`).
     */
    actionDisabled?: boolean;
    /**
     * Label for the action button rendered beneath the card. When `null` /
     * `undefined`, no action button is rendered.
     */
    actionLabel?: React.ReactNode;
    /** Small annotation after the title, e.g. `"(current)"`. */
    badge?: React.ReactNode;
    /** Feature list rendered under the price. */
    bullets: React.ReactNode[];
    className?: string;
    /** Background image URL. */
    image: string;
    /** Applies the "current plan" border hint when not `selected`. */
    isCurrent?: boolean;
    /** Click handler for the action button rendered beneath the card. */
    onAction?: () => void;
    onSelect?: () => void;
    /** Color blended with `mix-blend-mode: color` over the image (used for the highest-tier red treatment). */
    overlay?: string;
    price: TierCardPrice;
    /** Applies selected chrome (arc-border shimmer, active distortion, plus-lighter text blend). */
    selected?: boolean;
    /** Renders a radio selection indicator and exposes the card as `role="radio"`. */
    showSelector?: boolean;
    /** Shader tint passed through to `ImageDistortion`. */
    tint?: string;
    /** Active / inactive tint strength passed through to `ImageDistortion`. */
    tintStrength?: {
        active: number;
        inactive: number;
    };
    /** Tier name / headline. */
    title: React.ReactNode;
}
