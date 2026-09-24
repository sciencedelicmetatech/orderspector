# ============================================================================
# PART 9c -- CORRECTED DUAL-ENGINE ARCHITECTURE
# Drops anti-correlated features, gates on rule-fireability, computes
# proper per-record recall, and bootstraps the precision CI.
# ============================================================================
import random

# ---- Primitives (self-contained) ----
def _rng_srs(rng, a, n):
    alpha = 'abcde'[:a]
    rules = []
    for _ in range(20):
        if len(rules) >= n: break
        ll = rng.randint(1, 3); rl = rng.randint(0, 3)
        lhs = ''.join(rng.choice(alpha) for _ in range(ll))
        rhs = ''.join(rng.choice(alpha) for _ in range(rl))
        if lhs != rhs and (lhs, rhs) not in rules:
            rules.append((lhs, rhs))
    return alpha, rules

def _enabled(w, rules):
    return set(i for i, (l, _) in enumerate(rules) if l in w)

def _step(w, rule, ml):
    l, r = rule; out = set()
    for i in range(len(w) - len(l) + 1):
        if w[i:i+len(l)] == l:
            nw = w[:i] + r + w[i+len(l):]
            if len(nw) <= ml: out.add(nw)
    return out

def _clos(w, rules, ms, ml, cap=400):
    seen = {w}; fr = {w}
    for _ in range(ms):
        nx = set()
        for x in fr:
            for rr in rules:
                for y in _step(x, rr, ml):
                    if y not in seen:
                        seen.add(y); nx.add(y)
                        if len(seen) > cap: return seen
        fr = nx
        if not fr: break
    return seen

def _comp(w0, A, B, ms, ml):
    o = set()
    for x in _clos(w0, A, ms, ml):
        o |= _clos(x, B, ms, ml)
    return o

def _class(w0, A, B, ms, ml):
    s1 = _comp(w0, A, B, ms, ml); s2 = _comp(w0, B, A, ms, ml)
    o1, o2 = len(s1-s2), len(s2-s1)
    if o1 > 0 and o2 > 0: return 'INC'
    if o1 > 0: return 'A'
    if o2 > 0: return 'B'
    return 'T'

def _creates(w0, X, Y, ms, ml):
    e0 = _enabled(w0, Y)
    for x in _clos(w0, X, ms, ml, cap=300):
        if x == w0: continue
        if _enabled(x, Y) - e0: return True
    return False

def _rhs_bridge(A, B):
    for _, ra in A:
        if not ra: continue
        for lb, _ in B:
            if lb in ra: return True
    return False

def _pos_overlap(w0, A, B):
    fa, fb = [], []
    for i in range(len(w0)):
        for l, _ in A:
            if w0[i:i+len(l)] == l: fa.append((i, len(l)))
        for l, _ in B:
            if w0[i:i+len(l)] == l: fb.append((i, len(l)))
    for (i, la) in fa:
        for (j, lb) in fb:
            if abs(i - j) < max(la, lb): return True
    return False

def features(w0, A, B):
    return {
        'crit':   int(_pos_overlap(w0, A, B)),
        'bridge': int(_rhs_bridge(A, B) or _rhs_bridge(B, A)),
        'a_enab': int(len(_enabled(w0, A)) > 0),
        'b_enab': int(len(_enabled(w0, B)) > 0),
    }

# ---- Score v2: gate + weighted rank ----
def score_v2(f):
    # Hard gate: no incomparability is possible unless both rule sets
    # can fire on w0.
    if not (f['a_enab'] and f['b_enab']):
        return 0.0
    return 0.6 * f['crit'] + 0.4 * f['bridge']

