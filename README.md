# Turnip for Retroid Pocket Duo (Adreno 722 / Q-7790)

Turnip (Mesa Vulkan) builds tuned for the **Qualcomm Dragonwing Q-7790 (Adreno 722)** in the Retroid Pocket Duo.

## Upstream Mesa builds (GitHub Actions)
`.github/workflows/build-turnip.yml` builds upstream Mesa (default `70bd17c2`, 26.3.0-devel) for Android/KGSL and packages a `.adpkg.zip`.

* The A722 (`0x43020100`) entry is always edited (by `sed` in the workflow, so it applies at any Mesa commit) to the values of the clean T30 `--ccu2` build: `num_ccu = 2`, `tile_align_h = 32`, `highest_bank_bit = 16`, keeping `a730_raw_magic_regs`. Mirroring A720 (`a720_raw_magic_regs`, `highest_bank_bit = 15`) made the MK8 menu icons worse, so it was dropped. On KGSL, `highest_bank_bit` is read from the kernel, so the device-table value is only a fallback.
* `patches/a722-sysmem.patch` (`variant: sysmem` only): forces sysmem rendering on A722, like `TU_DEBUG=sysmem`. With `variant: autotune`, tu_autotune picks GMEM or sysmem per render pass.
* `pixel_center_interp` (default on): `patches/tu-no-force-sample-interp.patch`, see findings below. `stable_fixes` (default on): cherry-picks upstream mesa-stable `c88b6ebd3` (bindless descriptor invalidate) and `5cf8c6b2f` (push-constant range) from after `70bd17c2`.
* `tu_debug` (optional): `TU_DEBUG` flags baked in as the default (Android emulators can't set env vars), e.g. `noubwc` or `nolrz`. Package names carry the Mesa SHA and the flags.

## MK8 menu icon corruption (Eden) - findings
T30 `--ccu2` renders MK8 menu icons cleanly; upstream `70bd17c2` with the same A722 values flickers. Reversing T30 (`vulkan.purple.so`, private base `62ac221a33`, branded "PurpleVK" but still `VK_DRIVER_ID_MESA_TURNIP`, so Eden takes the same Turnip paths):

* A722 `fd_dev_info` header fields match (T30 `--ccu2` vs upstream v1.0.0).
* Effective magic regs match: T30's table lacks `RB_RBP_CNTL`/`RB_DBG_ECO_CNTL`, but its older code writes both from `magic.*` (= 0 for A722); upstream moved them into the table on 2026-10-02 (21d260a3, 396a186e) with the same values.
* The runtime overrides of `TPL1_DBG_ECO_CNTL`/`ECO_CNTL1`/`SP_CHICKEN_BITS` read the same prop values (TP UBWC flag hint, linear-mipmap threshold, EOLM all on).

A function-level diff of T30 against an unstripped upstream `5842099c` build (T30's base, ~2026-08-14, plus MR !42159 cherry-picked) finds only one private change that alters rendering on A722: T30 never sets `tu_shader_key::force_sample_interp`, while upstream forces per-sample interpolation of every non-centroid FS input whenever `sampleShadingEnable` is set. Eden's MSAA blits (`blit_color_msaa.frag`: `texelFetch(tex, ivec2(texcoord), gl_SampleID)`, sample shading 1.0) and its "Sample Shading" setting hit that path. `patches/tu-no-force-sample-interp.patch` matches T30. T30's other private changes (wave-size profiles, 3D-mipmap UBWC, extra GPU rows) are gated to A8xx/A740+ chip IDs and do not run on A722.

## Binary-patched T30 builds
`patch_t30_a722_sysmem.py` patches **MrPurple666's Turnip T30** (26.3.0-devel / Vulkan 1.4.359):

* **Variant A (`turnip_mrpurple_T30_a722_sysmem.adpkg.zip`):** 1-byte patch (`0x943c6e: 0 -> 1`, `disable_gmem` in the Adreno 722 `fd_dev_info` struct) that forces sysmem rendering on Adreno 722 without needing `TU_DEBUG=sysmem`.
* **Variant B (`turnip_mrpurple_T30_a722_ccu2_sysmem.adpkg.zip`, `--ccu2`):** Variant A plus `num_ccu` (+0x44) 1 -> 2, `tile_align_h` (+0x08) 16 -> 32 and `highest_bank_bit` (+0x28) 15 -> 16. Upstream A720 uses `highest_bank_bit = 15`; on KGSL the kernel value is used anyway.
