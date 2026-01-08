/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light mode
        'light-bg': '#ffffff',
        'light-surface': '#f9fafb',
        'light-border': '#e5e7eb',
        'light-text-primary': '#111827',
        'light-text-secondary': '#4b5563',
        // Dark mode
        'dark-bg': '#030712',
        'dark-surface': '#111827',
        'dark-border': '#1f2937',
        'dark-text-primary': '#f9fafb',
        'dark-text-secondary': '#9ca3af',
      },
    },
  },
  plugins: [],
}
