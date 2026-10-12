# Billz Playwright E2E — CI/CD Implementation Plan

**Audience:** QA Lead / Eng Lead / DevOps  
**Owner:** Automation (CCL-Billz Playwright suite)  
**Status:** Proposal — ready to execute once org repo + secrets are available  
**Date:** 12 Oct 2026  

---

## 1. Executive summary

We will run Billz end-to-end automation from a **dedicated org GitHub repo** (separate from the Billz application codebase), using **GitHub Actions**.

**First goal:** a reliable **smoke** gate for all three verticals — **Retail (default)**, **Galaxy (mobile)**, and **Restaurant** — triggered manually, then nightly.

**Not in scope for v1:** running full E2E on every Billz product PR (that comes later, after smoke is stable).

---

## 2. Current state

| Item | Status |
|------|--------|
| Playwright Python suite (POM, `--tenant`, parallel + serial runner) | In place |
| Verticals: Retail, Galaxy, Restaurant | Covered in suite |
| Galaxy `@pytest.mark.smoke` (~40 tests: auth, masters, main menu, accounting, reports) | Ready |
| Retail tagged smoke suite | **Gap** — deep tests exist; no `-m smoke` pack |
| Restaurant tagged smoke suite | **Gap** — suite exists; no `-m smoke` pack |
| Stub workflow `.github/workflows/playwright-ci.yml` | Outdated (no tenant / `run_tests.py`) |
| Code on personal GitHub; moving to **org repo** | In progress with DevOps |
| App (Billz) repo vs automation repo | **Separate** by design |

**Architecture (already decided):**

- Shared page objects + `--tenant retail|galaxy|restaurant`
- Galaxy = shared suite + thin Galaxy-only layer (serial / IMEI / EMI)
- Restaurant = own vertical tree (different product surface)
- Runner: `python run_tests.py --tenant <name>` (parallel, then serial)

---

