"""
ORDERSPECTOR ON SYMBOLIC RULES -- v4
Fixes the verified() early-exit bug and mirrors the corpus.
"""
import os as _os, sys as _sys
_ME = _os.path.abspath(__file__) if "__file__" in globals() else None
if _ME and _os.path.exists(_ME):
    _s = open(_ME, encoding="utf-8").read()
    _f = (_s.replace("\u201c", '"').replace("\u201d", '"')
             .replace("\u2018", "'").replace("\u2019", "'"))
    if _f != _s:
        open(_ME, "w", encoding="utf-8").write(_f)
        print("[self-heal] re-run"); _sys.exit(0)

MAX_STEPS = 30
MIN_DIR_SAMPLE = 10


def match(pattern, term, bindings=None):
    if bindings is None:
        bindings = {}
    if isinstance(pattern, str):
        if pattern.startswith("$"):
            if pattern in bindings:
                return bindings if bindings[pattern] == term else None
            b = dict(bindings)
            b[pattern] = term
            return b
        return bindings if pattern == term else None
    if isinstance(pattern, tuple):
        if not isinstance(term, tuple):
            return None
        if len(pattern) != len(term):
            return None
        b = bindings
        for p, t in zip(pattern, term):
            b = match(p, t, b)
            if b is None:
                return None
        return b
    return None


def substitute(rhs, bindings):
    if isinstance(rhs, str):
        return bindings.get(rhs, rhs) if rhs.startswith("$") else rhs
    if isinstance(rhs, tuple):
        return tuple(substitute(x, bindings) for x in rhs)
    return rhs


def redexes(lhs, term, path=()):
    out = []
    b = match(lhs, term)
    if b is not None:
        out.append((path, b))
    if isinstance(term, tuple):
        for i, sub in enumerate(term):
            out.extend(redexes(lhs, sub, path + (i,)))
    return out


def apply_at(term, path, rhs, bindings):
    if not path:
        return substitute(rhs, bindings)
    i = path[0]
    return term[:i] + (apply_at(term[i], path[1:], rhs, bindings),) + term[i+1:]


def rewrite(term, rules, max_steps=MAX_STEPS):
    if term is None or not rules:
        return term, 0
    steps = 0
    while True:
        moved = False
        for lhs, rhs in rules:
            m = redexes(lhs, term)
            if m:
                path, b = m[0]
                term = apply_at(term, path, rhs, b)
                moved = True
                steps += 1
                if steps >= max_steps:
                    return None, steps
                break
        if not moved:
            break
    return term, steps


def tree_size(t):
    if isinstance(t, tuple):
        return 1 + sum(tree_size(x) for x in t)
    return 1


def mirror(term):
    if isinstance(term, tuple):
        return tuple(mirror(x) for x in reversed(term))
    return term


def gt_sensitive(a, b, term):
    rab, _ = rewrite(term, [a])
    if rab is None: return True
    rab, _ = rewrite(rab, [b])
    rba, _ = rewrite(term, [b])
    if rba is None: return True
    rba, _ = rewrite(rba, [a])
    if rab is None or rba is None: return True
    return rab != rba


def paths_overlap(p1, p2):
    n = min(len(p1), len(p2))
    return p1[:n] == p2[:n]


def p_overlap(a, b, term):
    ma = redexes(a[0], term); mb = redexes(b[0], term)
    for pa, _ in ma:
        for pb, _ in mb:
            if paths_overlap(pa, pb):
                return True, 0
    return False, 0


def p_asym(a, b, term):
    la, ra = a; lb, rb = b
    ma = redexes(la, term); mb = redexes(lb, term)
    steps = 0; cb = False
    for path, bd in ma:
        t1 = apply_at(term, path, ra, bd); steps += 1
        if len(redexes(lb, t1)) > len(mb): cb = True; break
    ca = False
    for path, bd in mb:
        t2 = apply_at(term, path, rb, bd); steps += 1
        if len(redexes(la, t2)) > len(ma): ca = True; break
    return (cb != ca), steps


def p_destroy(a, b, term):
    la, ra = a; lb, rb = b
    ma = redexes(la, term); mb = redexes(lb, term)
    steps = 0
    for path, bd in ma:
        t1 = apply_at(term, path, ra, bd); steps += 1
        if len(redexes(lb, t1)) < len(mb): return True, steps
    for path, bd in mb:
        t2 = apply_at(term, path, rb, bd); steps += 1
        if len(redexes(la, t2)) < len(ma): return True, steps
    return False, steps


