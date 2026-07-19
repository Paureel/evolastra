# Plan: space-empire positioning and project links

_Make the product promise and creator channels unmistakable_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

The application exposes accessible GitHub and X links in its permanent command
header. The repository opens with Evolastra's distinctive promise: build and
expand a space empire while Codex agents perform real work.

## Scope

- Add persistent project/social links to the responsive app header.
- Reframe the README hero and product tour around the fleet-to-frontier loop.
- Update hosted-page metadata and the GitHub repository description.
- Add browser regression coverage and run the complete release gate.

## Steps

- [x] Implement and test the in-app transmission links.
- [x] Rework the README opening around the space-empire gameplay metaphor.
- [x] Update GitHub metadata and verify the complete release.

## Validation

`npm run verify` passes: 130 Python tests, 45 frontend tests, seven Playwright
browser/accessibility flows, strict type checks, the production build, harness,
source and asset scans, and both dependency audits. Desktop and compact-width
screenshots confirm that the project links remain visible without competing with
the active run controls.
