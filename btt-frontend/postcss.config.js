export default {
  plugins: {
    // Tailwind v4 ships its PostCSS plugin as a separate package, and handles
    // vendor prefixing itself — autoprefixer is no longer needed here.
    '@tailwindcss/postcss': {},
  },
};
