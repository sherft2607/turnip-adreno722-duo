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