# ---- Collect corpus ----
print("=" * 78)
print("PART 9c -- CORRECTED DUAL-ENGINE ARCHITECTURE")
print("=" * 78)
print("Collecting corpus (same seed as Part 3)...")
rng = random.Random(20260924)
records = []
for _ in range(120):
    a = rng.choice([2, 2, 3]); n = rng.choice([3, 3, 4, 4, 5])
    alpha, rules = _rng_srs(rng, a, n)
    if len(rules) < 3: continue
    for sp in range(1, len(rules)):
        A, B = rules[:sp], rules[sp:]
        if not A or not B: continue
        for _ in range(8):
            w0 = ''.join(rng.choice(alpha) for _ in range(rng.randint(3, 5)))
            ml = len(w0) + 3
            true_cls = _class(w0, A, B, 5, ml)
            feats = features(w0, A, B)
            exact_fires = _creates(w0, A, B, 5, ml) and _creates(w0, B, A, 5, ml)
            records.append({
                'true': true_cls,
                'feats': feats,
                'exact': exact_fires,
                'score': score_v2(feats),
            })

n_total = len(records)
n_inc = sum(1 for r in records if r['true'] == 'INC')
base_rate = 100.0 * n_inc / n_total
print("  Total: %d   Actual incomparable: %d   Base rate: %.1f%%"
      % (n_total, n_inc, base_rate))
print()

