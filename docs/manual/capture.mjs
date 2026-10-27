// Takes the screenshots of the manual from a running ARIANE (dev API without authentication).
// Usage: node capture.mjs [baseUrl]   (default http://localhost:3000)
import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const base = process.argv[2] ?? "http://localhost:3000";
const shot = (page, name, opts = {}) => page.screenshot({ path: path.join(here, "img", `${name}.png`), ...opts });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 950 }, locale: "fr-FR" });
await page.goto(base);
await page.getByLabel("Plugin client").waitFor();
await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" }); // Next.js dev indicator
await shot(page, "01-accueil");

const inputs = page.locator('input[type="file"]');
await inputs.nth(0).setInputFiles(path.join(root, "DRW3500402-907_Init_Lower_1-6.pdf"));
await inputs.nth(1).setInputFiles(path.join(root, "PL_3500402-907_A.1.pdf"));
await shot(page, "02-import");
const imported = page.waitForResponse((r) => r.url().endsWith("/api/v1/imports") && r.request().method() === "POST", { timeout: 120000 });
await page.getByRole("button", { name: "Analyser" }).click();
const importId = (await (await imported).json()).id;
await page.getByRole("tab", { name: "Rapport" }).waitFor({ timeout: 120000 });
await page.getByText("erreurs").first().waitFor({ timeout: 120000 });
await page.waitForTimeout(1500);
await shot(page, "03-rapport");

for (const [label, name] of [["Faisceau", "04-faisceau"], ["Connecteurs", "05-connecteurs"], ["Câblage", "06-cablage"]]) {
  await page.getByRole("tab", { name: label }).click();
  await page.waitForTimeout(2500);
  await shot(page, name);
}

// An error from the report, opened in the connectors view
await page.getByRole("tab", { name: "Rapport" }).click();
await page.getByText("duplicate-destination").first().click();
await page.waitForTimeout(1500);
await shot(page, "08-erreur");

// Search a wire, then show it in the connectors view with the info panel
await page.getByRole("tab", { name: "Connecteurs" }).click();
await page.getByLabel("Recherche").fill("907-01+");
await page.waitForTimeout(1500);
await shot(page, "09-recherche");

await page.getByRole("button", { name: "Excel…" }).click();
await page.getByRole("dialog").waitFor();
await page.getByLabel("Sous-titre").fill("Harnais inférieur INIT");
await page.getByLabel("Classification du document").selectOption("internal");
await page.getByLabel("Export control").selectOption("Not Listed/Not Controlled");
await page.getByLabel("Rédaction").fill("A. Dupont");
await page.getByLabel("Vérification (Project Manager)").fill("B. Martin");
await page.getByLabel("Approbation qualité (Quality Manager)").fill("C. Durand");
await shot(page, "10-export");

// The workbook with the same settings, as a sample for the manual
const settings = { edition: "00", subtitle: "Harnais inférieur INIT", classification: "internal", export_control: "Not Listed/Not Controlled",
  quality_manager: "C. Durand", project_manager: "B. Martin", redactor: "A. Dupont" };
const res = await page.request.post(`${base}/api/v1/imports/${importId}/export.xlsx`, { data: settings });
await fs.writeFile(path.join(here, "exemple-export.xlsx"), await res.body());

// History after a reload
await page.reload();
await page.getByLabel("Plugin client").waitFor();
await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
await page.waitForTimeout(1500);
await shot(page, "11-historique", { clip: { x: 0, y: 46, width: 300, height: 500 } });
await browser.close();
