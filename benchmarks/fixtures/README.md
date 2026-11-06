# Adversarial DOM-mutation fixtures

40 suites = 4 categories × 10 suites. Each suite is a realistic page (`v1.html`)
paired with a heavily redesigned version of the same page (`v2.html`) plus a
`targets.json` that names the elements a test script would interact with or
assert on. The benchmark asks: *given only the v1 page and a selector that
worked on v1, can a method find the same logical element in v2?*

```
benchmarks/fixtures/
  ecommerce/ecommerce-01 … ecommerce-10/
  dashboard/dashboard-01 … dashboard-10/
  table/table-01 … table-10/
  form/form-01 … form-10/
     ├── v1.html        original page
     ├── v2.html        mutated redesign of the same page
     └── targets.json   targets + authored (brittle) selectors
```

Validate with `.venv/bin/python benchmarks/validate_fixtures.py --category <name>`.

## Ground truth

Mark each target element in **both** pages with `data-dh-target="tN"` (exactly
one element per id per page). The harness records the marked elements and then
**deletes every `data-dh-target` attribute** before any method sees the DOM, so
the marker can never leak into matching. Never put `data-dh-target` on
anything that is not a target, and never reference it in selectors.

The v2 target must be the element a human tester would unambiguously call "the
same element" (same function, same item/row/field), e.g. the *Add to cart*
button **of the same product**, the *Email* input of the same form, the
*Status* cell **of the same invoice row**.

## targets.json

```json
{
  "suite": "ecommerce-03",
  "category": "ecommerce",
  "title": "Shopping cart — kitchenware store",
  "mutations": ["class-obfuscation", "wrapper-divs", "sibling-reorder", "shadow-dom", "decoy", "copy-change"],
  "notes": "v2 migrates to CSS modules, moves the order summary into <order-summary> shadow root, ...",
  "targets": [
    {
      "id": "t1",
      "description": "Quantity input of the 'Cast-iron skillet 26cm' line item",
      "css": "table.cart-items tr:nth-child(2) input.qty",
      "xpath": "//table[@class='cart-items']//tr[2]//input[@name='qty']",
      "mutations": ["class-obfuscation", "sibling-reorder", "decoy"]
    }
  ]
}
```

* `css` and `xpath` are the selectors a QA engineer would plausibly have
  written against **v1**: class chains, `nth-child`, ids, attribute selectors,
  text XPath (`//button[normalize-space()='Checkout']`), positional XPath, etc.
  Mix styles. Each **must match exactly the target and nothing else in v1**
  (the validator enforces this).
* Selectors are evaluated on the *composed tree*: a declarative shadow root
  `<template shadowrootmode="open">` is flattened into its host, i.e. the
  shadow root's children become children of the host element (Playwright's
  shadow-piercing semantics). `my-card > .inner` matches a `.inner` that is a
  top-level child of `my-card`'s shadow root.
* `mutations` tags (controlled vocabulary): `class-obfuscation`,
  `wrapper-divs`, `sibling-reorder`, `shadow-dom`, `decoy`, `id-change`,
  `testid-change`, `copy-change`, `tag-change`, `attribute-churn`,
  `structure-move`, `insertion`. Per-target tags list what changed for that
  target; the suite-level list must contain at least `class-obfuscation`,
  `wrapper-divs`, `sibling-reorder`, `shadow-dom`, `decoy`.

## Page requirements

* Valid, realistic HTML5 documents (`<!doctype html>`, `<head>`, header/nav,
  main content, footer, …) with realistic copy, prices, names, dates. Inline
  `<style>`/`<script>` blocks are fine but optional. No external resources are
  needed.
* ≥ 120 elements per page (aim for 200–700); each file ≤ 200 KB.
* Avoid markup that HTML parsers restructure (block elements inside `<p>`,
  nested `<a>`, `<div>` directly inside `<table>`/`<tr>`); place shadow hosts
  around whole components, not between table rows.
* 5–6 targets per suite with variety: buttons, links, text inputs, selects,
  checkboxes/radios, icon-only buttons (no text, maybe `aria-label`), table
  cells, prices/labels/headings that tests assert on, nav items, tabs.
* Each suite in a category must be a genuinely different page (different
  site, domain, layout and component structure), not one template with new data.

## Required v2 mutations (heavy, but a plausible redesign)

1. **Class obfuscation** — rename most class names: CSS-modules hashes
   (`Card_title__x7Gq2`), styled-components (`sc-gKclnd kQwYzP`), emotion
   (`css-1x9f2ab`), or swap semantic classes for Tailwind utilities
   (`btn btn-primary` → `inline-flex items-center rounded-md bg-indigo-600 px-3 py-2`).
   Target v1/v2 class-vocabulary overlap ≤ 0.35.
2. **Wrapper divs** — insert 1–3 extra wrapper `div`/`span`/custom elements
   around targets or their containers.
3. **Sibling reordering** — reorder repeated items (cards, rows, nav links,
   form fields, columns) that contain or neighbour targets.
4. **Shadow DOM shift** — every v2 has ≥ 1 declarative shadow root
   (`<x-widget><template shadowrootmode="open">…</template></x-widget>`); move
   components into, out of, or between shadow roots. In ≥ 3 suites per
   category at least one target must live inside a shadow root in v2.
5. **Decoys** — near-duplicates of targets: the same button in another
   card/row, a hidden duplicate (`hidden`, `style="display:none"`,
   `aria-hidden="true"`), a mobile-menu copy of the nav, a "recommended
   products" carousel repeating the product, a modal with a second *Submit*,
   a sticky header repeating the CTA. ≥ 2 targets per suite should have a
   same-tag, same-text decoy in v2.
6. **Attribute churn** — change or regenerate ids (`:r1f:`, `input-7f3a`), rename
   or drop `data-testid`/`data-test`/`data-qa` on at least half of the targets
   that had one, reword copy on ≥ 25 % of targets ("Add to cart" → "Add to bag",
   "Sign in" → "Log in"), change tags (`a.btn` → `button`, `table` →
   `div[role=grid]`), insert new content (banners, new columns, new fields).

Most authored selectors should break (no match or a wrong match) in v2, as
they do after real redesigns. But do **not** make v2 unrecognisable: keep the
signals a human uses — what the element says or is labelled, what it is
next to, which item/row/section it belongs to — at least partially intact.