## 3. How repos and PRs relate (clarity for lead)

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  Billz app repo         │         │  Automation org repo           │
│  (product PRs)          │         │  (this Playwright suite)       │
│  Build / unit / deploy  │ ──CD──► │  E2E hits staging URLs         │
└─────────────────────────┘         └──────────────────────────────┘
```

| Event | What runs |
|-------|-----------|
| PR on **Billz app** | App CI only (unless we later add a trigger) |
| Deploy to **staging** | Optional later: notify automation to run smoke |
| PR / push on **automation repo** | Our Actions: smoke / scheduled full |
| Manual **Run workflow** | On-demand smoke or full per tenant |

**v1 recommendation:** CI lives on the **automation org repo** only. Link to Billz deploy/PR in a later phase.

---

## 4. Target outcomes (v1)

1. Org repo hosts the suite; Actions enabled.  
2. Secrets for Retail + Galaxy + Restaurant staging credentials (no secrets in git).  
3. One workflow:
   - **Manual** (`workflow_dispatch`): choose tenant + `smoke` or `full`
   - **Nightly** schedule: smoke all three tenants (or smoke + limited full)
4. HTML + JUnit reports uploaded as artifacts (14-day retention).  
5. Smoke is fast, stable, and suitable as a health check for staging.

---

## 5. Implementation phases

### Phase 0 — Repo & access (DevOps + Automation)  
**When:** Now  

- [ ] Org repo URL confirmed; write access for automation owner  
- [ ] Point local `origin` to org remote; push `main`  
- [ ] GitHub Actions enabled for the repo  
- [ ] Confirm runners: `ubuntu-latest` + Chromium is acceptable  

**Exit criteria:** Can push to org repo; Actions tab visible.

---

### Phase 1 — Secrets & environment (DevOps)  
**When:** Parallel with Phase 2  

GitHub Actions secrets (repo or org level):

| Secret | Purpose |
|--------|---------|
| `RETAIL_BASE_URL` | Retail staging web URL |
| `RETAIL_USER_EMAIL` / `RETAIL_USER_PASSWORD` | Retail test user |
| `GALAXY_BASE_URL` | Galaxy staging web URL |
| `GALAXY_USER_EMAIL` / `GALAXY_USER_PASSWORD` | Galaxy test user |
| `RESTAURANT_BASE_URL` | Restaurant staging web URL |
| `RESTAURANT_USER_EMAIL` / `RESTAURANT_USER_PASSWORD` | Restaurant test user |

Notes for DevOps:

- Users must have permissions for screens covered by smoke (not admin-only gaps).  
- Prefer dedicated automation users so human UAT doesn’t collide.  
- Staging should stay up during the smoke window (esp. nightly).

**Exit criteria:** Workflow can log into all three tenants without `.env` in the repo.

---

### Phase 2 — Smoke packs for Retail & Restaurant (Automation)  
**When:** Before claiming “smoke on all three”  

Mirror Galaxy’s pattern (page loads + login/dashboard):

| Tenant | Deliverable |
|--------|-------------|
| **Retail** | `tests/**` smoke markers / small smoke modules: auth, dashboard, key master + main menu + accounting page-loads |
| **Restaurant** | Vertical smoke: auth/dashboard + critical POS/main + accounting page-loads |
| **Galaxy** | Already has smoke — keep as reference; trim if any flaky for CI |

Smoke rules:

- Fast (target **&lt; 15–20 min per tenant** on CI)  
- No heavy data factories unless required  
- API-synced waits (no `networkidle` / fixed sleeps) on pages we touch  
- Marker: `@pytest.mark.smoke` so CI runs: `pytest --tenant X -m smoke`

**Exit criteria:** Locally green:

```text
pytest --tenant retail     -m smoke
pytest --tenant galaxy     -m smoke
pytest --tenant restaurant -m smoke
```

---

### Phase 3 — CI workflow v1 (Automation)  
**When:** After Phase 1 + 2  

Replace stub `.github/workflows/playwright-ci.yml` with:

1. **workflow_dispatch**  
   - Inputs: `tenant` = retail | galaxy | restaurant | all  
   - Inputs: `suite` = smoke | full  
2. **Nightly cron** (e.g. 2:00 AM IST) — smoke × all tenants  
3. Job steps: checkout → Python → `pip install -r requirements.txt` → `playwright install --with-deps chromium` → run suite → upload `reports/`  

Run commands (conceptually):

```text
# Smoke
pytest --tenant <tenant> -m smoke -n 2 --dist loadfile

# Full (manual / later nightly)
python run_tests.py --tenant <tenant> --workers 2
```

**Exit criteria:** One successful manual run per tenant (smoke) with downloadable HTML report.

---

### Phase 4 — Stabilise & report (Automation + Lead)  
**When:** First 1–2 weeks of nightly  

- Triage flakes; quarantine only with BUG id / xfail policy (existing pattern)  
- Agree fail notification (email / Teams / Slack) with DevOps  
- Dashboard: Actions history + artifact reports  

**Exit criteria:** Nightly smoke green ≥ 4 of 5 consecutive nights (or known env issues documented).

---

### Phase 5 — Optional later (out of v1)  

| Enhancement | When to consider |
|-------------|------------------|
| Trigger smoke after Billz **staging deploy** | Staging deploy is reliable |
| PR check on automation repo (smoke on PR) | Team commits via PRs to automation |
| Full suite nightly per tenant | Smoke is stable; staging capacity OK |
| Billz PR → smoke on preview env | Preview envs + DevOps bandwidth |

---

## 6. Proposed timeline (indicative)

| Week | Work |
|------|------|
| **Week 1** | Org remote + secrets; Retail + Restaurant smoke packs; rewrite workflow |
| **Week 2** | Manual smoke all three; fix failures; enable nightly |
| **Week 3** | Stabilise; report pack to lead; decide Phase 5 |

Exact dates depend on DevOps secrets and staging availability.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Staging down / shared data collisions | Dedicated automation users; smoke avoids tenant-wide totals where possible; serial marker for full runs |
| Flaky waits | Continue page quality (API waits); no headed/slowmo in CI |
| Full suite too long / expensive | v1 = smoke only on schedule; full = manual |
| Restaurant still evolving | Smoke = page-load + critical paths only; no expanding Restaurant deep coverage in v1 |
| Secrets leak | Org secrets only; never commit `.env` |

---

## 8. Asks from Lead / DevOps

1. Confirm **org repo URL** and push access.  
2. Provision **six secrets** (URL + user + password × 3 tenants) — or confirm existing secret names.  
3. Approve **nightly smoke** window (timezone + staging freeze policy).  
4. Confirm notification channel for failures.  
5. Agree v1 scope: **automation-repo CI only** (not every Billz product PR yet).

---

## 9. Success criteria (v1 done)

- [ ] Suite lives on org GitHub repo  
- [ ] Manual workflow: smoke for retail, galaxy, restaurant — all green  
- [ ] Nightly smoke scheduled  
- [ ] Reports available as Actions artifacts  
- [ ] Lead can open one failed run and see HTML report without local setup  

---

## 10. Recommendation

**Approve Phase 0–3 as v1.**  
Start CI with **smoke on all three verticals**, keep **full suite** as manual/`run_tests.py` until smoke is trusted. Keep Billz product PRs decoupled until DevOps is ready for post-deploy triggers.

---

*Prepared for internal alignment. Automation will implement Phase 2–3 once org repo URL and secrets are confirmed.*
