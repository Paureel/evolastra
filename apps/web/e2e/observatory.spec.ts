import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const TEST_API_ORIGIN = "http://127.0.0.1:8011";

test.beforeEach(async ({ page, request }) => {
  await page.addInitScript((endpoint) => {
    window.sessionStorage.setItem("evolastra.api.endpoint", endpoint);
  }, TEST_API_ORIGIN);
  const response = await request.post(`${TEST_API_ORIGIN}/api/v1/demo/start?speed=50`, { data: {} });
  expect(response.ok()).toBeTruthy();
});

test("fresh production session stays offline until the visitor chooses to connect", async ({ page }) => {
  const companionRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith(TEST_API_ORIGIN)) companionRequests.push(request.url());
  });

  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("dialog", { name: "Enter Evolastra" })).toBeVisible();
  await expect(page.getByText(/Churn atlas/i)).toHaveCount(0);
  expect(companionRequests).toEqual([]);
});

test("live galaxy and system maps, synchronized views, search, and replay", async ({ page }) => {
  await page.goto("/?development-demo=1");
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", "/evolastra-mark.svg");
  await expect(page.getByRole("link", { name: "Evolastra on GitHub" })).toHaveAttribute("href", "https://github.com/Paureel/evolastra");
  await expect(page.getByRole("link", { name: "Aurel on X" })).toHaveAttribute("href", "https://x.com/aurel_pr");
  await expect(page.getByRole("heading", { name: /Churn atlas/i })).toBeVisible();
  await expect(page.getByText(/live.*0 lag/i)).toBeVisible();
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  const galaxyTimeline = page.getByRole("complementary", { name: "Galaxy timeline" });
  await expect(galaxyTimeline).toBeVisible();
  const galaxyReplay = galaxyTimeline.getByRole("slider", { name: "Replay sequence" });
  await expect.poll(async () => Number(await galaxyReplay.getAttribute("max"))).toBeGreaterThan(1);
  await galaxyReplay.focus();
  await page.keyboard.press("Home");
  await expect(galaxyTimeline.getByRole("button", { name: "Live", exact: true })).toBeEnabled();
  await galaxyTimeline.getByRole("button", { name: "Live", exact: true }).click();

  await page.getByRole("tab", { name: "System view" }).click();
  await expect(page.getByRole("img", { name: /Evolastra system view/i })).toBeVisible();
  await page.getByRole("tab", { name: "Galaxy map" }).click();
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();

  await page.getByRole("tab", { name: "Advanced" }).click();
  await expect(page.getByLabel("Advanced views")).toBeVisible();
  await page.getByRole("tab", { name: "Tech tree" }).click();
  await expect(page.getByLabel("Research tech tree")).toBeVisible();
  await page.getByRole("button", { name: /Researched Data ingress/i }).click();
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
  await page.goto("/?development-demo=1");
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("button", { name: "Contract friction completed" }).click();
  const inspector = page.getByRole("complementary", { name: "node inspector" });
  await expect(inspector.getByRole("heading", { name: "Contract friction" })).toBeVisible();
  await inspector.getByRole("button", { name: "Enter system view" }).click();
  await expect(page.getByRole("img", { name: /Contract friction, a pulsar/i })).toBeVisible();

  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("button", { name: "Robustness checks completed" }).click();
  await expect(inspector.getByRole("heading", { name: "Robustness checks" })).toBeVisible();
  await inspector.getByRole("button", { name: "Enter system view" }).click();
  await expect(page.getByRole("img", { name: /Robustness checks, a black hole/i })).toBeVisible();
});

test("map zoom is explicit and analysis artifacts open as safe figures", async ({ page }) => {
  await page.goto("/?development-demo=1");
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  const zoom = page.getByRole("slider", { name: "Map zoom level" });
  await expect(zoom).toBeVisible();
  await zoom.fill("175");
  await expect(page.locator(".map-zoom output")).toHaveText("175%");
  await page.getByRole("button", { name: "Zoom out" }).click();
  await expect(page.locator(".map-zoom output")).not.toHaveText("175%");

  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("tab", { name: "Figures" }).click();
  await expect(page.getByRole("region", { name: "Analysis figures" })).toBeVisible();
  const firstFigure = page.getByRole("button", { name: /^Open figure / }).first();
  await expect(firstFigure).toBeVisible();
  await firstFigure.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText(/preview|frequency/i).first()).toBeVisible();
  await dialog.getByRole("button", { name: "Close preview" }).click();
});

