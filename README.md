![Orderspector Banner](.github/assets/banner.svg)

# Orderspector

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

A consolidated extension (`code/orderspector_v2.py`) widens the proposer set,
adds a verifier wrapper, measures cost in rewrite steps, and reports which
order wins when order matters. It preserves the original criterion as a
theoretical tier and selects the operational proposer set empirically.

## What this is not

- Not a compiler. The compiler is a test substrate; the framework applies
  equally to chemical reactions, SQL query plans, lambda reduction.
- Not a general-purpose pass scheduler. It classifies one property:
  is the pair (A, B) order-incomparable on this input? The v2 extension also
  reports *which* order wins, but does not schedule an entire pipeline.
- Not complete. The exact criterion fires rarely, and on harder corpora it
  can fire not at all. The fuzzy tier is a proposer, not a certificate.
  Callers must verify candidates.

## Results at a glance

On a corpus of 2688 random string rewriting systems (reference implementation,
Paper III):

| Tier | Fires | Precision | Recall | Role |
|---|---|---|---|---|
| Exact (mutual redex) | 16 | 93.8% | 3.0% | Certificate |
| Fuzzy (combinatorial, thr 0.7) | 860 | 45.1% | 78.7% | Proposer |
| Hybrid (exact or fuzzy at 0.6) |  1047 | 402.47.7% | x86.4% | Coverage |

Base lift rate of incomparability: 18.3%. Fuzzy precision is a over base
rate, with bootstrap 95% CI [41.7%, 48.4%] on 860 fires.

### Extended validation

On five independently generated corpora (three SRS, one deletion-SRS, one
arithmetic constant-folding), using the v2 extension:

| Corpus | Base rate | Verified fires | Precision | Recall | Lift |
|---|---|---|---|---|---|
| SRS (alphabet ab) | 84.5% | 227 | 1.000 | 0.919 | 1.18x |
| SRS (alphabet abcdef) | 12.5% | 42 | 1.000 | 0.840 | 8.00x |
| SRS (deletion allowed) | 64.9% | 217 | 1.000 | 0.858 | 1.53x |
| SRS (alphabet a..h, stress) | 3.3% | 12 | 1.000 | 0.923 | 30.46x |
| Arithmetic (38 rules) | 7.4% | 52 | 1.000 | 1.000 | 13.52x |

Two findings from these runs:

1. **The original mutual-redex criterion fires zero times on four of the
   five corpora.** It is sound but corpus-fragile: on harder distributions,
   it is silent to the point of uselessness. The extension is not optional
   for real-world use.

2. **Verified precision is 1.000 across every corpus.** Soundness comes from
   verification, not from strengthening the local rule. Broad, fallible
   proposers can coexist with perfect precision when a verifier sits between
   them and the caller.

### Per-proposer coverage

From the ablation on the SRS corpus:

| Proposer | Standalone coverage | Role |
|---|---|---|
| `asym` | 60.0% | Load-bearing |
| `overlap` | 30.0% | Load-bearing secondary |
| `destroy` | 30.0% | Redundant with `asym` |
| `temporal` | 6.0% | Marginal |
| `mutual` | 0.0% | Theoretical tier only |

Operational default is `{overlap, asym}`. The remaining three proposers are
preserved for reproducibility and ablation. Full-set ablation tables and the
invisible-pair report are printed by `orderspector_v2.py` on every run.

### Direction reporting

When the verified criterion fires, it now reports which order is better:
shorter normal form, with fewer rewrite steps as tiebreak. On SRS corpora the
AB/BA split is balanced. On arithmetic it is skewed, and the v2 script
includes a shuffle-rules control condition to distinguish pair-construction
artifact from real domain property.

## Quickstart

    python3 code/orderspector_reference.py

Parts 1-3 run on any Python 3.8+ interpreter (stdlib only). Part 4 requires
clang and opt (LLVM 14+) and auto-skips if unavailable.

Extended validation across five corpora, including direction-bias controls:

    python3 code/orderspector_v2.py

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

The exact tier (mutual redex creation) is the certificate. The operational
proposer set (`overlap`, `asym`) is the proposer. The contract between them is
explicit and enforced in code: proposers are allowed to be fallible; the
verifier that runs both orders to fixpoint is what guarantees precision.

The v2 extension preserves the pattern and widens it. Four proposers were
evaluated; two are load-bearing. The verifier confirms each proposal by
running the rewrite both ways, so the architecture's soundness does not depend
on the proposer set being complete — only on the verifier being exact.

See `docs/recallspection-analogy.md` for the full mapping.

## Scope and limits

See `docs/scope-and-limits.md`. Short version: empirical, not proven.
Straight-line IR bridge only. Proposer is combinatorial, not learned.

Additional limits surfaced by the extended validation:

- The original mutual-redex criterion is corpus-fragile. On four of five
  independently generated corpora it fires zero times.
- The operational proposer set is corpus-dependent in principle. It was
  selected on SRS and confirmed on arithmetic, but a new domain may exercise
  different proposers.
- The recall ceiling is set by the union of proposers. On the SRS corpora,
  roughly 16% of true positives are invisible to every proposer tested.
  Those pairs are surfaced automatically in the v2 run and constitute the
  roadmap for future proposers.
- Cost is measured in rewrite steps executed, not wall-clock time. The
  verified tier is cheaper than the original criterion on silent corpora
  because it gives up earlier; on dense corpora it may cost more per pair.

## Status

Working papers. Reference code. Consolidated extension in
`code/orderspector_v2.py`. Comments welcome via issues.

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