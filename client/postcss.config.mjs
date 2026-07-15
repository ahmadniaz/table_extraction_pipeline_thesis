/**
 * Next.js only accepts PostCSS plugins as string names (see postcss-shape).
 * `@csstools/postcss-oklab-function` runs after Tailwind and converts `oklch()` in emitted CSS to
 * `rgb()` so tools like html2canvas see only sRGB colors.
 */
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
    '@csstools/postcss-oklab-function': {
      preserve: false,
      subFeatures: { displayP3: false },
    },
  },
};

export default config;
