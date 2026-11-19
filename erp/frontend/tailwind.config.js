/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: '#2563EB',
          secondary: '#7C3AED',
        },
        uccb: {
          green: '#0B7A3E',
          yellow: '#F7C600',
          red: '#C8102E',
          ink: '#141414',
          paper: '#F5F3EE',
        },
        canvas: 'hsl(var(--canvas))',
        background: 'hsl(var(--background))',
        input: 'hsl(var(--input))',
        success: 'hsl(var(--success) / <alpha-value>)',
        warning: 'hsl(var(--warning) / <alpha-value>)',
        info: 'hsl(var(--info) / <alpha-value>)',
        module: 'hsl(var(--module) / <alpha-value>)',
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar))',
          foreground: 'hsl(var(--sidebar-foreground))',
          muted: 'hsl(var(--sidebar-muted))',
        },
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive) / <alpha-value>)',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        ring: 'hsl(var(--ring))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
      },
      borderRadius: {
        xl: 'calc(var(--radius) + 4px)',
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      // Les composants de src/components/ui ont été générés par shadcn pour
      // Tailwind v4, qui comprend nativement des variantes comme
      // `data-open:` ou `data-horizontal:`. Le projet tourne sous Tailwind
      // v3, qui les ignorait silencieusement (onglets posés à côté de leur
      // contenu au lieu d'au-dessus, onglet actif non surligné, séparateurs
      // sans taille...). Ces alias les font correspondre aux attributs que
      // Radix pose réellement ; ils valent aussi pour `group-data-*`.
      data: {
        open: 'state="open"',
        closed: 'state="closed"',
        active: 'state="active"',
        disabled: 'disabled',
        horizontal: 'orientation="horizontal"',
        vertical: 'orientation="vertical"',
        inset: 'inset',
        placeholder: 'placeholder',
      },
      // Noms d'ombres propres à Tailwind v4, utilisés par les mêmes composants.
      boxShadow: {
        '2xs': '0 1px rgb(0 0 0 / 0.05)',
        xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        card: '0 1px 2px rgb(16 24 40 / 0.04), 0 1px 3px rgb(16 24 40 / 0.05)',
        'card-hover': '0 4px 12px -2px rgb(16 24 40 / 0.08), 0 2px 4px -2px rgb(16 24 40 / 0.05)',
        flottant: '0 12px 32px -8px rgb(16 24 40 / 0.18)',
      },
    },
  },
  plugins: [
    // `outline-hidden` (Tailwind v4) = l'ancien `outline-none` de v3.
    ({ addUtilities }) => {
      addUtilities({
        '.outline-hidden': { outline: '2px solid transparent', 'outline-offset': '2px' },
      });
    },
  ],
};
