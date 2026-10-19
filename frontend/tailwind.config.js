import preset from 'frappe-ui/tailwind'
import animate from 'tailwindcss-animate'

// Keep the ERPNext/Frappe UI preset and add shadcn-vue (Tailwind v3) tokens.
export default {
  presets:[preset],
  // App toggles .dark on <html> (src/workspace.js); the frappe-ui preset defaults to [data-theme=dark].
  darkMode:['selector','.dark'],
  content:['./index.html','./src/**/*.{vue,js,ts}'],
  theme:{
    extend:{
      borderRadius:{lg:'var(--radius)',md:'calc(var(--radius) - 2px)',sm:'calc(var(--radius) - 4px)'},
      colors:{
        border:'hsl(var(--border))',
        input:'hsl(var(--input))',
        ring:'hsl(var(--ring))',
        background:'hsl(var(--background))',
        foreground:'hsl(var(--foreground))',
        primary:{DEFAULT:'hsl(var(--primary))',foreground:'hsl(var(--primary-foreground))'},
        secondary:{DEFAULT:'hsl(var(--secondary))',foreground:'hsl(var(--secondary-foreground))'},
        destructive:{DEFAULT:'hsl(var(--destructive))',foreground:'hsl(var(--destructive-foreground))'},
        muted:{DEFAULT:'hsl(var(--muted))',foreground:'hsl(var(--muted-foreground))'},
        accent:{DEFAULT:'hsl(var(--accent))',foreground:'hsl(var(--accent-foreground))'},
        popover:{DEFAULT:'hsl(var(--popover))',foreground:'hsl(var(--popover-foreground))'},
        card:{DEFAULT:'hsl(var(--card))',foreground:'hsl(var(--card-foreground))'},
      },
    },
  },
  plugins:[animate],
}
