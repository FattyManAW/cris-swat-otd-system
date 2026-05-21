/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Text"', '"Segoe UI"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // OTD brand: teal-blue accent on dark surfaces
        'otd': {
          bg:    'var(--c-bg)',
          card:  'var(--c-card)',
          border:'var(--c-border)',
          text:  'var(--c-text)',
          muted: 'var(--c-muted)',
          accent:'var(--c-accent)',
          green: 'var(--c-green)',
          amber: 'var(--c-amber)',
          red:   'var(--c-red)',
          agent: 'var(--c-agent)',
        },
      },
    },
  },
  plugins: [],
}