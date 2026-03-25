/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './frontend/index.html',
    './frontend/src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        powerhaus: {
          'primary': '#7c3aed',          // Violet-600
          'primary-content': '#ffffff',
          'secondary': '#db2777',         // Pink-600
          'secondary-content': '#ffffff',
          'accent': '#a855f7',            // Purple-500
          'accent-content': '#ffffff',
          'neutral': '#374151',           // Gray-700
          'neutral-content': '#f9fafb',
          'base-100': '#ffffff',          // White background
          'base-200': '#f3f4f6',          // Gray-100
          'base-300': '#e5e7eb',          // Gray-200
          'base-content': '#1f2937',      // Gray-800
          'info': '#8b5cf6',              // Violet-500
          'info-content': '#ffffff',
          'success': '#10b981',           // Emerald-500
          'success-content': '#ffffff',
          'warning': '#f59e0b',           // Amber-500
          'warning-content': '#ffffff',
          'error': '#ef4444',             // Red-500
          'error-content': '#ffffff',
        },
      },
    ],
    darkTheme: 'powerhaus',
  },
}
