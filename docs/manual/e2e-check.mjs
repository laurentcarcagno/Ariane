// Full path through the Docker stack: sign in, import the sample PDFs, correct a missing diameter, survive an expired token.
// Usage: node e2e-check.mjs   (env: ARIANE_URL, ARIANE_USER, ARIANE_PASSWORD)
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const url = process.env.ARIANE_URL ?? "https://localhost/";
const check = (ok, what) => { console.log(`${ok ? "OK  " : "FAIL"} ${what}`); if (!ok) process.exitCode = 1; };

const browser = await chromium.launch();
const page = await (await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1600, height: 950 } })).newPage();
const login = async () => {
  await page.waitForSelector("#username", { timeout: 20000 });
  await page.fill("#username", process.env.ARIANE_USER ?? "alice.bg");
  await page.fill("#password", process.env.ARIANE_PASSWORD ?? "dev-only-change-me");
  await page.click("#kc-login");
  await page.getByLabel("Plugin client").waitFor({ timeout: 20000 });
};
await page.goto(url);
await login();
check(true, "signed in");

const inputs = page.locator('input[type="file"]');
await inputs.nth(0).setInputFiles(path.join(root, "DRW3500402-907_Init_Lower_1-6.pdf"));
await inputs.nth(1).setInputFiles(path.join(root, "PL_3500402-907_A.1.pdf"));
await page.getByRole("button", { name: "Analyser" }).click();
await page.getByText("diameter-missing").first().waitFor({ timeout: 120000 });
check(true, "imported; report lists diameter-missing");

await page.getByText("diameter-missing").first().click();   // opens the segment in the harness view
await page.getByLabel("Diamètre").waitFor();
await page.getByLabel("Diamètre").fill("2.5");
await page.getByRole("button", { name: "Enregistrer" }).click();
await page.getByText(/saisi par/).waitFor({ timeout: 10000 });
await page.getByRole("tab", { name: "Rapport" }).click();
check(await page.getByText("diameter-missing").count() === 0, "diameter-missing gone after the edit");
await page.getByRole("button", { name: /^Info/ }).click();
check(await page.getByText("topology-edited").count() === 1, "edit reported as topology-edited (info)");

// expired token: the API answers 401 once, the app goes back through Keycloak (SSO session) and lands on the app again
let refused = 0;
await page.route(/\/api\/v1\/imports\/[0-9a-f-]{36}$/, async (route) => {
  if (!refused++) await route.fulfill({ status: 401, body: "{}" }); else await route.continue();
});
await page.locator("section", { hasText: "Analyses précédentes" }).locator("li button").first().click();
await page.waitForURL(/\/auth\/realms\/ariane|\/\?code=|\/$/, { timeout: 20000 });
await page.getByLabel("Plugin client").waitFor({ timeout: 20000 });
await page.waitForLoadState("networkidle");
check(refused === 1 && !(await page.locator("#username").count()), "401 -> silent sign-in again, no login form shown");
await browser.close();
