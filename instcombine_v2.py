"""
instcombine_v2.py -- extended instcombine stepper with constant folding.

Drop-in replacement for orderspector_reference._make_step_instcombine.
Fixes:
  1. Synthetic constants ('true'/'false'/literal ints) were never
     classified in OPCODE, so downstream GVN/DCE treated them as
     unknown-opcode instructions instead of literals.
  2. No constant folding on add/sub/mul -> instcombine plateaued after
     one icmp-self-fold instead of cascading (e.g. c=(x==x); c+c never
     reduced further).
  3. No identity rules (x+0, x*1, x-x) -> missed additional DCE-enabling
     simplifications that real LLVM performs in the same pass.

Usage (in orderspector_reference.py):

    from instcombine_v2 import make_step_instcombine

    passes = {
        'instcombine': make_step_instcombine(OPCODE, _valid, _freeze),
        ...
    }

_valid and _freeze are passed in explicitly rather than imported, so
this module has no import-order dependency on the caller.
"""

import re

_INT_RE = re.compile(r'^-?\d+$')


def _is_const(OPCODE, x):
    return x in ('true', 'false') or OPCODE.get(x) == 'lit' or bool(_INT_RE.match(x))


def _const_val(OPCODE, x):
    if x == 'true':
        return 1
    if x == 'false':
        return 0
    if _INT_RE.match(x):
        return int(x)
    return None


def _fresh_const(OPCODE, val, counter):
    """Return a unique id for a folded constant, classified as 'lit'."""
    if val == 1:
        name = 'true'
    elif val == 0:
        name = 'false'
    else:
        # unique per-call name so distinct folded constants at different
        # instructions don't collide and get merged incorrectly by GVN
        # unless their value truly matches
        name = '%cfold.' + str(val) + '.' + str(next(counter))
    OPCODE[name] = 'lit'
    return name


def make_step_instcombine(OPCODE, _valid, _freeze):
    """
    Build the instcombine step function.

    OPCODE: mutable dict, id -> opcode string. Mutated in place to
            register newly-created constant ids (matches the pattern
            used elsewhere in orderspector_reference for 'arg'/'lit').
    _valid: orderspector_reference._valid (topological validity check)
    _freeze: orderspector_reference._freeze (operand-map freezing)
    """
    _counter_box = [0]

    def _next():
        _counter_box[0] += 1
        return _counter_box[0]

    def step(state):
        word, ops_fs = state
        ops = dict(ops_fs)
        out = set()

        def emit(n, replacement_id):
            new_ops = dict(ops)
            del new_ops[n]
            for k, ins in list(new_ops.items()):
                if k == n:
                    continue
                new_ops[k] = tuple(replacement_id if x == n else x for x in ins)
            nw = tuple(x for x in word if x != n)
            if _valid(nw, new_ops):
                out.add((nw, _freeze(new_ops)))

        for n in word:
            op = OPCODE.get(n)
            o = ops.get(n, ())

            # Rule 1: icmp eq x,x -> true
            if op == 'icmp' and len(o) == 2 and o[0] == o[1]:
                c = _fresh_const(OPCODE, 1, _next)
                emit(n, c)
                continue

            # Rule 2: constant folding on add/sub/mul
            if op in ('add', 'sub', 'mul') and len(o) == 2:
                a, b = o
                if _is_const(OPCODE, a) and _is_const(OPCODE, b):
                    va, vb = _const_val(OPCODE, a), _const_val(OPCODE, b)
                    if va is not None and vb is not None:
                        val = {'add': va + vb, 'sub': va - vb, 'mul': va * vb}[op]
                        c = _fresh_const(OPCODE, val, _next)
                        emit(n, c)
                        continue

            # Rule 3: self-subtraction, sub x,x -> 0
            if op == 'sub' and len(o) == 2 and o[0] == o[1]:
                c = _fresh_const(OPCODE, 0, _next)
                emit(n, c)
                continue

            # Rule 4: additive/multiplicative identities
            if op == 'add' and len(o) == 2:
                if _is_const(OPCODE, o[1]) and _const_val(OPCODE, o[1]) == 0:
                    emit(n, o[0]); continue
                if _is_const(OPCODE, o[0]) and _const_val(OPCODE, o[0]) == 0:
                    emit(n, o[1]); continue
            if op == 'mul' and len(o) == 2:
                if _is_const(OPCODE, o[1]) and _const_val(OPCODE, o[1]) == 1:
                    emit(n, o[0]); continue
                if _is_const(OPCODE, o[0]) and _const_val(OPCODE, o[0]) == 1:
                    emit(n, o[1]); continue

        return out

    return step
