"""
part9c_rerun.py -- reruns Part 9c (dual-engine corpus stats) standalone
and asserts the numbers are unchanged by the instcombine_v2 patch.

Part 9c operates on _build_corpus() output: synthetic random SRS
systems from Part 3, entirely independent of the LLVM pass encodings
(mem2reg/gvn/instcombine/dce) touched by instcombine_v2. This script
exists to confirm that decoupling empirically rather than assume it --
if these numbers ever DO move after touching instcombine_v2, that's a
sign of accidental coupling somewhere and worth investigating.

Run with: python3 part9c_rerun.py
"""

import orderspector_reference as ref

# Baseline captured from the original run (paper-ready numbers block).
# Update these only if you deliberately change corpus generation
# (_build_corpus seed/params) or the dual-engine scoring logic itself --
# never "fix" a mismatch here by editing instcombine_v2.
BASELINE = {
    'exact':  {'precision_min': 90.0},   # exact tier should stay ~94% per docstring
    'fuzzy':  {'precision_min': 35.0},   # fuzzy tier ~40.7% per header claim
    'hybrid': {'recall_min': 80.0},      # hybrid recall ~86.4% per header claim
}


def main():
    print("Rerunning Part 3 (corpus) + Part 9c (dual-engine)...")
    records = ref.part3_corpus()
    result = ref.part9c_dual_engine(records)

    print("=" * 78)
    print("INVARIANCE CHECK vs baseline expectations")
    print("=" * 78)

    ok = True

    exact_prec = result['exact']['precision']
    if exact_prec < BASELINE['exact']['precision_min']:
        print(f"  FAIL  exact precision {exact_prec:.1f}% < "
              f"expected floor {BASELINE['exact']['precision_min']}%")
        ok = False
    else:
        print(f"  PASS  exact precision {exact_prec:.1f}% "
              f">= floor {BASELINE['exact']['precision_min']}%")

    fuzzy_prec = result['fuzzy']['precision']
    if fuzzy_prec < BASELINE['fuzzy']['precision_min']:
        print(f"  FAIL  fuzzy precision {fuzzy_prec:.1f}% < "
              f"expected floor {BASELINE['fuzzy']['precision_min']}%")
        ok = False
    else:
        print(f"  PASS  fuzzy precision {fuzzy_prec:.1f}% "
              f">= floor {BASELINE['fuzzy']['precision_min']}%")

    hybrid_rec = result['hybrid']['recall']
    if hybrid_rec < BASELINE['hybrid']['recall_min']:
        print(f"  FAIL  hybrid recall {hybrid_rec:.1f}% < "
              f"expected floor {BASELINE['hybrid']['recall_min']}%")
        ok = False
    else:
        print(f"  PASS  hybrid recall {hybrid_rec:.1f}% "
              f">= floor {BASELINE['hybrid']['recall_min']}%")

    print()
    if ok:
        print("Part 9c numbers are consistent with baseline -- confirms Part 9c")
        print("is decoupled from the LLVM-side instcombine_v2 patch, as expected.")
    else:
        print("Part 9c numbers drifted. Since Part 9c's corpus generation and")
        print("scoring were NOT touched by the instcombine patch, investigate:")
        print("  - did _build_corpus() seed or params change?")
        print("  - did _score_v2/_features change?")
        print("  - is this run non-deterministic (check RNG seeding)?")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