def p_mutual(a, b, term):
    la, ra = a; lb, rb = b
    ma = redexes(la, term); mb = redexes(lb, term)
    steps = 0; cb = False
    for path, bd in ma:
        t1 = apply_at(term, path, ra, bd); steps += 1
        if len(redexes(lb, t1)) > len(mb): cb = True; break
    ca = False
    for path, bd in mb:
        t2 = apply_at(term, path, rb, bd); steps += 1
        if len(redexes(la, t2)) > len(ma): ca = True; break
    return (cb and ca), steps


PROPOSERS = {"overlap": p_overlap, "asym": p_asym,
             "destroy": p_destroy, "mutual": p_mutual}
DEFAULT_SET = ["overlap", "asym"]


def propose(a, b, term, names):
    total = 0
    for n in names:
        f, s = PROPOSERS[n](a, b, term)
        total += s
        if f:
            return True, total
    return False, total


def verified(rule_a, rule_b, terms, names=None):
    """FIX: continue scanning when verification on a term is confluent.
    Do not give up on the first proposer witness that happens to be safe."""
    names = names or DEFAULT_SET
    la, ra = rule_a[1], rule_a[2]
    lb, rb = rule_b[1], rule_b[2]
    cost = 0

    for t in terms:
        f, s = propose((la, ra), (lb, rb), t, names)
        cost += s
        if not f:
            continue
        rab, s1 = rewrite(t, [(la, ra)])
        if rab is not None:
            rab, s2 = rewrite(rab, [(lb, rb)]); s1 += s2
        rba, s3 = rewrite(t, [(lb, rb)])
        if rba is not None:
            rba, s4 = rewrite(rba, [(la, ra)]); s3 += s4
        cost += s1 + s3

        if rab is None or rba is None:
            return True, "DIVERGE", cost
        if rab == rba:
            continue
        if tree_size(rab) < tree_size(rba):
            return True, "AB", cost
        if tree_size(rba) < tree_size(rab):
            return True, "BA", cost
        return True, ("AB" if s1 <= s3 else "BA"), cost

    return False, None, cost


RULES = [
    ("add_right_id",   ("add", "$X", "0"), "$X"),
    ("add_left_id",    ("add", "0", "$X"), "$X"),
    ("mul_right_id",   ("mul", "$X", "1"), "$X"),
    ("mul_left_id",    ("mul", "1", "$X"), "$X"),
    ("mul_right_zero", ("mul", "$X", "0"), "0"),
    ("mul_left_zero",  ("mul", "0", "$X"), "0"),
    ("sub_self",       ("sub", "$X", "$X"), "0"),
    ("div_one",        ("div", "$X", "1"), "$X"),
    ("pow_zero",       ("pow", "$X", "0"), "1"),
    ("pow_one",        ("pow", "$X", "1"), "$X"),
    ("add_self",       ("add", "$X", "$X"), ("mul", "2", "$X")),
    ("two_mul",        ("mul", "2", "$X"), ("add", "$X", "$X")),
]


_BASE_TERMS = [
    "a", "b", "0", "1", "2",
    ("add", "a", "0"),
    ("add", "0", "a"),
    ("mul", "a", "1"),
    ("mul", "1", "a"),
    ("mul", "a", "0"),
    ("mul", "0", "a"),
    ("sub", "a", "a"),
    ("div", "a", "1"),
    ("pow", "a", "0"),
    ("pow", "a", "1"),
    ("add", "a", "a"),
    ("mul", "2", "a"),
    ("mul", ("add", "a", "0"), "0"),
    ("mul", "0", ("add", "a", "0")),
    ("add", ("mul", "a", "1"), "0"),
    ("add", ("add", "a", "0"), "0"),
    ("mul", ("mul", "a", "1"), "1"),
    ("add", ("sub", "a", "a"), "0"),
    ("mul", ("pow", "a", "1"), "1"),
    ("pow", ("add", "a", "0"), "1"),
    ("add", ("mul", "a", "0"), "1"),
    ("add", "1", ("mul", "a", "0")),
    ("add", ("add", "a", "a"), "0"),
    ("add", ("mul", "2", "a"), "0"),
    ("add", ("add", "a", "0"), ("add", "a", "0")),
    ("add", ("mul", "a", "1"), ("mul", "a", "1")),
    ("add", ("add", "a", "b"), "0"),
    ("mul", ("add", "a", "0"), ("add", "b", "0")),
    ("add", ("mul", "a", "1"), ("mul", "b", "0")),
    ("add", ("sub", "a", "a"), ("sub", "b", "b")),
    ("mul", ("add", "a", "a"), "1"),
    ("mul", "1", ("add", "a", "a")),
    ("div", ("add", "a", "a"), "1"),
    ("pow", ("add", "a", "a"), "1"),
    ("add", ("add", "a", "0"), ("mul", "b", "1")),
    ("mul", ("mul", "a", "1"), ("add", "b", "0")),
    ("add", ("add", "a", "a"), ("mul", "2", "b")),
]


