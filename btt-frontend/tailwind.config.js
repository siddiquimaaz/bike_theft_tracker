/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // dark navy palette — command-centre aesthetic
        btt: {
          950: '#03060f',
          900: '#06091a',
          800: '#0c1225',
          700: '#111a35',
          600: '#1a274a',
          500: '#263560',
        },
        // semantic overrides so we can write bg-primary, text-muted, etc.
        primary:  { DEFAULT: '#f59e0b', hover: '#fbbf24', dim: 'rgba(245,158,11,.12)' },
        muted:    '#8b96b0',
        faint:    '#454e66',
      },
      fontFamily: {
        heading: ['"Exo 2"', 'sans-serif'],
        sans:    ['"DM Sans"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: { btt: '8px', 'btt-lg': '12px' },
      boxShadow:    { btt: '0 0 0 1px rgba(255,255,255,.06)' },
    },
  },
  plugins: [],
};