test("command star shipyard builds core and research-unlocked vessels", async ({ page }) => {
  await page.goto("/?development-demo=1");
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  await page.getByRole("tab", { name: "System view" }).click();
  const systemMap = page.getByRole("img", { name: /Evolastra system view/i });
  await expect(systemMap).toBeVisible();
  const box = await systemMap.boundingBox();
  expect(box).not.toBeNull();
  await systemMap.click({ position: { x: box!.width / 2, y: box!.height / 2 } });

  const shipyard = page.getByRole("dialog", { name: "Build a Codex vessel" });
  await expect(shipyard).toBeVisible();
  await expect(shipyard.getByRole("button", { name: /CORE HULL Frigate/ })).toBeVisible();
  await expect(shipyard.getByRole("button", { name: /CORE HULL Mothership/ })).toBeVisible();
  await expect(shipyard.getByRole("button", { name: /CORE HULL Colony ship/ })).toBeVisible();
  await shipyard.getByRole("button", { name: "Build Frigate" }).click();
  await expect(shipyard.getByRole("option", { name: /Frigate \d{2}/ }).last()).toBeAttached();
  await shipyard.getByRole("button", { name: "Close shipyard" }).click();

  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("tab", { name: "Figures" }).click();
  const firstFigure = page.getByRole("button", { name: /^Open figure / }).first();
  await expect(firstFigure).toBeVisible();
  await firstFigure.click();
  const figureResults = await new AxeBuilder({ page }).analyze();
  await page.getByRole("button", { name: "Close preview" }).click();
  await page.getByRole("tab", { name: "Tech tree" }).click();
  await expect(page.getByLabel("Research tech tree")).toBeVisible();
  const specialist = page.getByRole("button", { name: "Build specialist ship" }).first();
  await expect(specialist).toBeVisible();
  await specialist.click();
  await expect(shipyard).toBeVisible();
  await expect(shipyard.getByText("RESEARCH HULL").first()).toBeVisible();
});

test("single player opens an opt-in local-first multiplayer federation", async ({ page }) => {
  await page.goto("/?development-demo=1");
  await expect(page.getByRole("heading", { name: /Churn atlas/i })).toBeVisible();
  await page.getByRole("button", { name: "Open multiplayer federation" }).click();
  const federation = page.getByRole("dialog", { name: "Research federation" });
  await expect(federation).toBeVisible();
  await expect(federation.getByRole("tab", { name: "Host project" })).toBeVisible();
  await expect(federation.getByRole("tab", { name: "Join project" })).toBeVisible();
  await expect(federation.getByText("THIS DEVICE")).toBeVisible();
  await expect(federation.getByText(/Netlify/i)).toBeVisible();
  await federation.getByRole("button", { name: "Close multiplayer" }).click();
  await expect(federation).not.toBeVisible();
});

