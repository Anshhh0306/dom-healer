# Healed selectors in a real browser (Chromium + Playwright, JavaScript disabled)

238 healed targets; ground-truth marker resolvable in the browser for 238; 31 wrong predictions excluded below.

| Correctly healed targets | n | CSS finds exactly the true element | XPath finds exactly the true element |
|---|---:|---:|---:|
| all | 207 | 207 (100.0%) | 153 (73.9%) |
| in light DOM | 153 | 153 (100.0%) | 153 (100.0%) |
| inside shadow DOM | 54 | 54 (100.0%) | 0 (0.0%) |

Playwright's XPath engine does not pierce shadow roots, so XPath is only expected to work for light-DOM targets.
