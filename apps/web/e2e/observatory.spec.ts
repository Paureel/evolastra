import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  const response = await request.post("http://127.0.0.1:8000/api/v1/demo/start?speed=50", { data: {} });
  expect(response.ok()).toBeTruthy();
});

test("live galaxy and system maps, synchronized views, search, and replay", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", "/evolastra-mark.svg");
  await expect(page.getByRole("heading", { name: /Churn atlas/i })).toBeVisible();
  await expect(page.getByText(/live.*0 lag/i)).toBeVisible();
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();

  await page.getByRole("tab", { name: "System view" }).click();
  await expect(page.getByRole("img", { name: /Evolastra system view/i })).toBeVisible();
  await page.getByRole("tab", { name: "Galaxy map" }).click();
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();

  await page.getByRole("tab", { name: "Advanced" }).click();
  await expect(page.getByLabel("Advanced views")).toBeVisible();
  await page.getByRole("tab", { name: "Tech tree" }).click();
  await expect(page.getByLabel("Research tech tree")).toBeVisible();
  await page.getByRole("treeitem", { name: /Researched Data ingress/i }).click();
  await expect(page.getByRole("complementary", { name: "node inspector" }).getByRole("heading", { name: "Data ingress" })).toBeVisible();
  await page.getByRole("tab", { name: "Findings" }).click();
  await expect(page.getByRole("heading", { name: "Findings and contradictions" })).toBeVisible();

  await page.getByRole("button", { name: /^Search/i }).click();
  await page.getByRole("textbox", { name: "Search query" }).fill("tenure");
  await expect(page.getByRole("dialog", { name: "Search and command palette" }).getByRole("button").first()).toBeVisible();
  await page.keyboard.press("Escape");

  const replay = page.getByRole("slider", { name: "Replay sequence" });
  await expect.poll(async () => Number(await replay.getAttribute("max"))).toBeGreaterThan(1);
  await expect.poll(async () => Number(await replay.inputValue())).toBeGreaterThan(1);
  await replay.focus();
  await page.keyboard.press("Home");
  await expect(page.getByRole("button", { name: "Live", exact: true })).toBeEnabled();
  await page.getByRole("combobox", { name: "Replay speed" }).selectOption("12");
  await page.getByRole("button", { name: "Play replay" }).click();
  await expect.poll(async () => Number(await replay.inputValue())).toBeGreaterThan(1);
  await page.getByRole("button", { name: "Pause replay" }).click();
  await page.getByRole("button", { name: "Live", exact: true }).click();
  await expect(replay).toHaveValue(await replay.getAttribute("max") ?? "1");
});

test("stellar identity persists from galaxy systems into system view", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("button", { name: "Contract friction completed" }).click();
  await page.getByRole("tab", { name: "System view" }).click();
  await expect(page.getByRole("img", { name: /Contract friction, a pulsar/i })).toBeVisible();

  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("button", { name: "Robustness checks completed" }).click();
  await page.getByRole("tab", { name: "System view" }).click();
  await expect(page.getByRole("img", { name: /Robustness checks, a black hole/i })).toBeVisible();
});

test("@accessibility core surface has no serious axe violations", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  const defaultResults = await new AxeBuilder({ page }).analyze();
  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("tab", { name: "Tech tree" }).click();
  await expect(page.getByLabel("Research tech tree")).toBeVisible();
  const techTreeResults = await new AxeBuilder({ page }).analyze();
  const serious = [...defaultResults.violations, ...techTreeResults.violations].filter((violation) => ["critical", "serious"].includes(violation.impact ?? ""));
  expect(serious, serious.map((item) => `${item.id}: ${item.help}`).join("\n")).toEqual([]);
});