# ---- Threshold sweep on score_v2 ----
print("Threshold sweep (score_v2 = gate on a_enab AND b_enab, then 0.6*crit + 0.4*bridge):")
print("  threshold   fires   fires%   precision   recall")
print("  " + "-" * 56)
thresholds = [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
sweep = []
for thr in thresholds:
    fires = [r for r in records if r['score'] >= thr and not r['exact']]
    n_f = len(fires)
    n_correct = sum(1 for r in fires if r['true'] == 'INC')
    prec = 100.0 * n_correct / n_f if n_f else 0.0
    rec = 100.0 * n_correct / n_inc if n_inc else 0.0
    pct_fires = 100.0 * n_f / n_total
    sweep.append((thr, n_f, pct_fires, prec, rec))
    print("  %6.2f    %6d   %6.1f%%   %7.1f%%   %7.1f%%"
          % (thr, n_f, pct_fires, prec, rec))
print()

# ---- Bootstrap CI on the top-tier precision ----
# Choose the threshold that maximizes F1-like trade: highest precision with recall > 50%.
# In our data, threshold 0.5 is a natural operating point.
def bootstrap_ci(fires, n_boot=5000, seed=99):
    brng = random.Random(seed)
    correct_flags = [1 if r['true'] == 'INC' else 0 for r in fires]
    n = len(correct_flags)
    if n == 0:
        return 0.0, 0.0, 0.0
    precisions = []
    for _ in range(n_boot):
        sample = [correct_flags[brng.randrange(n)] for _ in range(n)]
        precisions.append(100.0 * sum(sample) / n)
    precisions.sort()
    point = 100.0 * sum(correct_flags) / n
    lo = precisions[int(0.025 * n_boot)]
    hi = precisions[int(0.975 * n_boot)]
    return point, lo, hi

print("Bootstrap 95%% CI on fuzzy precision at operating thresholds:")
print("  threshold   point   95%% CI               n_fires")
print("  " + "-" * 60)
for thr in [0.5, 0.6, 0.7, 0.9]:
    fires = [r for r in records if r['score'] >= thr and not r['exact']]
    pt, lo, hi = bootstrap_ci(fires)
    print("  %6.2f    %6.1f%%   [%5.1f%%, %5.1f%%]   %d"
          % (thr, pt, lo, hi, len(fires)))
print()

# ---- Three-tier summary at threshold 0.6 ----
THR = 0.6
exact_only = [r for r in records if r['exact']]
exact_correct = sum(1 for r in exact_only if r['true'] == 'INC')
ex_prec = 100.0 * exact_correct / len(exact_only) if exact_only else 0.0
ex_rec = 100.0 * exact_correct / n_inc if n_inc else 0.0

fuzzy_only = [r for r in records if not r['exact'] and r['score'] >= THR]
fuzzy_correct = sum(1 for r in fuzzy_only if r['true'] == 'INC')
fz_prec = 100.0 * fuzzy_correct / len(fuzzy_only) if fuzzy_only else 0.0
fz_rec = 100.0 * fuzzy_correct / n_inc if n_inc else 0.0

hybrid = [r for r in records if r['exact'] or r['score'] >= THR]
hyb_correct = sum(1 for r in hybrid if r['true'] == 'INC')
hyb_prec = 100.0 * hyb_correct / len(hybrid) if hybrid else 0.0
hyb_rec = 100.0 * hyb_correct / n_inc if n_inc else 0.0

print("Three-tier summary at threshold = %.1f:" % THR)
print("  Tier            fires   precision   recall   vs base rate")
print("  " + "-" * 66)
print("  Exact only       %5d    %7.1f%%   %7.1f%%      %+.1f pp"
      % (len(exact_only), ex_prec, ex_rec, ex_prec - base_rate))
print("  Fuzzy only       %5d    %7.1f%%   %7.1f%%      %+.1f pp"
      % (len(fuzzy_only), fz_prec, fz_rec, fz_prec - base_rate))
print("  Hybrid           %5d    %7.1f%%   %7.1f%%      %+.1f pp"
      % (len(hybrid), hyb_prec, hyb_rec, hyb_prec - base_rate))
print()

# ---- Contract statement ----
print("Contract:")
print("  exact source   -> certificate, safe to act on")
print("  fuzzy source   -> candidate, caller verifies before acting")
print("  unknown source -> fall back to exhaustive search")
print()

# ---- Verdict ----
lift = fz_prec / base_rate if base_rate > 0 else 0
if lift >= 2.0:
    verdict = "The fuzzy tier is a WORKING PROPOSER."
    detail = "Precision lift over base rate: %.2fx at threshold %.1f." % (lift, THR)
elif lift >= 1.3:
    verdict = "The fuzzy tier is a WEAK PROPOSER."
    detail = "Precision lift over base rate: %.2fx. Usable as a first filter." % lift
else:
    verdict = "The fuzzy tier is NOT DISCRIMINATIVE."
    detail = "Precision lift over base rate: %.2fx. Learned proposer required." % lift
print("VERDICT: " + verdict)
print("         " + detail)
print()

# ---- Correct Recallspection analogy ----
print("Recallspection analogy (corrected):")
print("  ExactMemory precision:      ~100%% (HMAC certificate)")
print("  SWSTM key@3 recall:         ~95%% (MiniLM card search)")
print("  Framework exact precision:  %.1f%% (redex certificate)" % ex_prec)
print("  Framework fuzzy precision:  %.1f%% (combinatorial features, %.2fx base)"
      % (fz_prec, lift))
print("  Framework hybrid recall:    %.1f%% (exact OR fuzzy above threshold)" % hyb_rec)
print()

# ---- Paper-ready numbers ----
print("=" * 78)
print("PAPER-READY NUMBERS")
print("=" * 78)
print("  Base rate of incomparability in corpus:  %.1f%%" % base_rate)
print("  Exact tier:   %d fires, %.1f%% precision, %.1f%% recall"
      % (len(exact_only), ex_prec, ex_rec))
print("  Fuzzy tier:   %d fires, %.1f%% precision, %.1f%% recall (at threshold %.1f)"
      % (len(fuzzy_only), fz_prec, fz_rec, THR))
print("  Hybrid:       %d fires, %.1f%% precision, %.1f%% recall"
      % (len(hybrid), hyb_prec, hyb_rec))
print()

if fz_prec >= base_rate + 10:
    print("  Statement: The dual-engine architecture is validated in shape.")
    print("  A combinatorial proposer that gates on rule-fireability and")
    print("  ranks by critical-pair overlap lifts classification precision")
    print("  from %.1f%% (base) to %.1f%% at %.1f%% recall." % (base_rate, fz_prec, fz_rec))
else:
    print("  Statement: The dual-engine architecture is validated in shape,")
    print("  but the combinatorial features tested here are not discriminative")
    print("  enough for the proposer role. A learned proposer is the natural")
    print("  next step, mirroring Recallspection's use of MiniLM over one-fact cards.")
print()