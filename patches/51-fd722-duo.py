#!/usr/bin/env python3
"""FD722 (Retroid Pocket Duo, chip_id 0x43020100): pin the known-good GMEM config.

The Duo's 60 FPS docked result comes from upstream's own FD722 values, so this
script changes nothing today - it locks them in:

  num_ccu          1    asserted
  tile_align_h    16    asserted
  highest_bank_bit 15   written out; it is A6xxGPUInfo's default today
                        (freedreno_dev_info.py), and 15 is the Duo's device-tree
                        value, read from
                        /proc/device-tree/soc/qcom,kgsl-3d0@3d00000 (hbb = 15,
                        cross-checked against the kernel's RB_NC_MODE_CNTL
                        0x814, where bits 2:1 = hbb - 13).

Unlike the other patches here this one EXITS NON-ZERO if upstream has moved
num_ccu or tile_align_h, instead of warning and continuing. That is the point
of it: num_ccu is not a tuning knob, it is multiplied into the colour and depth
CCU offsets inside GMEM (src/freedreno/common/fd6_gmem_cache.h), and the Duo has
only 1 MiB of GMEM, so a changed value must be looked at by a human before it
ships. With MESA_REF pinned to a commit it can never fire.

To try the A720-style 2 CCU / 32 tile config instead, set EXPECT below to
(2, 32) and flip ENFORCE to False - the script then rewrites the block.

Run from the Mesa source root.
"""
import re
import sys

NAME = "51-fd722-duo.py"
SUMMARY = "FD722 num_ccu=1, tile_align_h=16, highest_bank_bit=15 (pinned)"

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"
EXPECT = (1, 16)        # (num_ccu, tile_align_h)
HBB = 15
ENFORCE = True          # False = rewrite the block to EXPECT instead of failing


def main():
    try:
        src = open(DEVICES_PY, encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {DEVICES_PY}: {e}; skipped")
        return 0

    m = re.search(r"GPUId\(chip_id=0x43020100.*?\n    \)\)", src, re.S)
    if not m:
        print(f"{NAME}: WARNING FD722 (0x43020100) block not found; skipped")
        return 0
    block = m.group(0)

    got = {}
    for key in ("num_ccu", "tile_align_h", "highest_bank_bit"):
        k = re.search(rf"\b{key}\s*=\s*(\d+)", block)
        got[key] = int(k.group(1)) if k else None
    # highest_bank_bit absent means A6xxGPUInfo's default, which is 15 today.
    print(f"{NAME}: upstream FD722 num_ccu={got['num_ccu']} "
          f"tile_align_h={got['tile_align_h']} "
          f"highest_bank_bit={got['highest_bank_bit'] if got['highest_bank_bit'] is not None else 'default'}")

    drift = (got["num_ccu"], got["tile_align_h"]) != EXPECT
    if drift and ENFORCE:
        print(f"{NAME}: ERROR FD722 moved off the tested config "
              f"{EXPECT[0]} CCU / tile_align_h {EXPECT[1]}; review before shipping",
              file=sys.stderr)
        return 1

    new = block
    if drift:
        new = re.sub(r"\bnum_ccu\s*=\s*\d+", f"num_ccu = {EXPECT[0]}", new)
        new = re.sub(r"\btile_align_h\s*=\s*\d+", f"tile_align_h = {EXPECT[1]}", new)
    if got["highest_bank_bit"] is None:
        if "raw_magic_regs" not in new:
            print(f"{NAME}: WARNING no raw_magic_regs anchor for highest_bank_bit; skipped")
            return 0
        new = new.replace("raw_magic_regs =",
                          f"highest_bank_bit = {HBB},\n        raw_magic_regs =", 1)
    else:
        new = re.sub(r"\bhighest_bank_bit\s*=\s*\d+", f"highest_bank_bit = {HBB}", new)

    if new == block:
        print(f"{NAME}: already applied")
        return 0
    open(DEVICES_PY, "w", encoding="utf-8").write(src.replace(block, new, 1))
    print(f"{NAME}: applied ({SUMMARY})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
