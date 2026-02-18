// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import { githubPages } from "@astrojs/github-pages";

export default defineConfig({
  site: "https://itssebastianfrey.com",

  adapter: githubPages(),

  vite: {
    plugins: [tailwindcss()],
  },
});
