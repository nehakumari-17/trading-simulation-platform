/** @type {import('tailwindcss').Config} */
export default {
  // only process files that actually use tailwind classes
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      // custom colors to match a broker-style dark theme
      colors: {
        // main background shades
        bg: {
          primary:   '#0f0f0f',
          secondary: '#1a1a1a',
          card:      '#1e1e1e',
          hover:     '#252525',
        },
        // accent — green for buy/profit, red for sell/loss
        buy:  '#22c55e',
        sell: '#ef4444',
        // neutral text
        muted: '#6b7280',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
