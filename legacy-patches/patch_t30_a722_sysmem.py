#!/usr/bin/env python3
"""Patch MrPurple Turnip T30 so Adreno 722 (chip_id 0x43020100) defaults to sysmem rendering.

Mechanism (found by reversing T30 vulkan.purple.so):
  * fd_dev_info table: 32-byte rows {u32 gpu_id, u32 pad, u64 chip_id, char *name, fd_dev_info *info}.
    Pointers are R_AARCH64_RELATIVE relocations, so info vaddrs are read from .rela.dyn.
  * struct fd_dev_info is 0x320 bytes in T30; the byte at +0x316 is `disable_gmem`.
  * use_sysmem_rendering() copies the struct into the physical device (pdev+0x1d90) and tests
    pdev+0x20a6 bit0; if set it returns true with reason "Unsupported GPU" -> sysmem path.
  Setting disable_gmem=1 in the A722 info struct == TU_DEBUG=sysmem, but only for A722.

Only stdlib is used. Usage:
  python patch_t30_a722_sysmem.py T30/vulkan.purple.so out_dir [--meta T30/meta.json]
Produces out_dir/turnip_mrpurple_T30_a722_sysmem.adpkg.zip
"""
import argparse, hashlib, json, os, struct, sys, zipfile

T30_SHA256 = "1d80dfa019659b008e4669311db5b1e4a02af59ff1d5458a98e2f5fe18ed013b"
CHIP_IDS = (0x43020100, 0xFFFF43020100)       # Adreno 722 (exact + patch-wildcard rows)
INFO_SIZE = 0x320
DISABLE_GMEM_OFF = 0x316                       # T30 layout (T29 layout: 0x314, size 0x31c)
OUT_NAME = "turnip_mrpurple_T30_a722_sysmem.adpkg.zip"


def parse_elf(d):
    if d[:4] != b"\x7fELF" or d[4] != 2 or struct.unpack_from("<H", d, 18)[0] != 183:
        sys.exit("not an ELF64 AArch64 file")
    phoff, shoff = struct.unpack_from("<QQ", d, 32)[0], struct.unpack_from("<Q", d, 40)[0]
    phentsize, phnum = struct.unpack_from("<HH", d, 54)
    shentsize, shnum = struct.unpack_from("<HH", d, 58)
    loads = []
    for i in range(phnum):
        t, _, off, va, _, fsz, _, _ = struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize)
        if t == 1:
            loads.append((va, off, fsz))
    rela = {}
    for i in range(shnum):
        _, st, _, _, off, size, _, _, _, _ = struct.unpack_from("<IIQQQQIIQQ", d, shoff + i * shentsize)
        if st == 4:  # SHT_RELA
            for o in range(off, off + size, 24):
                r_off, r_info, r_add = struct.unpack_from("<QQq", d, o)
                if r_info & 0xFFFFFFFF == 1027:  # R_AARCH64_RELATIVE
                    rela[r_off] = r_add
    return loads, rela


def v2o(loads, va):
    for lva, off, fsz in loads:
        if lva <= va < lva + fsz:
            return va - lva + off
    raise ValueError(hex(va))


def o2v(loads, o):
    for lva, off, fsz in loads:
        if off <= o < off + fsz:
            return o - off + lva
    raise ValueError(hex(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("so")
    ap.add_argument("out_dir")
    ap.add_argument("--meta")
    ap.add_argument("--ccu2", action="store_true",
                    help="Variant B: also set A722 +0x44=2, +0x08=32, +0x28=16 (A720 values)")
    ap.add_argument("--force", action="store_true", help="skip the T30 sha256 check")
    a = ap.parse_args()

    d = bytearray(open(a.so, "rb").read())
    sha = hashlib.sha256(d).hexdigest()
    if sha != T30_SHA256 and not a.force:
        sys.exit(f"sha256 {sha} is not the known T30 build; layout offsets may differ (use --force)")

    loads, rela = parse_elf(bytes(d))
    infos, rows = set(), []
    # scan every 8-aligned qword for a chip_id row; validate with a RELATIVE reloc at +24
    for o in range(0, len(d) - 32, 8):
        if struct.unpack_from("<Q", d, o + 8)[0] in CHIP_IDS:
            try:
                va = o2v(loads, o)
            except ValueError:
                continue
            if va + 24 in rela and va + 16 in rela:
                name_o = v2o(loads, rela[va + 16])
                name = bytes(d[name_o:d.index(b"\0", name_o)])
                rows.append((o, hex(struct.unpack_from("<Q", d, o + 8)[0]), name))
                infos.add(rela[va + 24])
    if not rows or len(infos) != 1:
        sys.exit(f"expected exactly one shared info struct for A722, got rows={rows} infos={infos}")
    info_va = infos.pop()
    info_o = v2o(loads, info_va)
    print("A722 rows:", [(hex(o), c, n.decode()) for o, c, n in rows])
    print(f"info struct vaddr {info_va:#x} file offset {info_o:#x}")

    w = struct.unpack_from("<I", d, info_o)[0]
    if w != 7 or d[info_o + 0x314:info_o + 0x316] != b"\x01\x01":
        sys.exit("info struct does not match the expected T30 layout")
    p = info_o + DISABLE_GMEM_OFF
    if d[p] == 1:
        print("already patched")
    else:
        assert d[p] == 0
        d[p] = 1
        print(f"patched byte at file offset {p:#x}: 00 -> 01 (disable_gmem)")

    out_name, tag, note = OUT_NAME, "A722-sysmem", "Adreno 722 defaults to sysmem rendering."
    if a.ccu2:
        for off, old, new in ((0x44, 1, 2), (0x08, 16, 32), (0x28, 15, 16)):
            q = info_o + off
            cur = struct.unpack_from("<I", d, q)[0]
            if cur != old:
                sys.exit(f"info+{off:#x} is {cur}, expected T30 value {old}")
            struct.pack_into("<I", d, q, new)
            print(f"patched info+{off:#x} (file {q:#x}): {old} -> {new}")
        out_name, tag = "turnip_mrpurple_T30_a722_ccu2_sysmem.adpkg.zip", "A722-ccu2-sysmem"
        note = "Adreno 722 uses A720 tile/CCU values (+0x44=2) and defaults to sysmem rendering."

    os.makedirs(a.out_dir, exist_ok=True)
    meta_path = a.meta or os.path.join(os.path.dirname(os.path.abspath(a.so)), "meta.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    meta["name"] = meta["name"].replace("T30", f"T30 {tag}", 1)
    meta["description"] = meta["description"].rstrip(". ") + ". Patched: " + note
    out = os.path.join(a.out_dir, out_name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("meta.json", json.dumps(meta, indent=2))
        z.writestr(meta["libraryName"], bytes(d))
    print("wrote", out)


if __name__ == "__main__":
    main()
