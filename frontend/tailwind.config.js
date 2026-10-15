/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slatebase: '#0b0f19',
        slatepanel: '#111726',
        slatesub: '#161e31',
        slateborder: '#1e2638',
        amberaccent: '#f59e0b',
        blueaccent: '#3b82f6',
      }
    },
  },
  plugins: [],
}
