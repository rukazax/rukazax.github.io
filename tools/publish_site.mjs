// Publish the static blog to GitHub Pages using the stored OAuth token.
import fs from "node:fs";
import path from "node:path";

const TOKEN = JSON.parse(fs.readFileSync("C:\\Users\\AMNovez\\.dsh\\secrets\\github.json", "utf8")).token;
const SITE = "C:\\Users\\AMNovez\\Documents\\deepseek-harness\\default-workspace\\blog\\site";
const OWNER = "rukazax";
const REPO = "rukazax.github.io";

const H = {
  authorization: `Bearer ${TOKEN}`,
  accept: "application/vnd.github+json",
  "user-agent": "dsh-blog-publisher",
  "x-github-api-version": "2022-11-28",
};

async function call(method, url, body) {
  const res = await fetch(url.startsWith("http") ? url : "https://api.github.com" + url, {
    method,
    headers: { ...H, ...(body ? { "content-type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch { json = { raw: text.slice(0, 300) }; }
  return { status: res.status, json };
}

// 1. repository
let repo = await call("GET", `/repos/${OWNER}/${REPO}`);
if (repo.status === 404) {
  const created = await call("POST", "/user/repos", {
    name: REPO,
    description: "Блог: заметки об инструментах, автоматизации и открытом коде",
    homepage: `https://${REPO}/`,
    private: false,
    has_issues: true,
    has_wiki: false,
    auto_init: false,
  });
  console.log(created.status < 300 ? "created repo " + REPO : "repo create failed " + JSON.stringify(created.json));
} else {
  console.log("repo exists:", repo.json.full_name, "branch:", repo.json.default_branch);
}

// 2. files
const files = [];
function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else files.push(p);
  }
}
walk(SITE);

for (const file of files) {
  const rel = path.relative(SITE, file).split(path.sep).join("/");
  const content = fs.readFileSync(file).toString("base64");
  const existing = await call("GET", `/repos/${OWNER}/${REPO}/contents/${encodeURI(rel)}`);
  const sha = existing.status === 200 ? existing.json.sha : undefined;
  const put = await call("PUT", `/repos/${OWNER}/${REPO}/contents/${encodeURI(rel)}`, {
    message: sha ? `update ${rel}` : `add ${rel}`,
    content,
    branch: "main",
    ...(sha ? { sha } : {}),
  });
  console.log((put.status < 300 ? "ok  " : "FAIL") + " " + rel + " (" + put.status + ")");
  if (put.status >= 300) console.log("     ", JSON.stringify(put.json).slice(0, 300));
}

// 3. GitHub Pages
let pages = await call("GET", `/repos/${OWNER}/${REPO}/pages`);
if (pages.status === 404) {
  const created = await call("POST", `/repos/${OWNER}/${REPO}/pages`, {
    source: { branch: "main", path: "/" },
    build_type: "legacy",
  });
  console.log(created.status < 300 ? "Pages enabled" : "Pages enable failed: " + JSON.stringify(created.json).slice(0, 300));
} else {
  console.log("Pages already configured:", JSON.stringify(pages.json).slice(0, 200));
}

// 4. wait for the build; GitHub Pages occasionally fails the first run, so retry once
for (let attempt = 1; attempt <= 3; attempt++) {
  let errored = false;
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 6000));
    const build = await call("GET", `/repos/${OWNER}/${REPO}/pages/builds/latest`);
    const status = build.json?.status;
    console.log(`build ${attempt}.${i + 1}: ${status || build.status}`);
    if (status === "built") break;
    if (status === "errored") {
      errored = true;
      console.log("build error:", JSON.stringify(build.json.error || build.json).slice(0, 200));
      break;
    }
  }
  if (!errored) break;
  if (attempt === 3) break;
  console.log("retrying build...");
  await call("POST", `/repos/${OWNER}/${REPO}/pages/builds`);
}

const site = await fetch(`https://${REPO}/`, { redirect: "follow" });
console.log("site:", site.status, site.headers.get("content-type"));
if (site.status === 200) {
  const html = await site.text();
  console.log("title:", (html.match(/<title>(.*?)<\/title>/) || ["", "?"])[1]);
}
