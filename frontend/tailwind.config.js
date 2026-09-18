/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary — sampled from logo.png icon green (#1BCA9A)
        primary: {
          50: '#ecfdf6',
          100: '#d4faeb',
          200: '#aef2dc',
          300: '#7ce7c7',
          400: '#42d6ae',
          500: '#1bca9a',
          600: '#0c9a77',
          700: '#0a7c61',
          800: '#0a634f',
          900: '#095141',
          950: '#04302a',
        },
        // Medical blue — sampled from logo.png icon blue side (#0778BD)
        medical: {
          50: '#f0f9fe',
          100: '#ddf1fa',
          200: '#b6e3f4',
          300: '#82d0ea',
          400: '#45b6da',
          500: '#0778bd',
          600: '#0668a3',
          700: '#085685',
          800: '#0b4970',
          900: '#0e3e5e',
        },
        // Wordmark navy — sampled from logo.png "MedPak" text
        navy: {
          DEFAULT: '#001633',
          700: '#0a2e5a',
        },
        brand: {
          light: '#f8fafc',
          DEFAULT: '#0f172a',
          dark: '#020617',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
