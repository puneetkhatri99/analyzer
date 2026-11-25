// Import boundaries only (not a style linter): `npm run lint`.
//   shared code (api, components, hooks, lib)  never imports a feature
//   a feature                                  never reaches into another feature, only its index.js
//   app / main                                 import features only through their index.js
const FEATURES = ["admin", "landing", "report"];

const rule = (patterns) => ({ "no-restricted-imports": ["error", { patterns }] });
const deepInto = (f) => ({
  group: [`@/features/${f}/**`],
  message: `Import @/features/${f} (its index.js), not a file inside it. Shared code belongs in src/lib, src/hooks or src/components.`,
});

export default [
  {
    files: ["src/**/*.{js,jsx,mjs}"],
    languageOptions: { ecmaVersion: "latest", sourceType: "module", parserOptions: { ecmaFeatures: { jsx: true } } },
  },
  {
    files: ["src/{api,components,hooks,lib}/**"],
    rules: rule([{ group: ["@/features/**", "**/features/**", "@/app/**"], message: "Shared code can't depend on a feature or the app shell." }]),
  },
  { files: ["src/app/**", "src/main.jsx"], rules: rule(FEATURES.map(deepInto)) },
  ...FEATURES.map((f) => ({
    files: [`src/features/${f}/**`],
    rules: rule([...FEATURES.filter((o) => o !== f).map(deepInto), { group: ["@/app/**"], message: "A feature can't import the app shell." }]),
  })),
];
