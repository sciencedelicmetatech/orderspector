![Orderspector Banner](.github/assets/banner.svg)
 Orderspector

A reasoning layer over rewriting systems. Predicts when two rewrite relations
produce order-dependent results, using a certificate tier and a proposer tier
with an explicit contract.

Part of the [Sciencedelic Metatech](https://github.com/sciencedelicmetatech)
ecosystem, alongside
[recallspection](https://github.com/sciencedelicmetatech/recallspection).

---

## What this is

A formal framework and empirical validation for **order incomparability** in
rewriting systems. Three working papers (I, II, III) plus a reference
implementation that reproduces every number in them.

The central object is a **criterion**: two rewrite relations are
order-incomparable exactly when each creates redexes for the other. The
criterion is a *sufficient* condition with high precision. A second tier of
cheap combinatorial features recovers coverage.

## What this is not

- Not a compiler. The compiler is a test substrate; the framework applies
  equally to chemical reactions, SQL query plans, lambda reduction.
- Not a general-purpose pass scheduler. It classifies one property:
  is the pair (A, B) order-incomparable on this input?
- Not complete. The exact criterion fires rarely. The fuzzy tier is a
  proposer, not a certificate. Callers must verify candidates.

## Results at a glance

On a corpus of 2688 random string rewriting systems:

| Tier | Fires | Precision | Recall | Role |
|---|---|---|---|---|
| Exact (mutual redex) | 16 | 93.8% | 3.0% | Certificate |
| Fuzzy (combinatorial, thr 0.7) | 860 | 45.1% | 78.7% | Proposer |
| Hybrid (exact or fuzzy at 0.6) | 1047 | 40.7% | 86.4% | Coverage |

Base rate of incomparability: 18.3%. Fuzzy precision is a 2.47x lift over base
rate, with bootstrap 95% CI [41.7%, 48.4%] on 860 fires.

## Quickstart

    python3 code/orderspector_reference.py

Parts 1-3 run on any Python 3.8+ interpreter (stdlib only). Part 4 requires
clang and opt (LLVM 14+) and auto-skips if unavailable.

## The three papers

| Paper | Subject | Source |
|---|---|---|
| I | Observer-relative framework | `papers/paper-I-framework/paper.tex` |
| II | Criterion and scaling law | `papers/paper-II-criterion/paper.tex` |
| III | Empirical validation and dual-engine architecture | `papers/paper-III-validation/paper.tex` |

## The architecture pattern

Orderspector mirrors the Recallspection design:

    exact first, fuzzy proposes, caller verifies
    fuzzy is fail-open as a candidate list, fail-closed as an answer

The exact tier (mutual redex creation) is the certificate. The fuzzy tier
(four combinatorial features) is the proposer. The contract between them is
explicit and enforced in code.

See `docs/recallspection-analogy.md` for the full mapping.

## Scope and limits

See `docs/scope-and-limits.md`. Short version: empirical, not proven.
Straight-line IR bridge only. Proposer is combinatorial, not learned.

## Status

Working papers. Reference code. Comments welcome via issues.

## License

**Code:** GNU Affero General Public License v3.0 (AGPL-3.0). See `LICENSE`.

**Papers:** Creative Commons Attribution-ShareAlike 4.0 (CC-BY-SA-4.0).
See `papers/LICENSE`.

The AGPL applies to the reference implementation and to any derivative works,
including network services that expose modified versions of the code. The
papers are share-alike under CC-BY-SA-4.0, which mirrors the copyleft spirit
of the AGPL for written work.

For attribution purposes, cite the working paper(s) and the repository:

    Raell, E. (2026). Orderspector: A Reasoning Layer over Rewriting
    Systems. Working Papers I-III. Sciencedelic Metatech.
    https://github.com/sciencedelicmetatech/orderspector