/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
      boxShadow: {
        'glass':    '0 4px 24px rgba(0,0,0,0.055), 0 1px 2px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.88)',
        'glass-lg': '0 8px 40px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.92)',
        'gradient': '0 4px 20px rgba(37,99,235,0.28)',
        'gradient-lg': '0 6px 28px rgba(37,99,235,0.35)',
      },
      backgroundImage: {
        'gradient-brand':   'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
        'gradient-emerald': 'linear-gradient(135deg, #059669 0%, #34d399 100%)',
        'gradient-amber':   'linear-gradient(135deg, #d97706 0%, #fbbf24 100%)',
        'gradient-rose':    'linear-gradient(135deg, #e11d48 0%, #fb7185 100%)',
      },
      backdropBlur: {
        xs: '4px',
      },
    },
  },
  plugins: [],
};