def _build_terms():
    seen = set()
    out = []
    for t in _BASE_TERMS:
        for cand in (t, mirror(t)):
            key = repr(cand)
            if key not in seen:
                seen.add(key)
                out.append(cand)
    return out


TERMS = _build_terms()


def main():
    print("=" * 76)
    print("ORDERSPECTOR ON SYMBOLIC RULES -- v4 (MIRRORED, FIXED VERIFIED)")
    print("=" * 76)
    print("rules: {}   base terms: {}   mirrored terms: {}   pairs: {}".format(
        len(RULES), len(_BASE_TERMS), len(TERMS),
        len(RULES) * (len(RULES) - 1) // 2))
    print("")

    for name, lhs, rhs in RULES:
        print("  {:<18} {:<24} ->  {}".format(name, str(lhs), str(rhs)))
    print("")

    print("Computing ground truth ...")
    pairs = []
    for i in range(len(RULES)):
        for j in range(i + 1, len(RULES)):
            pairs.append((RULES[i], RULES[j]))

    truth = {}
    for ra, rb in pairs:
        s = any(gt_sensitive((ra[1], ra[2]), (rb[1], rb[2]), t) for t in TERMS)
        truth[(ra[0], rb[0])] = s

    positives = sum(1 for v in truth.values() if v)
    print("  truly order-sensitive: {}/{} ({:.1%})".format(
        positives, len(pairs), positives / len(pairs) if pairs else 0))
    print("")

    tp = fp = fn_ = tn = 0
    cost = 0
    dirs = {"AB": 0, "BA": 0, "DIVERGE": 0}
    fired_pairs = []
    missed_pairs = []

    for ra, rb in pairs:
        fired, direction, c = verified(ra, rb, TERMS)
        cost += c
        actual = truth[(ra[0], rb[0])]
        if fired and actual:
            tp += 1
            if direction in dirs: dirs[direction] += 1
            fired_pairs.append((ra[0], rb[0], direction))
        elif fired and not actual:
            fp += 1
        elif not fired and actual:
            fn_ += 1
            missed_pairs.append((ra[0], rb[0]))
        else:
            tn += 1

    total = tp + fp + fn_ + tn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn_) if (tp + fn_) else 0.0
    base = positives / total if total else 0.0
    lift = prec / base if base else 0.0
    avg = cost / len(pairs) if pairs else 0.0

    print("RESULTS:")
    print("  fired:      {}".format(tp + fp))
    print("  true pos:   {}".format(tp))
    print("  false pos:  {}".format(fp))
    print("  false neg:  {}".format(fn_))
    print("  precision:  {:.3f}".format(prec))
    print("  recall:     {:.3f}".format(rec))
    print("  base rate:  {:.3f}".format(base))
    print("  lift:       {:.2f}x".format(lift))
    print("  avg cost:   {:.2f} rewrite steps per pair".format(avg))
    print("")

    print("ORDER-SENSITIVE PAIRS (classified):")
    if not fired_pairs:
        print("  (none)")
    for a, b, d in fired_pairs:
        print("  {:<18} x {:<18}  direction={}".format(a, b, d))
    print("")

    if missed_pairs:
        print("MISSED PAIRS (order matters, no proposer fired):")
        for a, b in missed_pairs:
            print("  {:<18} x {}".format(a, b))
        print("")

    total_dir = sum(dirs.values())
    if total_dir:
        print("Direction split (n={}): AB={} BA={} DIVERGE={}".format(
            total_dir, dirs["AB"], dirs["BA"], dirs["DIVERGE"]))
        if total_dir < MIN_DIR_SAMPLE:
            print("  (sample too small to assess bias, n < {})".format(MIN_DIR_SAMPLE))
        else:
            ab_frac = dirs["AB"] / total_dir
            ba_frac = dirs["BA"] / total_dir
            if abs(ab_frac - ba_frac) > 0.15:
                print("  (WARNING: direction split is skewed)")
            else:
                print("  (balanced)")


if __name__ == "__main__":
    main()
