import { expect, test, type Page } from "@playwright/test";


const API = "http://127.0.0.1:18080";
const auth = (token: string) => ({ Authorization: `Bearer ${token}` });


async function login(page: Page, token: string) {
  await page.getByPlaceholder("operator token").fill(token);
  await page.getByRole("button", { name: "Sign in" }).click();
}


async function switchRole(page: Page, token: string) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, token);
}


async function createAndSubmit(
  page: Page,
  purpose: string,
  amountMinor: number,
) {
  await page.getByRole("button", { name: "Purchase Requests" }).click();
  await page.getByPlaceholder("amount in minor units").fill(String(amountMinor));
  await page.getByPlaceholder("purpose").fill(purpose);
  await page.getByPlaceholder("supporting reference").fill(`quote-${purpose}`);
  await page.getByRole("button", { name: "Create draft" }).click();
  const row = page.getByRole("row").filter({ hasText: purpose });
  await expect(row).toContainText("draft");
  page.once("dialog", (dialog) => dialog.accept());
  await row.getByRole("button", { name: "Submit" }).click();
  await expect(row).toContainText("submitted");
}


async function decide(page: Page, purpose: string, decision: "Approve" | "Reject") {
  await page.getByRole("button", { name: "Approvals" }).click();
  const row = page.getByRole("row").filter({ hasText: purpose });
  await expect(row).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await row.getByRole("button", { name: decision, exact: true }).click();
  await expect(row).not.toBeVisible();
}


async function applyCommitment(page: Page, purpose: string) {
  await page.getByRole("button", { name: "Purchase Requests" }).click();
  const row = page.getByRole("row").filter({ hasText: purpose });
  await expect(row).toContainText("approved");
  page.once("dialog", (dialog) => dialog.accept());
  await row.getByRole("button", { name: "Apply commitment" }).click();
  return row;
}


test("four-view Budget Control acceptance", async ({ page, request }) => {
  const unauthenticated = await request.get(`${API}/budget/budgets`);
  expect(unauthenticated.status()).toBe(401);

  const bootstrap = await request.post(`${API}/budget/bootstrap`, {
    headers: auth("admin-token"),
    data: {
      organization_name: "Browser Acceptance Org",
      budget_name: "Operations",
      owner_type: "department",
      owner_name: "Operations",
      period_start: "2026-01-01",
      period_end: "2026-12-31",
      currency: "USD",
      allocation_minor: 2000,
      owner_principal: "owner",
      requester_principal: "requester",
      idempotency_key: "browser-bootstrap-v1",
    },
  });
  expect(bootstrap.ok()).toBeTruthy();

  await page.goto("/");
  await page.getByRole("button", { name: "Budget Control" }).click();
  await expect(page.getByText("Enter your operator token")).toBeVisible();
  await login(page, "requester-token");

  // Happy path: 2,000 minor units - 1,500 committed = 500 ($5.00).
  await createAndSubmit(page, "Acceptance equipment", 1500);
  await switchRole(page, "owner-token");
  await decide(page, "Acceptance equipment", "Approve");
  const happyRow = await applyCommitment(page, "Acceptance equipment");
  await expect(page.getByText(/verified_success · execution/)).toBeVisible();
  await expect(happyRow).toContainText("committed");
  await page.getByRole("button", { name: "Budgets", exact: true }).click();
  await expect(page.getByText("$5.00", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Spending History" }).click();
  await expect(page.getByRole("cell", { name: "commitment" })).toBeVisible();

  // Rejected path remains explicit and creates no financial effect.
  await switchRole(page, "requester-token");
  await createAndSubmit(page, "Rejected equipment", 100);
  await switchRole(page, "owner-token");
  await decide(page, "Rejected equipment", "Reject");
  await page.getByRole("button", { name: "Purchase Requests" }).click();
  await expect(page.getByRole("row").filter({ hasText: "Rejected equipment" }))
    .toContainText("rejected");

  // Two approvals against the same 500 evidence: one succeeds, one is stale.
  await switchRole(page, "requester-token");
  await createAndSubmit(page, "Concurrent A", 400);
  await createAndSubmit(page, "Concurrent B", 400);
  await switchRole(page, "owner-token");
  await decide(page, "Concurrent A", "Approve");
  await decide(page, "Concurrent B", "Approve");
  await applyCommitment(page, "Concurrent A");
  await expect(page.getByText(/verified_success · execution/)).toBeVisible();
  await applyCommitment(page, "Concurrent B");
  await expect(page.getByText(/blocked_before_execution · execution none/)).toBeVisible();

  // Role denial is visible: an authenticated principal without a Budget role
  // sees no budgets or mutation controls.
  await switchRole(page, "stranger-token");
  await page.getByRole("button", { name: "Budgets", exact: true }).click();
  await expect(page.getByText("No budgets are visible for this principal.")).toBeVisible();
  await page.getByRole("button", { name: "Purchase Requests" }).click();
  await expect(page.getByRole("button", { name: "Create draft" })).toBeDisabled();

  // Unresolved rendering is exercised at the HTTP boundary; the real backend
  // is left unchanged while the browser receives an ambiguous mutation result.
  await switchRole(page, "requester-token");
  await createAndSubmit(page, "Unresolved equipment", 50);
  await switchRole(page, "owner-token");
  await decide(page, "Unresolved equipment", "Approve");
  await page.route("**/budget/requests/*/commit", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        financial_status: "outcome_unknown",
        execution_id: "ambiguous-browser-test",
      }),
    });
  });
  await applyCommitment(page, "Unresolved equipment");
  await expect(
    page.getByText("outcome_unknown · execution ambiguous-browser-test")
  ).toBeVisible();
});
