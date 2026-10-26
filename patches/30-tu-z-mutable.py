#!/usr/bin/env python3
"""Turnip-Z port: safe mutable-format image handling for Adreno 722 (FD722).

On Android 16 with 15-wn-add-aimapper-gralloc.py and 16-wn-add-ubwc-swapchain-usage.py,
swapchain AHardwareBuffers arrive in tu_image_init() with:
  - pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT
  - fmt_list == NULL
  - modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED

In upstream Mesa, when !mutable_ubwc_fc (A710/A720/A722), fmt_list_has_swaps is true
when fmt_list is NULL, setting force_linear_tile = true -> tile_mode = TILE6_LINEAR.
Then at `if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED)`, assert(!force_linear_tile)
is compiled out in release builds (-DNDEBUG) and ubwc_enabled = true is set while
tile_mode remains TILE6_LINEAR. That illegal TILE6_LINEAR + UBWC combination causes
the purple vertical lines and GPU hang seen whenever 30-tu-z-mutable.py was disabled
or TU_Z_MUTABLE=0 was set.

Conversely, Vauzi's original 30-tu-z-mutable.py (TU_Z_MUTABLE=2) forced ALL mutable
images in the game to stay TILE6_3 + UBWC even when format_list_ubwc_possible() was
false or when views mixed incompatible UBWC formats or swapped formats without
setting is_mutable = true (MUTABLEEN), causing Mario Kart 8 Deluxe's in-race item
roulette icon to render blank.

This patch fixes both:
1. When modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED, force_linear_tile is cleared and
   tile_mode = TILE6_3 is enforced so UBWC swapchains never become TILE6_LINEAR.
2. For mutable images on !mutable_ubwc_fc:
   - TU_Z_MUTABLE=1 (default):
     * UBWC is kept ONLY when format_list_ubwc_possible(device, fmt_list, pCreateInfo)
       is true (all listed view formats are UBWC-capable) or modifier is QCOM_COMPRESSED.
     * When fmt_list_has_swaps is true (and not r8g8_r16), the image stays tiled
       (TILE6_3) and sets `is_mutable = true` so fdl6_view_init sets A6XX_TEX_MEMOBJ_1_MUTABLEEN
       and uses each view's native color swap on A7xx hardware.
   - TU_Z_MUTABLE=0:
     * Full upstream linear fallback for non-QCOM_COMPRESSED mutable images with swaps,
       while still protecting DRM_FORMAT_MOD_QCOM_COMPRESSED swapchains from TILE6_LINEAR.
   - TU_Z_MUTABLE=2:
     * Legacy Turnip-Z behavior (keep UBWC on all mutable images) plus is_mutable = true.

Run from the Mesa source root. All edits are applied or none.
"""
import sys

NAME = "30-tu-z-mutable.py"
MARKER = "TU_Z_MUTABLE"
IMAGE = "src/freedreno/vulkan/tu_image.cc"

EDITS = [
    (IMAGE,
     '#include "tu_wsi.h"\n',
     '#include "tu_wsi.h"\n'
     '\n'
     'DEBUG_GET_ONCE_NUM_OPTION(tu_z_mutable, "TU_Z_MUTABLE", 1)\n'
     'DEBUG_GET_ONCE_BOOL_OPTION(tu_z_mutable_swap, "TU_Z_MUTABLE_SWAP", true)\n',
     1),
    (IMAGE,
     '         } else if (!mutable_ubwc_fc) {\n'
     '            if (ubwc_enabled) {\n',
     '         } else if (!mutable_ubwc_fc) {\n'
     '            int64_t z_mutable = debug_get_option_tu_z_mutable();\n'
     '            bool keep_ubwc = (z_mutable >= 2) ||\n'
     '               (z_mutable >= 1 && format_list_ubwc_possible(device, fmt_list, pCreateInfo));\n'
     '            if (ubwc_enabled && !keep_ubwc) {\n',
     1),
    (IMAGE,
     '            if (r8g8_r16 || fmt_list_has_swaps) {\n'
     '               ubwc_enabled = false;\n'
     '               force_linear_tile = true;\n'
     '            }\n',
     '            if (r8g8_r16 ||\n'
     '                (fmt_list_has_swaps && z_mutable < 1 &&\n'
     '                 modifier != DRM_FORMAT_MOD_QCOM_COMPRESSED)) {\n'
     '               ubwc_enabled = false;\n'
     '               force_linear_tile = true;\n'
     '            } else if (fmt_list_has_swaps &&\n'
     '                       device->physical_device->info->chip >= 7 &&\n'
     '                       debug_get_option_tu_z_mutable_swap()) {\n'
     '               is_mutable = true;\n'
     '            }\n',
     1),
    (IMAGE,
     '   if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {\n'
     '      assert(!force_linear_tile);\n'
     '      ubwc_enabled = true;\n'
     '      force_ubwc = true;\n'
     '   }\n',
     '   if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {\n'
     '      force_linear_tile = false;\n'
     '      tile_mode = TILE6_3;\n'
     '      ubwc_enabled = true;\n'
     '      force_ubwc = true;\n'
     '   }\n',
     1),
]


def main():
    files = {}
    for path, _, _, _ in EDITS:
        if path not in files:
            try:
                files[path] = open(path, encoding="utf-8").read()
            except OSError as e:
                print(f"{NAME}: WARNING cannot read {path}: {e}; skipped")
                return 0
    if any(MARKER in s for s in files.values()):
        print(f"{NAME}: already applied")
        return 0
    for path, old, new, count in EDITS:
        found = files[path].count(old)
        if found != count:
            print(f"{NAME}: WARNING anchor matched {found}x (want {count}) in {path}; "
                  f"upstream changed, patch skipped")
            return 0
        files[path] = files[path].replace(old, new)
    for path, s in files.items():
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(s)
    print(f"{NAME}: applied (TU_Z_MUTABLE default 1, TU_Z_MUTABLE_SWAP default true, QCOM_COMPRESSED tile guard)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
