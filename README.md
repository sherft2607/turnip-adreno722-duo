# Turnip Vulkan Driver for Retroid Pocket Duo (Adreno 722)

Custom, hardware-verified Mesa Freedreno (Turnip) Vulkan driver engineered specifically for the **Retroid Pocket Duo** (Qualcomm Adreno 722 GPU).

---

## 🎯 Target Hardware & Identity

* **Device:** Retroid Pocket Duo
* **Chipset:** Qualcomm Dragonwing Q7790 (`CQ7790S`)
* **Platform / SoC ID:** `sun` / SoC ID `732` (Codename `kera`)
* **GPU Model:** `Qualcomm Adreno (TM) 722`
* **GPU Chip ID:** `0x43020100` (`1124204800`)
* **Kernel Driver:** `msm_kgsl` (`adreno_gpu_core_gen7_17_0`, `gpurev 0x00071100`)
* **Operating System:** Android 16 (API Level 36)

---

## 🔬 Hardware Ground Truth

Parameters dumped from physical Retroid Pocket Duo hardware over ADB: the kernel
device tree, `msm_kgsl.ko`, the vendor blobs and `stock_vkjson.json`. The last
column says where each value comes from, because not all of them are readable
off the hardware.

| Hardware Parameter | Value | Source |
|---|---|---|
| **On-Chip GMEM** | `1 MiB` (`0x100000`) | Kernel core struct; Turnip reads it from KGSL at runtime |
| **Highest Bank Bit** | `15` (`0xf`) | Device tree, cross-checked against the kernel's `RB_NC_MODE_CNTL = 0x814` (bits 2:1 = hbb − 13). Also upstream Mesa's default, so this is locked rather than changed |
| **Compute Shared Memory** | `32 KiB` (`32768`) | OEM blob reports `maxComputeSharedMemorySize = 32768`. Locked back down after patch 18 raises every device to 64 KiB |
| **Wave / Subgroup Size** | `64` | OEM blob reports `subgroupSize = 64` with no smaller size |
| **CCU Count** | `num_ccu = 1`, `tile_align_h = 16` | **[INFERENCE]** Not exposed by the kernel. Upstream Mesa's own FD722 values, independently matched by vauzi's blob-trace analysis in patch 56 |
| **Async Compute (LPAC)** | Disabled | Blob-trace analysis (patch 56): `GPUProps(has_lpac = False)`, overriding `a7xx_base` |
| **UBWC** | Mode 4.0, 32-byte min access length | Device tree (`qcom,ubwc-mode = 4`, `qcom,min-access-length = 0x20`) |
| **Magic Registers** | Standalone `a722_raw_magic_regs` | 37-entry table from 116 Qualcomm blob cmdstream traces, correcting 12 values that upstream inherited from A730 |

### Note on subgroup size

The blob reports a single subgroup size of 64. This build has
`09-tu-ir3-subgroup-half-warp.patch` **active**, which advertises
`minSubgroupSize = 32` and lowers `WaveSize(32)` compute shaders onto half
waves. It is in the build because it was part of the configuration measured at
60 FPS with no crashes. To match the blob exactly, rename it to
`09-tu-ir3-subgroup-half-warp.patch.off` and `minSubgroupSize` returns to 64.

---

## ⚡ Performance & Compatibility

### 1. Eden (Nintendo Switch)
* **Mario Kart 8 Deluxe:** locked **55–60 FPS at 1080p docked**, solid 60 FPS at 720p handheld.
* **Display pipeline:** Android 16 **IMapper5 stable-C SP-HAL** gralloc backend (patch 15), which removes the 30 FPS swapchain cap.
* **Clocks:** patch 17 disables the KGSL governor through `KGSL_PROP_PWRCTRL` while any queue is alive and restores it on close, so the GPU holds its top frequency during emulation instead of being clocked down.
* **2D HUD icons:** fixed by patch 58. Upstream Turnip sets `force_sample_interp` whenever a pipeline enables sample shading, so every non-centroid fragment input is evaluated at its sample position. Eden's MSAA blit shader (`texelFetch(tex, ivec2(texcoord), gl_SampleID)` with `minSampleShading 1.0`) then fetches a different source texel per sample when the blit is scaled, and the 2D icons vanish. MrPurple's T30 never sets the flag; patch 58 does the same.

