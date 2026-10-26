#!/usr/bin/env python3
"""Default tu_autotune algorithm to PREFER_SYSMEM on Adreno 722 (1 MiB GMEM).

In upstream Mesa, tu_autotune::algorithm::PREFER_SYSMEM:
1. Still honors all GMEM-required paths in tu_autotune::get_optimal_mode():
   - sysmem_single_prim_mode (subpass feedback loops) -> GMEM
   - pass->has_fdm (fragment density map) -> GMEM
   - pass->has_msrtss (multisampled render to single sampled) -> GMEM
2. Uses SYSMEM for normal 1080p render passes so the 1 MiB GMEM on Adreno 722
   does not thrash into multi-bin tiling passes.
3. Leaves tu6_init_static_regs() and emit_rb_ccu_cntl() 100% unmodified upstream Mesa.
"""
import sys

NAME = "36-tu-z-sysmem-only.py"
AUTOTUNE = "src/freedreno/vulkan/tu_autotune.cc"

OLD = "   DEFAULT = BANDWIDTH, /* Default algorithm, used if no other is specified. */\n"
NEW = "   DEFAULT = PREFER_SYSMEM, /* Default algorithm for Adreno 722 1 MiB GMEM. */\n"


def main():
    try:
        s = open(AUTOTUNE, encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {AUTOTUNE}: {e}; skipped")
        return 0

    if NEW in s:
        print(f"{NAME}: already applied")
        return 0

    if s.count(OLD) != 1:
        print(f"{NAME}: WARNING anchor matched {s.count(OLD)}x in {AUTOTUNE}; skipped")
        return 0

    s = s.replace(OLD, NEW, 1)
    with open(AUTOTUNE, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)

    print(f"{NAME}: applied (tu_autotune DEFAULT = PREFER_SYSMEM)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
