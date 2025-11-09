/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      fontWeight: {
        '650': '650',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 300ms ease-out',
      },
      colors: {
        cream: {
          50: '#fefdfb',
          100: '#fef9f1',
          200: '#fdf2e3',
          300: '#fbebd5',
          400: '#f7ddc7',
          500: '#f3cfb9',
          600: '#e5b8a3',
          700: '#d4a28d',
          800: '#c08d77',
          900: '#a97961',
        },
        tan: {
          50: '#faf8f5',
          100: '#f4f0e8',
          200: '#e8dfd1',
          300: '#dbceba',
          400: '#cfbda3',
          500: '#c2ac8c',
          600: '#a69470',
          700: '#8a7c54',
          800: '#6e6338',
          900: '#524b1c',
        },
        maroon: {
          50: '#fdf2f2',
          100: '#fce4e4',
          200: '#f7cccc',
          300: '#f1a8a8',
          400: '#e87a7a',
          500: '#b91c1c',
          600: '#991b1b',
          700: '#7f1d1d',
          800: '#651a1a',
          900: '#450a0a',
        },
        brown: {
          50: '#fdf8f6',
          100: '#f2e8e5',
          200: '#eaddd7',
          300: '#e0cec7',
          400: '#d2bab0',
          500: '#bfa094',
          600: '#a18072',
          700: '#8b6f47',
          800: '#6b5b47',
          900: '#3c2414',
        },
      },
    },
  },
  plugins: [],
};