// End-to-end check of the browser sign-in (Keycloak, code flow + PKCE) against the Docker stack.
// Usage: node login-check.mjs [outDir]   (env: ARIANE_URL, ARIANE_USER, ARIANE_PASSWORD, ARIANE_NEW_PASSWORD)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const url = process.env.ARIANE_URL ?? "https://localhost/";
const user = process.env.ARIANE_USER ?? "alice.bg";
const password = process.env.ARIANE_PASSWORD ?? "dev-only-change-me";
const newPassword = process.env.ARIANE_NEW_PASSWORD ?? password;
const out = process.argv[2] ?? "img";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await (await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1400, height: 900 } })).newPage();
const log = [];
page.on("console", (m) => m.type() === "error" && log.push(`console: ${m.text()}`));
page.on("response", (r) => r.status() >= 400 && log.push(`${r.status()} ${r.url()}`));

await page.goto(url);
await page.waitForSelector("#username", { timeout: 20000 });
await page.screenshot({ path: `${out}/login-01-keycloak.png` });
await page.fill("#username", user);
await page.fill("#password", password);
await page.click("#kc-login");
await page.waitForLoadState("networkidle");
if (await page.locator("#password-new").count()) {  // temporary password: Keycloak asks for a new one
  await page.screenshot({ path: `${out}/login-02-new-password.png` });
  await page.fill("#password-new", newPassword);
  await page.fill("#password-confirm", newPassword);
  await page.click('input[type=submit], button[type=submit]');
  await page.waitForLoadState("networkidle");
}
for (const f of ["#firstName", "#lastName", "#email"]) if (await page.locator(f).count() && !(await page.inputValue(f))) await page.fill(f, "x");
await page.waitForSelector("text=Plans de faisceau", { timeout: 20000 });
await page.screenshot({ path: `${out}/login-03-app.png` });
console.log("signed in as:", await page.locator("header").innerText());
console.log("api calls rejected:", log.length ? log : "none");

await page.getByRole("button", { name: "Déconnexion" }).click();
await page.waitForSelector("#username", { timeout: 20000 });
console.log("sign-out OK: back on the login page");
await browser.close();
