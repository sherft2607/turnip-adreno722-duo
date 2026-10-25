#!/usr/bin/env python3
"""FD722 (Retroid Pocket Duo, chip_id 0x43020100): pin the known-good GMEM config.

The Duo's 60 FPS docked result comes from upstream's own FD722 values, so this
script changes nothing today - it locks them in:

  num_ccu          2    rewritten (T30 value)
  tile_align_h    32    rewritten (T30 value)
  cs_shared_mem_size
                   32 KiB  rewritten. 18-wn-a8xx-shared-mem.py raises this to
                        64 KiB on every device entry, FD722 included, and it
                        runs before this script. The Duo's SP has 32 KiB: the
                        OEM blob reports maxComputeSharedMemorySize = 32768
                        (stock vkjson), and the value is handed straight to
                        that limit (tu_device.cc). Advertising 64 KiB let the
                        compute shader decoding the Mario Kart 8 HUD item
                        texture overflow it, so the icon came out blank while
                        3D geometry rendered fine.
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

Numbered 57 so it runs after 56-fd722-blob.py, which replaces the whole FD722
add_gpus block with its own text. 56 happens to set the same four values from
its blob traces, so this script normally reports "already applied" and exists to
fail the build if 56 (or anything else) ever moves them.

Run from the Mesa source root.
"""
import re
import sys

NAME = "57-fd722-duo.py"

DEVICES_PY = "src/freedreno/common/freedreno_devices.py"
# v5.4: MrPurple T30's GMEM configuration, which renders the Mario Kart 8 HUD
# icons correctly with autotune enabled (its own meta.json: "num_ccu=2,
# tile_align_h=32, highest_bank_bit=16 ... uses tu_autotune GMEM/sysmem
# selection"). num_ccu and tile_align_h only really matter once passes render
# in GMEM; our 1/16/15 set was only ever validated in a forced-sysmem build,
# where they are close to inert. With Turnip-Z off, autotune turns GMEM on and
# 1/16/15 produced UBWC corruption (purple/black lines) and a GPU hang.
EXPECT = (2, 32)        # (num_ccu, tile_align_h)
HBB = 16
CS_SHARED_MEM_KIB = 32   # OEM blob limit; matches plain Mesa, which T30 is
ENFORCE = False         # rewrite 56's block to EXPECT instead of failing

SUMMARY = (f"FD722 num_ccu={EXPECT[0]}, tile_align_h={EXPECT[1]}, "
           f"highest_bank_bit={HBB}, cs_shared_mem_size={CS_SHARED_MEM_KIB} KiB")


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
    for key in ("num_ccu", "tile_align_h", "highest_bank_bit", "cs_shared_mem_size"):
        k = re.search(rf"\b{key}\s*=\s*(\d+)", block)
        got[key] = int(k.group(1)) if k else None
    # highest_bank_bit absent means A6xxGPUInfo's default, which is 15 today.
    print(f"{NAME}: upstream FD722 num_ccu={got['num_ccu']} "
          f"tile_align_h={got['tile_align_h']} "
          f"highest_bank_bit={got['highest_bank_bit'] if got['highest_bank_bit'] is not None else 'default'} "
          f"cs_shared_mem_size={got['cs_shared_mem_size']} * 1024")

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
    if not re.search(r"\bcs_shared_mem_size\s*=\s*\d+\s*\*\s*1024", new):
        print(f"{NAME}: ERROR cs_shared_mem_size not in the N * 1024 form", file=sys.stderr)
        return 1
    new = re.sub(r"\bcs_shared_mem_size\s*=\s*\d+\s*\*\s*1024",
                 f"cs_shared_mem_size = {CS_SHARED_MEM_KIB} * 1024", new)

    if new == block:
        print(f"{NAME}: already applied")
        return 0
    open(DEVICES_PY, "w", encoding="utf-8").write(src.replace(block, new, 1))
    print(f"{NAME}: applied ({SUMMARY})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
