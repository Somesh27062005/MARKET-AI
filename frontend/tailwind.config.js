/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        theme: {
          primary: 'var(--theme-primary)',
          secondary: 'var(--theme-secondary)',
          accent: 'var(--theme-accent)',
        },
        surface: {
          900: 'rgb(var(--surface-900-rgb) / <alpha-value>)',
          800: 'rgb(var(--surface-800-rgb) / <alpha-value>)',
          700: 'rgb(var(--surface-700-rgb) / <alpha-value>)',
          600: 'rgb(var(--surface-600-rgb) / <alpha-value>)',
          500: 'rgb(var(--surface-500-rgb) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'float': 'float 8s ease-in-out infinite',
        'float-delayed': 'float 8s ease-in-out 3s infinite',
        'float-slow': 'float 10s ease-in-out 5s infinite',
        'spin-slow': 'spin 2s linear infinite',
        'shake': 'shake 0.4s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translate3d(0, 0, 0)' },
          '50%': { transform: 'translate3d(0, -20px, 0)' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-6px)' },
          '40%': { transform: 'translateX(6px)' },
          '60%': { transform: 'translateX(-4px)' },
          '80%': { transform: 'translateX(4px)' },
        },
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
