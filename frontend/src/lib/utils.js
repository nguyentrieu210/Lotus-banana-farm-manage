import {clsx} from 'clsx'
import {twMerge} from 'tailwind-merge'

// Standard shadcn-vue class merge helper. CSS classes from consumers win.
export function cn(...inputs){return twMerge(clsx(inputs))}
