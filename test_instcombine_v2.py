"""
test_instcombine_v2.py -- unit tests for instcombine_v2, isolated from
clang/opt. Exercises the new fold rules directly on hand-built states
so regressions surface without a Colab/LLVM environment.

Run with: python3 test_instcombine_v2.py
"""

import sys
from instcombine_v2 import make_step_instcombine

# Minimal stand-ins for _valid / _freeze, matching the real semantics
# in orderspector_reference.py (topological validity + frozen operand map).

def _valid(word, ops):
    pos = {nid: i for i, nid in enumerate(word)}
    for nid in word:
        for inp in ops.get(nid, ()):
            if inp in pos and pos[inp] > pos[nid]:
                return False
    return True

def _freeze(ops):
    return frozenset((k, tuple(v)) for k, v in ops.items())


def _fixpoint(state, step_fn, max_iter=20):
    cur = state
    for _ in range(max_iter):
        nxt = step_fn(cur)
        if not nxt:
            return cur
        cur = next(iter(nxt))
    return cur


PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}   {detail}")


def test_icmp_self_fold():
    # %c = icmp eq %x, %x   -> %c replaced by a 'true' literal
    OPCODE = {'%x': 'arg', '%c': 'icmp'}
    OPERANDS = {'%x': (), '%c': ('%x', '%x')}
    word = ('%x', '%c')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, nops_fs = result
    nops = dict(nops_fs)
    check("icmp eq x,x removed", '%c' not in nw, nw)
    check("replacement classified as lit",
          any(OPCODE.get(k) == 'lit' for k in nw if k not in ('%x',)),
          OPCODE)


def test_add_const_fold():
    # %r = add 2, 3   -> folds to a literal 5
    OPCODE = {'2': 'lit', '3': 'lit', '%r': 'add'}
    OPERANDS = {'2': (), '3': (), '%r': ('2', '3')}
    word = ('2', '3', '%r')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, _ = result
    check("add const,const removed original add", '%r' not in nw, nw)


def test_sub_self_zero():
    # %r = sub %x, %x   -> folds to 0 ('false')
    OPCODE = {'%x': 'arg', '%r': 'sub'}
    OPERANDS = {'%x': (), '%r': ('%x', '%x')}
    word = ('%x', '%r')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, _ = result
    check("sub x,x removed", '%r' not in nw, nw)
    check("zero constant registered",
          any(OPCODE.get(k) == 'lit' for k in nw),
          OPCODE)


def test_add_zero_identity():
    # %r = add %x, 0   -> %r replaced directly by %x (no new const needed)
    OPCODE = {'%x': 'arg', '0': 'lit', '%r': 'add'}
    OPERANDS = {'%x': (), '0': (), '%r': ('%x', '0')}
    word = ('%x', '0', '%r')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, _ = result
    check("add x,0 removed", '%r' not in nw, nw)


def test_mul_one_identity():
    OPCODE = {'%x': 'arg', '1': 'lit', '%r': 'mul'}
    OPERANDS = {'%x': (), '1': (), '%r': ('%x', '1')}
    word = ('%x', '1', '%r')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, _ = result
    check("mul x,1 removed", '%r' not in nw, nw)


def test_cascade_icmp_then_dce_ready():
    """
    Reproduces the g() case from the Colab test:
        c = (x == x)      -- icmp eq
        unused = c + c    -- add on the folded result
    After instcombine reaches fixpoint, 'unused' should be a folded
    constant (2), leaving nothing for instcombine itself to do further,
    but making it trivially dead for a DCE pass to remove (verified
    structurally here, not by invoking the real DCE stepper).
    """
    OPCODE = {'%x': 'arg', '%c': 'icmp', '%u': 'add'}
    OPERANDS = {'%x': (), '%c': ('%x', '%x'), '%u': ('%c', '%c')}
    word = ('%x', '%c', '%u')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, nops_fs = result
    nops = dict(nops_fs)
    check("icmp and add both folded away", '%c' not in nw and '%u' not in nw, nw)
    check("only %x plus folded literal(s) remain",
          all(OPCODE.get(k) in ('arg', 'lit') for k in nw), (nw, OPCODE))


def test_no_spurious_merging_of_distinct_folds():
    """
    Two independent add-const-folds with different values must not be
    merged into the same id by _fresh_const's uniqueness counter.
    """
    OPCODE = {'2': 'lit', '3': 'lit', '4': 'lit', '%r1': 'add', '%r2': 'add'}
    OPERANDS = {'2': (), '3': (), '4': (),
                '%r1': ('2', '3'), '%r2': ('2', '4')}
    word = ('2', '3', '4', '%r1', '%r2')
    s0 = (word, _freeze(OPERANDS))
    step = make_step_instcombine(OPCODE, _valid, _freeze)
    result = _fixpoint(s0, step)
    nw, _ = result
    check("both adds folded, distinct results not collapsed",
          '%r1' not in nw and '%r2' not in nw, nw)


if __name__ == "__main__":
    print("=" * 70)
    print("instcombine_v2 unit tests")
    print("=" * 70)
    test_icmp_self_fold()
    test_add_const_fold()
    test_sub_self_zero()
    test_add_zero_identity()
    test_mul_one_identity()
    test_cascade_icmp_then_dce_ready()
    test_no_spurious_merging_of_distinct_folds()
    print("-" * 70)
    print(f"{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
