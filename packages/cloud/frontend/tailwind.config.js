/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Dark theme colors matching desktop client
        dark: {
          bg: '#1a1a1a',
          surface: '#2d2d2d',
          border: '#404040',
        },
        primary: {
          DEFAULT: '#3b82f6',
          hover: '#2563eb',
        },
        accent: {
          DEFAULT: '#2B5B8A',
          hover: '#1e4a73',
        }
      },
    },
  },
  plugins: [],
}
