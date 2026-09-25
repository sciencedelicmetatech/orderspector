"""
part4_extended.py -- extends the LLVM bridge (Part 4) to properly cover
instcombine pairs, using live `opt` invocations instead of hardcoded
LLVM_MEASURED tuples. Requires clang/opt on PATH (run in the same
Colab/container as orderspector_colab_test.py).

Run with: python3 part4_extended.py
"""

import os
import re
import subprocess

import orderspector_reference as ref
from instcombine_v2 import make_step_instcombine


def check_llvm_available():
    for tool in ("clang", "opt"):
        try:
            subprocess.run([tool, "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"ERROR: `{tool}` not found.")
            return False
    return True


def build_ir(c_source, fn_name, workdir):
    os.makedirs(workdir, exist_ok=True)
    src_path = os.path.join(workdir, "src.c")
    with open(src_path, "w") as fh:
        fh.write(c_source)
    naive_path = os.path.join(workdir, "naive.ll")
    subprocess.run(
        f"clang -Xclang -disable-O0-optnone -O0 -S -emit-llvm {src_path} -o {naive_path}",
        shell=True, check=True, capture_output=True,
    )
    with open(naive_path) as fh:
        ll = fh.read()
    m = re.search(r'define[^{]*@' + fn_name + r'\s*\([^)]*\)[^{]*\{(.*?)\n\}', ll, re.DOTALL)
    if not m:
        raise RuntimeError(f"could not find function @{fn_name}")
    insts = ref._parse_function(m.group(1))
    return insts, naive_path


def live_llvm_pair_counts(naive_path, pass_a, pass_b, fn_name, workdir):
    counts = {}
    for order_name, pipeline in [("ab", f"{pass_a},{pass_b}"), ("ba", f"{pass_b},{pass_a}")]:
        out_path = os.path.join(workdir, f"{pass_a}_{pass_b}_{order_name}.ll")
        subprocess.run(
            ["opt", f"-passes={pipeline}", "-S", naive_path, "-o", out_path],
            check=True, capture_output=True,
        )
        counts[order_name] = ref._count_llvm(out_path, fn_name)
    return counts["ab"], counts["ba"]


def build_passes(OPCODE):
    return {
        'mem2reg': ref._make_step_mem2reg(OPCODE),
        'gvn': ref._make_step_gvn(OPCODE),
        'instcombine': make_step_instcombine(OPCODE, ref._valid, ref._freeze),
        'dce': ref._make_step_dce(OPCODE),
    }


def run_pair(c_source, fn_name, workdir, pairs_to_test):
    print("=" * 78)
    print(f"PART 4 EXTENDED: {fn_name}")
    print("=" * 78)
    if not check_llvm_available():
        return

    insts, naive_path = build_ir(c_source, fn_name, workdir)
    OPCODE = dict((i['id'], i['opcode']) for i in insts)
    OPERANDS = dict((i['id'], i['operands']) for i in insts)
    w0 = tuple(i['id'] for i in insts)
    for i in insts:
        for op in i['operands']:
            if op not in OPCODE:
                OPCODE[op] = 'arg' if op.startswith('%') else 'lit'
                OPERANDS[op] = ()
    s0 = (w0, ref._freeze(OPERANDS))

    passes = build_passes(OPCODE)

    print(f"Parsed {len(w0)} instructions from clang -O0 output.\n")
    header = f"{'pair':<28}{'framework':<12}{'fw(a,b)':<10}{'fw(b,a)':<10}{'LLVM(a,b)':<12}{'LLVM(b,a)':<12}{'agree?'}"
    print(header)
    print("-" * len(header))

    results = []
    for pass_a, pass_b in pairs_to_test:
        cls, fw_ab, fw_ba = ref._classify_pair(passes[pass_a], passes[pass_b], s0)
        llvm_ab, llvm_ba = live_llvm_pair_counts(naive_path, pass_a, pass_b, fn_name, workdir)

        fw_diff = fw_ab != fw_ba
        llvm_diff = llvm_ab != llvm_ba
        # "agree" = framework and LLVM both say tied, or both say order-sensitive
        # in the same direction (smaller count wins)
        if not fw_diff and not llvm_diff:
            agree = "AGREE(tied)"
        elif fw_diff and llvm_diff:
            fw_dir = "ab" if fw_ab < fw_ba else "ba"
            llvm_dir = "ab" if llvm_ab < llvm_ba else "ba"
            agree = "AGREE(dir)" if fw_dir == llvm_dir else "MISMATCH(dir)"
        else:
            agree = "MISMATCH(tied-vs-sensitive)"

        pair_str = f"{pass_a} x {pass_b}"
        print(f"{pair_str:<28}{cls:<12}{fw_ab:<10}{fw_ba:<10}{llvm_ab:<12}{llvm_ba:<12}{agree}")
        results.append((pass_a, pass_b, cls, fw_ab, fw_ba, llvm_ab, llvm_ba, agree))
    print()
    return results


if __name__ == "__main__":
    workdir = "/tmp/orderspector_part4_ext"

    C_TOY = (
        "int f(int x, int y, int z) {\n"
        "    int a = x + y;\n"
        "    int b = x + y;\n"
        "    int c = a * b;\n"
        "    int d = a + z;\n"
        "    int e = b + z;\n"
        "    int dead1 = x * y;\n"
        "    int dead2 = dead1 + 7;\n"
        "    return c + d + e;\n"
        "}\n"
    )
    C_INSTCOMBINE_DCE = (
        "int g(int x) {\n"
        "    int c = (x == x);\n"
        "    int unused = c + c;\n"
        "    return x;\n"
        "}\n"
    )

    all_results = []
    all_results += run_pair(C_TOY, "f", workdir + "_toy",
                             [('mem2reg', 'gvn'), ('gvn', 'dce'),
                              ('mem2reg', 'dce'), ('instcombine', 'dce'),
                              ('mem2reg', 'instcombine')])
    all_results += run_pair(C_INSTCOMBINE_DCE, "g", workdir + "_ic",
                             [('instcombine', 'dce'), ('gvn', 'instcombine')])

    n_agree = sum(1 for r in all_results if r[-1].startswith("AGREE"))
    print("=" * 78)
    print(f"TOTAL: {n_agree}/{len(all_results)} pairs agree (framework vs live LLVM)")
    print("=" * 78)
