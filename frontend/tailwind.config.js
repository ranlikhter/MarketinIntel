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
          50:  '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        dark: {
          base:     '#08080e',
          surface:  '#0e0e1a',
          elevated: '#141427',
          border:   'rgba(255,255,255,0.07)',
        },
      },
      boxShadow: {
        'glass':    '0 4px 24px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)',
        'glass-lg': '0 8px 40px rgba(0,0,0,0.4), 0 2px 8px rgba(0,0,0,0.3)',
        'gradient': '0 4px 20px rgba(245,158,11,0.25)',
        'gradient-lg': '0 6px 28px rgba(245,158,11,0.35)',
      },
      backgroundImage: {
        'gradient-brand':   'linear-gradient(135deg, #f59e0b 0%, #f97316 100%)',
        'gradient-emerald': 'linear-gradient(135deg, #047857 0%, #059669 100%)',
        'gradient-amber':   'linear-gradient(135deg, #b45309 0%, #d97706 100%)',
        'gradient-rose':    'linear-gradient(135deg, #be123c 0%, #e11d48 100%)',
        'gradient-blue':    'linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)',
      },
      backdropBlur: {
        xs: '4px',
      },
    },
  },
  plugins: [],
};