test("public three-empire showcase loads without pairing and remains read only", async ({ page }) => {
  await page.goto("/");
  const entry = page.getByRole("dialog", { name: "Enter Evolastra" });
  await expect(entry.getByRole("button", { name: "Explore public demo" })).toBeVisible();
  await expect(entry.getByText(/STAD: Stomach Adenocarcinoma/i)).toBeVisible();
  await expect(entry.getByText(/Copy Number Alteration \(CNA\) analysis/i)).toBeVisible();
  await expect(entry.getByText(/first-time setup installs a small local companion and Codex hooks/i)).toBeVisible();
  await expect(entry.getByRole("tabpanel", { name: "For humans" })).toContainText("bootstrap.ps1");
  await entry.getByRole("tab", { name: "For Codex agents" }).click();
  await expect(entry.getByRole("link", { name: "Agent setup file ↗" })).toHaveAttribute("href", "/agent-setup.md");
  await expect(entry.getByRole("link", { name: "llms.txt ↗" })).toHaveAttribute("href", "/llms.txt");
  await entry.getByRole("button", { name: "Explore public demo" }).click();

  await expect(page.getByRole("heading", { name: "STAD CNA · Three-Empire Expedition" })).toBeVisible();
  await expect(page.getByText("PUBLIC SHOWCASE · THREE EMPIRES")).toBeVisible();
  await expect(page.getByRole("button", { name: "Open multiplayer federation" })).toContainText("3 players");
  await expect(page.getByRole("img", { name: /13 claimed analysis systems, 3 territorial empires/i })).toBeVisible();

  await page.getByRole("button", { name: "Open multiplayer federation" }).click();
  const federation = page.getByRole("dialog", { name: "Three-empire expedition" });
  const roster = federation.getByRole("region", { name: "Researchers" });
  await expect(roster.getByText("Amplification Dominion", { exact: true })).toBeVisible();
  await expect(roster.getByText("Loss Cartographers", { exact: true })).toBeVisible();
  await expect(roster.getByText("Constellation Pact", { exact: true })).toBeVisible();
  await expect(federation.getByRole("button", { name: "Claim system" })).toHaveCount(0);
  await federation.getByRole("button", { name: "Close showcase details" }).click();

  await page.getByRole("tab", { name: "Advanced" }).click();
  await expect(page.getByText("PUBLIC SHOWCASE · READ ONLY")).toBeVisible();
  await page.getByRole("tab", { name: "Figures" }).click();
  await expect(page.getByRole("button", { name: /^Open figure / })).toHaveCount(6);
  await page.getByRole("tab", { name: "Tech tree" }).click();
  await expect(page.getByRole("button", { name: "Build specialist ship" })).toHaveCount(0);
  const replay = page.getByRole("slider", { name: "Replay phase" });
  await expect(replay).toHaveAttribute("max", "12");
  await replay.fill("7");
  await expect(page.getByText(/PHASE 7 \/ 12 · Loss Cartographers capital/i)).toBeVisible();
  await replay.fill("10");
  await expect(page.getByText(/PHASE 10 \/ 12 · Constellation Pact capital/i)).toBeVisible();
  await page.getByRole("tab", { name: "Galaxy map" }).click();
  await expect(page.getByRole("img", { name: /10 claimed analysis systems, 3 territorial empires/i })).toBeVisible();
});

test("@accessibility core surface has no serious axe violations", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/?development-demo=1");
  await expect(page.getByRole("img", { name: /Evolastra galaxy map/i })).toBeVisible();
  const defaultResults = await new AxeBuilder({ page }).analyze();
  await page.getByRole("tab", { name: "System view" }).click();
  const systemMap = page.getByRole("img", { name: /Evolastra system view/i });
  const systemBox = await systemMap.boundingBox();
  expect(systemBox).not.toBeNull();
  await systemMap.click({ position: { x: systemBox!.width / 2, y: systemBox!.height / 2 } });
  await expect(page.getByRole("dialog", { name: "Build a Codex vessel" })).toBeVisible();
  const shipyardResults = await new AxeBuilder({ page }).analyze();
  await page.getByRole("button", { name: "Close shipyard" }).click();
  await page.getByRole("button", { name: "Open multiplayer federation" }).click();
  await expect(page.getByRole("dialog", { name: "Research federation" })).toBeVisible();
  const federationResults = await new AxeBuilder({ page }).analyze();
  await page.getByRole("button", { name: "Close multiplayer" }).click();
  await page.getByRole("tab", { name: "Advanced" }).click();
  await page.getByRole("tab", { name: "Figures" }).click();
  await page.getByRole("button", { name: /^Open figure / }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const figureResults = await new AxeBuilder({ page }).analyze();
  await page.getByRole("button", { name: "Close preview" }).click();
  await page.getByRole("tab", { name: "Tech tree" }).click();
  await expect(page.getByLabel("Research tech tree")).toBeVisible();
  const techTreeResults = await new AxeBuilder({ page }).analyze();
  const serious = [...defaultResults.violations, ...shipyardResults.violations, ...federationResults.violations, ...figureResults.violations, ...techTreeResults.violations].filter((violation) => ["critical", "serious"].includes(violation.impact ?? ""));
  expect(serious, serious.map((item) => `${item.id}: ${item.help}`).join("\n")).toEqual([]);
});