### 2. Cemu (Nintendo Wii U)
* **The Legend of Zelda: The Wind Waker HD:** clean rendering at a locked **30 FPS**.

### 3. Winlator (PC compatibility)
* The builder has a glibc target, but this fork ships no `patches/glibc/`, so the
  Winlator X11 WSI patches are not applied. Untested here; use vauzi's upstream
  builds for Winlator.

---

## 🏗️ Architecture & Patch Stack

Built on upstream **Mesa 27.0.0-devel**, pinned to commit
[`74920caaa0be`](https://gitlab.freedesktop.org/mesa/mesa/-/commit/74920caaa0bed55313e7af00036c61515621913b),
with **Android NDK r29** targeting **Platform SDK 36**.

`patches/` is vauzi's 4.4-exp set, taken from
[`93ec337`](https://github.com/Vauzi-17/710/commit/93ec337) on the `sw` branch —
the newest commit whose patch list matches the 4.4-exp release notes exactly.
4.4-exp stops at `50-fd720-blob.py` and carries none of the later 60-series
patches.

* **Patches 01 & 15:** `u_gralloc` UBWC detection and the Android 16 IMapper5 SP-HAL loader.
* **Patch 02:** LRZ state reuse for `LOAD_OP_DONT_CARE` depth attachments. Gated on `TU_DEBUG(SYSMEM)`; nothing in this build sets that flag, so it is currently dormant.
* **Patch 16:** UBWC-compressed swapchain framebuffers.
* **Patch 17:** KGSL governor lock (`KGSL_PROP_PWRCTRL`) plus an autotune bandwidth tweak.
* **Patches 30–37:** Turnip-Z engine — mutable-format UBWC, cheaper sampling, forced sysmem rendering. (`34` and `35` ship disabled, as upstream.)
* **Patches 40–46, 50:** FD710 and FD720 tuning. Anchored to those GPUs by name; they do not touch FD722.
* **Patch 56 (`56-fd722-blob.py`):** standalone Adreno 722 magic registers and `has_lpac = False`, from vauzi's blob analysis. Replaces the whole FD722 device entry.
* **Patch 58 (`58-tu-no-force-sample-interp.patch`):** never set `force_sample_interp`, matching MrPurple T30. Fixes the missing 2D HUD icons in Eden.
* **Patch 57 (`57-fd722-duo.py`):** Duo hardware enforcement — `highest_bank_bit = 15`, `cs_shared_mem_size = 32 KiB`, and asserts `num_ccu = 1` / `tile_align_h = 16`. Numbered 57 so it runs after 56 and has the final word; it fails the build rather than shipping drifted values.

Anything renamed `.off` in `patches/` is disabled but kept, and re-enabled by
dropping the suffix.

---

## 🚀 How to Build & Install

1. Go to the **Actions** tab of this repository.
2. Select **Turnip Duo v5.2 (Fix MK8 Icons via tu-no-force-sample-interp)**.
3. Click **Run workflow** on branch `main`. The defaults are the pinned Mesa commit and version `5.2`.
4. When it finishes, download **`Turnip-Duo-v5.2.zip`** from the run's artifacts.
5. In your emulator (Eden, Cemu, …), open the GPU driver manager and install the `.adpkg.zip`.

---

## ⚙️ Recommended Device Settings

* **Retroid Pocket Duo OS:** Performance Mode set to **Performance / Extreme**, Fan Mode to **Sport / Smart**, to avoid thermal throttling.
* **Eden:** Graphics Accuracy **Normal**, VSync **Mailbox / FIFO Relaxed**, **Asynchronous ASTC Texture Decoding** enabled.

---

## Credits

Patch set by [vauzi](https://github.com/Vauzi-17/710). Turnip and Mesa are the
work of the Mesa community. Duo-specific calibration and hardware verification
by sherft2607, on physical Retroid Pocket Duo hardware.
