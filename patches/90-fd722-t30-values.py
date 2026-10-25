#!/usr/bin/env python3
"""FD722: MrPurple T30's device values, which render the MK8 HUD icons correctly.

T30's own meta.json: "Patched: num_ccu=2, tile_align_h=32, highest_bank_bit=16.
Adreno 722 uses tu_autotune GMEM/sysmem selection." That package is confirmed
visually clean on this device, so these three values are the baseline to build
performance on top of, rather than our own 1 / 16 / 15 set.

Idempotent. Run from the Mesa source root.
"""
import re
import sys

NAME = "90-fd722-t30-values.py"
SUMMARY = "FD722 num_ccu=2, tile_align_h=32, highest_bank_bit=16 (T30 values)"
DEVICES_PY = "src/freedreno/common/freedreno_devices.py"
NUM_CCU, TILE_ALIGN_H, HBB = 2, 32, 16


def main():
    try:
        src = open(DEVICES_PY, encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: ERROR cannot read {DEVICES_PY}: {e}", file=sys.stderr)
        return 1
    m = re.search(r"GPUId\(chip_id=0x43020100.*?\n    \)\)", src, re.S)
    if not m:
        print(f"{NAME}: ERROR FD722 (0x43020100) block not found", file=sys.stderr)
        return 1
    block = new = m.group(0)
    new = re.sub(r"\bnum_ccu\s*=\s*\d+", f"num_ccu = {NUM_CCU}", new)
    new = re.sub(r"\btile_align_h\s*=\s*\d+", f"tile_align_h = {TILE_ALIGN_H}", new)
    if re.search(r"\bhighest_bank_bit\s*=\s*\d+", new):
        new = re.sub(r"\bhighest_bank_bit\s*=\s*\d+", f"highest_bank_bit = {HBB}", new)
    else:
        if "raw_magic_regs" not in new:
            print(f"{NAME}: ERROR no raw_magic_regs anchor for highest_bank_bit", file=sys.stderr)
            return 1
        new = new.replace("raw_magic_regs =",
                          f"highest_bank_bit = {HBB},\n        raw_magic_regs =", 1)
    for key, want in (("num_ccu", NUM_CCU), ("tile_align_h", TILE_ALIGN_H),
                      ("highest_bank_bit", HBB)):
        got = re.search(rf"\b{key}\s*=\s*(\d+)", new)
        if not got or int(got.group(1)) != want:
            print(f"{NAME}: ERROR {key} did not end at {want}", file=sys.stderr)
            return 1
    if new == block:
        print(f"{NAME}: already applied")
        return 0
    open(DEVICES_PY, "w", encoding="utf-8").write(src.replace(block, new, 1))
    print(f"{NAME}: applied ({SUMMARY})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
