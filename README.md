# Turnip Duo v5.1 (4.4-exp stack + A722 calibration)

vauzi's Turnip 4.4-exp patch set, pinned and built for the **Retroid Pocket Duo
(Qualcomm Dragonwing Q-7790, Adreno 722)**.

4.4-exp is the fast, stable one: it stops at `50-fd720-blob.py` and does not
carry the 60-series patches that came after it.

* **Mesa**: pinned to `74920caaa0bed55313e7af00036c61515621913b` (Mesa 27.0.0-devel, 2026-10-17).
* **Patches**: `patches/` is vauzi's tree at [`93ec337`](https://github.com/Vauzi-17/710/commit/93ec337) on the `sw` branch — the newest commit whose patch set matches the 4.4-exp release notes exactly.
* **v5.1**: the full 4.4-exp patch set, exactly as vauzi shipped it, with one
  Duo-specific addition. The 4.4.1-5.0 experiments are all reverted: patch 02
  is on, patch 09 is on, the Turnip-Z set (30-37) is on, and
  `default_env.conf` has no active entries. `TU_DEBUG=sysmem` is deliberately
  **not** baked in - on this device it corrupts UBWC swapchain strides
  (purple/black vertical lines, GPU hangs). Patch 36 forces sysmem through its
  own path instead, which is what the known-good build used.
* **Duo-specific**: `patches/51-fd722-duo.py` pins FD722 to `num_ccu = 1`,
  `tile_align_h = 16`, `highest_bank_bit = 15` — upstream's own values, which
  is what gave 60 FPS docked — and rewrites `cs_shared_mem_size` to 32 KiB. It
  asserts the first two rather than editing them, and fails the build if
  upstream ever moves them.
* Nothing in vauzi's set targets FD722: `40`–`46` are anchored to FD710, `50`
  to FD720, `14` to FD740 / X1-85. The Duo otherwise runs upstream config.

## Building

Actions → **Turnip Duo v4.4-exp (Duo Edition)** → Run workflow. The defaults
are the pinned Mesa commit and version `4.4-exp`; output is
`Turnip-Duo-v4.4-exp.zip` (AdrenoTools).

Recommended at runtime: `TU_DEBUG=sysmem`.

The older hand-rolled workflows (`build-turnip.yml`, `release-duo-v1.yml`,
`bisect-builds.yml`) and their patches in `legacy-patches/` are untouched and
still work; vauzi's builder only reads `patches/`.

---

# Turnip for Retroid Pocket Duo (Adreno 722 / Q-7790)

Custom Mesa Turnip Vulkan graphic drivers optimized for the **Qualcomm Dragonwing Q-7790 (Adreno 722)** in the Retroid Pocket Duo.

---

## 🌟 Recommended Driver (Start Here!)

For 99% of users, download the **T30 CCU2 Autotune** driver from the [Releases Page](https://github.com/sherft2607/turnip-adreno722-duo/releases):

* **`turnip_mrpurple_T30_a722_ccu2_autotune.adpkg.zip`** (Recommended)
  * **Status:** Rock-solid stability. Zero visual glitches or crashes.
  * **Performance:** 
    * **Wind Waker HD (Cemu):** Stable 29–30 FPS @ 720p.
    * **Mario Kart 8 Deluxe (Eden):** ~50 FPS average (+5 FPS over stock driver).
    * **Azahar (3DS):** Smooth dual-screen rendering with fast on-chip memory enabled.
  * **What it does:** Unlocks both GPU cores (`num_ccu = 2`, `tile_align_h = 32`) on MrPurple's battle-tested T30 Turnip base and enables fast on-chip GPU memory (`autotune`).

* **`turnip_mrpurple_T30_a722_ccu2_sysmem.adpkg.zip`** (Safe Fallback)
  * Same 2-core fix as above, but routes rendering through system memory (`sysmem`) if any heavy game overloads GMEM.

---

## 🧪 Experimental Upstream Builds (High FPS, Known UI Glitches)

Automated builds compiled directly from upstream Mesa (`src/freedreno` / Turnip) using `.github/workflows/build-turnip.yml`.

> [!WARNING]
> Upstream Mesa delivers **~10% higher in-game FPS** (e.g. 55 FPS average in MK8 Deluxe), but currently suffers from **flickering / disappearing 2D menu and UI icons** in emulators like Eden. Use the T30 driver above for normal gameplay.

* **Upstream Autotune:** Builds Mesa from source with the A722 2-core patch applied (`num_ccu = 2`, `tile_align_h = 32`, `highest_bank_bit = 16`).
* **`tu_debug` options:** Diagnostic builds (`noubwc`, `nolrz`) are available under releases to help isolate upstream driver bugs.

---

## How to Install in Emulators

1. Download the `.adpkg.zip` file (do not unzip it).
2. Open your emulator (**Eden**, **Cemu**, or **Azahar**).
3. Go to **Settings** → **GPU / Graphics Driver Manager**.
4. Tap **Install / Add** and select the `.adpkg.zip` file.
5. Select the driver from the list.
