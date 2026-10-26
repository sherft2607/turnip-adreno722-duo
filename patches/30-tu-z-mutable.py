#!/usr/bin/env python3
"""Protect DRM_FORMAT_MOD_QCOM_COMPRESSED swapchain images from TILE6_LINEAR in tu_image_init.

On Android 16 with 15-wn-add-aimapper-gralloc.py and 16-wn-add-ubwc-swapchain-usage.py,
swapchain AHardwareBuffers arrive in tu_image_init() with:
  - pCreateInfo->flags & VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT
  - fmt_list == NULL
  - modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED

In upstream Mesa, when !mutable_ubwc_fc (A710/A720/A722), fmt_list_has_swaps is true
when fmt_list is NULL, setting force_linear_tile = true -> tile_mode = TILE6_LINEAR.
Then at `if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED)`, assert(!force_linear_tile)
is compiled out in release builds (-DNDEBUG) and ubwc_enabled = true is set while
tile_mode remains TILE6_LINEAR, corrupting the swapchain with purple vertical lines.

This patch leaves 100% of game-internal VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT handling untouched
(pure upstream Mesa behavior, identical to T30 / build-0 where the Mario Kart 8 Deluxe item
roulette icon renders properly), and ONLY ensures that when modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED,
force_linear_tile is cleared and tile_mode = TILE6_3 is restored.
"""
import sys

NAME = "30-tu-z-mutable.py"
IMAGE = "src/freedreno/vulkan/tu_image.cc"

OLD = (
    '   if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {\n'
    '      assert(!force_linear_tile);\n'
    '      ubwc_enabled = true;\n'
    '      force_ubwc = true;\n'
    '   }\n'
)

NEW = (
    '   if (modifier == DRM_FORMAT_MOD_QCOM_COMPRESSED) {\n'
    '      force_linear_tile = false;\n'
    '      tile_mode = TILE6_3;\n'
    '      ubwc_enabled = true;\n'
    '      force_ubwc = true;\n'
    '   }\n'
)


def main():
    try:
        s = open(IMAGE, encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {IMAGE}: {e}; skipped")
        return 0

    if NEW in s:
        print(f"{NAME}: already applied")
        return 0

    if s.count(OLD) != 1:
        print(f"{NAME}: WARNING anchor matched {s.count(OLD)}x in {IMAGE}; skipped")
        return 0

    s = s.replace(OLD, NEW, 1)
    with open(IMAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)

    print(f"{NAME}: applied (pure upstream mutable handling + QCOM_COMPRESSED TILE6_3 guard)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
