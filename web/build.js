// Injects Supabase credentials from Vercel env vars into index.html at build time.
// Both SUPABASE_URL and SUPABASE_ANON_KEY must be set in Vercel project settings.
const fs = require("fs");

const url = process.env.SUPABASE_URL || "";
const key = process.env.SUPABASE_ANON_KEY || "";

if (!url || !key) {
  console.warn(
    "WARNING: SUPABASE_URL or SUPABASE_ANON_KEY is not set. " +
    "The frontend will not be able to load articles."
  );
}

let html = fs.readFileSync("index.html", "utf8");

html = html
  .replace("window.__SUPABASE_URL__ || \"\"", JSON.stringify(url))
  .replace("window.__SUPABASE_ANON_KEY__ || \"\"", JSON.stringify(key));

fs.writeFileSync("index.html", html);
console.log("Build complete. Supabase credentials injected.");
