#!/usr/bin/env python3
"""Turnip: restore unconditional UCHE invalidate + WFI on SUBPASS_FENCE and backport August Mesa fixes.

1. On October Mesa (74920caaa0be), the September SUBPASS_FENCE series replaced
   TU_CMD_FLAG_CACHE_INVALIDATE + TU_CMD_FLAG_WAIT_FOR_IDLE on UCHE_READ_GMEM
   with TU_CMD_FLAG_CACHE_INVALIDATE_GMEM + TU_CMD_FLAG_SUBPASS_SLICE_FENCE,
   and wrapped FD_CACHE_INVALIDATE + WFI inside CP_COND_REG_EXEC(RENDER_MODE == SYSMEM).
   However, when tu_CmdBeginRenderPass2 emits tu_subpass_barrier(..., true) onto
   cmd->cs before tu6_sysmem_render_begin sets RM6_DIRECT_RENDER, RENDER_MODE is
   not SYSMEM yet, so CP_COND_REG_EXEC skips FD_CACHE_INVALIDATE + WFI and only
   emits FD_SUBPASS_FENCE (which only invalidates the GMEM aperture, leaving
   offscreen sysmem RTT textures like the Mario Kart 8 Deluxe 2D item roulette
   icon with stale UCHE lines). Restore unconditional FD_CACHE_INVALIDATE + WFI.
2. On August Mesa (24c8a889 / 5842099c), backport two upstream mesa-stable fixes:
   - c88b6ebd3: tu: Fix bindless descriptor invalidate sequence
   - 5cf8c6b2f: tu: Don't bail after the first instr when gathering push const range
"""
import pathlib
import sys

NAME = "25-tu-fix-subpass-fence-sysmem.py"
CMD_BUF = pathlib.Path("src/freedreno/vulkan/tu_cmd_buffer.cc")
SHADER = pathlib.Path("src/freedreno/vulkan/tu_shader.cc")

OLD_SUBPASS_FENCE = """   if (emit_subpass_slice_fence) {
      /* Emit the stronger flushes in sysmem mode. We need this from
       * experimentation.
       */
      tu_cond_exec_start(cs, CP_COND_REG_EXEC_0_MODE(RENDER_MODE) |
                             CP_COND_REG_EXEC_0_SYSMEM);
      if (emit_cache_invalidate_gmem)
         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_CACHE_INVALIDATE);
      if (emit_subpass_slice_wait)
         tu_cs_emit_wfi(cs);
      tu_cond_exec_end(cs);

      if (CHIP >= A8XX) {
         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_LABEL);
         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_SUBPASS_SLICE_FENCE);
         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_LABEL);
      } else {
         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_SUBPASS_FENCE);
      }
   }"""

NEW_SUBPASS_FENCE = """   if (emit_subpass_slice_fence) {
      if (emit_cache_invalidate_gmem)
         tu_emit_event_write<CHIP>(cmd_buffer, cs, FD_CACHE_INVALIDATE);
      if (emit_subpass_slice_wait)
         tu_cs_emit_wfi(cs);
   }"""

OLD_BINDLESS = """   if (flushes & TU_CMD_FLAG_BINDLESS_DESCRIPTOR_INVALIDATE) {
      tu_cs_emit_regs(cs, SP_UPDATE_CNTL(CHIP,
            .cs_bindless = CHIP == A6XX ? 0x1f : 0xff,
            .gfx_bindless = CHIP == A6XX ? 0x1f : 0xff,
      ));
   }"""

NEW_BINDLESS = """   if (flushes & TU_CMD_FLAG_BINDLESS_DESCRIPTOR_INVALIDATE) {
      if (CHIP < A8XX) {
         tu_cs_emit_regs(cs, SP_UPDATE_CNTL(CHIP,
               .cs_bindless = CHIP == A6XX ? 0x1f : 0xff,
               .gfx_bindless = CHIP == A6XX ? 0x1f : 0xff,
         ));
      }
      tu_cs_emit_regs(cs, A6XX_SP_CS_BINDLESS_INVALIDATE(1));
      tu_cs_emit_regs(cs, A6XX_SP_GFX_BINDLESS_INVALIDATE(1));
   }"""

OLD_PUSH_CONST = """            uint32_t base = nir_intrinsic_base(intrin);
            uint32_t range = nir_intrinsic_range(intrin);
            min = MIN2(min, base);
            max = MAX2(max, base + range);
            break;
         }"""

NEW_PUSH_CONST = """            uint32_t base = nir_intrinsic_base(intrin);
            uint32_t range = nir_intrinsic_range(intrin);
            min = MIN2(min, base);
            max = MAX2(max, base + range);
         }"""


def main():
    applied = []
    if CMD_BUF.exists():
        s = CMD_BUF.read_text(encoding="utf-8")
        orig = s
        if OLD_SUBPASS_FENCE in s:
            s = s.replace(OLD_SUBPASS_FENCE, NEW_SUBPASS_FENCE, 1)
            applied.append("unconditional FD_CACHE_INVALIDATE+WFI on subpass_slice_fence")
        if OLD_BINDLESS in s:
            s = s.replace(OLD_BINDLESS, NEW_BINDLESS, 1)
            applied.append("c88b6ebd3 bindless descriptor invalidate")
        if s != orig:
            CMD_BUF.write_text(s, encoding="utf-8", newline="\n")

    if SHADER.exists():
        s = SHADER.read_text(encoding="utf-8")
        if OLD_PUSH_CONST in s:
            s = s.replace(OLD_PUSH_CONST, NEW_PUSH_CONST, 1)
            SHADER.write_text(s, encoding="utf-8", newline="\n")
            applied.append("5cf8c6b2f gather_push_constants")

    if applied:
        print(f"{NAME}: applied ({', '.join(applied)})")
    else:
        print(f"{NAME}: already applied or not needed on this Mesa ref")
    return 0


if __name__ == "__main__":
    sys.exit(main())
