# Two different decisions are being published under the same case reference

I hit this while building a scraper against the Decisions and Determinations database, and spent a
while assuming it was my bug before working out it isn't. Writing it up in case it's useful.

Observed 31 August 2026.

## Problem

A search result set can contain two rows with the same case reference, pointing at two completely
different decisions.

The clearest example is `PWD2437`. Search the Labour Court for June 2024 and you get 48 results, but
only 47 distinct references, because `PWD2437` appears twice:

- `/en/cases/2024/march/pwd2437.html` — listed 20/06/2024
- `/en/cases/2024/june/pwd2437.html` — listed 17/06/2024

Both pages open with `DECISION NO. PWD2437`. But one is appeal **PW/24/39**, and the other is appeal
**PW/24/12**. Different appellants, different adjudication decisions underneath
(`ADJ-00047991` vs `ADJ-00044826`), different outcomes. Two unrelated cases that happen to have been
issued the same determination number.

It isn't a one-off:

| Reference | Body | Search window | The two documents | Underlying cases |
|---|---|---|---|---|
| `PWD2437` | Labour Court | Jun 2024 | `/2024/march/…`, `/2024/june/…` | `PW/24/39` · `PW/24/12` |
| `RPD241` | Labour Court | Feb 2024 | `/2024/july/…`, `/2024/february/…` | `ADJ-00037979` · `ADJ-00038089` |
| `ADJ-00044064` | WRC | Feb 2024 | `/2024/february/…`, `/2024/january/…` | `CA-00054488-003` · `CA-00054488-001` |

I checked six months of Labour Court results, paging each window in full and comparing the number of
rows against the number of distinct references:

| Window | Rows | Distinct | |
|---|---|---|---|
| Jan 2024 | 45 | 45 | |
| Feb 2024 | 65 | 64 | `RPD241` |
| Mar 2024 | 18 | 18 | |
| Apr 2024 | 44 | 44 | |
| May 2024 | 41 | 41 | |
| Jun 2024 | 48 | 47 | `PWD2437` |

Two in 261 rows, roughly 0.8%, and it shows up in the WRC set too — 285 rows and 284 distinct
references for February 2024.

**Things I ruled out first**, because they were my more likely explanations:

- *Bad pagination on my end.* No — every window returns exactly as many rows as its own reported
  total. Nothing is dropped or repeated across page boundaries. The two `ADJ-00044064` rows are on
  pages 9 and 29, nowhere near each other.
- *The result count being wrong.* It isn't. It counts rows correctly. It just isn't a count of
  distinct references.
- *A redirect or an alias.* Both URLs return 200 with different bodies. Neither redirects.
- *The same decision published twice.* The documents differ in substance — different parties,
  different complaint references, different lengths.

## Why it's a problem

If you're reading the site by hand this barely registers — two similar entries, easy to miss one.

It's worse for anything automated, because the case reference is the only stable identifier the
database exposes. Anything that deduplicates on it drops one of the two decisions, and gets no error
while doing it: the record count simply comes out one lower than the result count, with nothing to
say why. Same for anything that names files after the reference, which is the obvious thing to do
given it's what the `Ref no:` field shows.

There's a citation problem too. "PWD2437" doesn't identify a decision. Someone following that
reference has a 50/50 chance of reading the wrong appeal.

## Suggested solution

**Stop the reuse at source.** Determination and decision numbers should be unique within a tribunal.
`PW/24/39` and `PW/24/12` shouldn't both have come out as `PWD2437`. This is the only fix that
actually solves it rather than working around it.

**If historical numbers can't be changed, expose something that is unique.** The document URL already
is. Putting a stable per-decision id in each result row would let anyone consuming the search
deduplicate correctly without touching a single existing reference. That's probably the cheapest
useful change.

**Fix the three above.** They can be renumbered, or annotated so a reader can tell which appeal
they're looking at.

**Add a check that would catch the next one.** Count rows against distinct references per month per
body. It's a one-line query and it's exactly how I found these — if it had been running, these three
would have been flagged when they were published rather than years later by someone writing a
scraper.

---

Everything above came from ordinary GET requests to the public search endpoint and the case pages it
links to, at low concurrency with an identifying User-Agent. Nothing authenticated, no unusual
request rate. Happy to share the exact URLs and the comparison script if it helps.

The address published for search problems is `webmaster@workplacerelations.ie`.
