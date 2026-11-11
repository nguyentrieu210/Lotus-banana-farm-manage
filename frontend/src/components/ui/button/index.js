import {cva} from 'class-variance-authority'
export {default as Button} from './Button.vue'

// shadcn-vue new-york button variants for Tailwind v3, on the Lotus tokens (spec 004).
// Solid red is reserved for the one primary action. Destructive actions are tinted crimson with a border —
// a different hue, weight and shape from the primary — so "Xóa" never reads as "Lưu" (FR-007).
// `danger` is the solid crimson for the last confirmation inside a confirm dialog only.
export const buttonVariants=cva(
  'inline-flex min-w-0 max-w-full items-center justify-center gap-2 whitespace-normal break-words rounded-md text-sm font-medium ring-offset-background transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0',
  {variants:{
    variant:{
      default:'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:bg-primary/80',
      destructive:'border border-[color:var(--lotus-tone-danger-border)] bg-[color:var(--lotus-tone-danger-soft)] text-[color:var(--lotus-tone-danger-text)] hover:border-[color:var(--lotus-tone-danger-solid)] hover:bg-[color:var(--lotus-tone-danger-solid)] hover:text-[color:var(--lotus-tone-danger-on)]',
      danger:'bg-[color:var(--lotus-tone-danger-solid)] text-[color:var(--lotus-tone-danger-on)] shadow-sm hover:opacity-90',
      outline:'border border-[color:var(--lotus-border-control)] bg-background hover:bg-[color:var(--lotus-hover)] hover:text-foreground',
      secondary:'bg-secondary text-secondary-foreground hover:bg-[color:var(--lotus-active)]',
      soft:'bg-[color:var(--lotus-tone-primary-soft)] text-[color:var(--lotus-tone-primary-text)] hover:bg-[color:var(--lotus-primary-100)]',
      ghost:'hover:bg-[color:var(--lotus-hover)] hover:text-foreground',
      link:'text-primary underline-offset-4 hover:underline',
    },
    size:{
      default:'min-h-[var(--lotus-control-height)] h-auto px-4 py-1.5',
      sm:'min-h-[var(--lotus-control-sm)] h-auto rounded-md px-3 py-1 text-xs',
      lg:'min-h-[var(--lotus-control-lg)] h-auto px-6 py-2 text-[15px]',
      icon:'h-[var(--lotus-control-height)] w-[var(--lotus-control-height)]',
    },
  },
  defaultVariants:{variant:'default',size:'default'}}
)
