/*
 * Asimov SCP Firmware
 * Copyright (c) 2025, Positron AI. All rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Description:
 *     Asimov System Support — platform boot orchestrator.
 *
 *     This module implements the system_power driver API and orchestrates
 *     the AP boot sequence:
 *       1. In mod_init, programs RVBAR for all DSUs via cmn_cfg_mgmt
 *          RVBAR slots, programs each DSU peripheral-port range 0 for the
 *          FSR, DSU0's ACP bases and the ACP publisher enable, the common
 *          DSU broadcast policy and the resetless XMS configuration chain,
 *          then writes RESET_CTRL_BOOT_HOLD_MASK to release every block
 *          except the two PCIe controller subsystems, then loads the SPM
 *          chain. These strap writes precede reset release because the
 *          clusters sample them at nSRESET deassert.
 *       2. In the start-phase event handler, calls power-domain
 *          restricted API to power on the primary core; the framework
 *          cascades SYSTOP -> cluster -> core PPUs.
 *
 *     mod_clock / mod_pik_clock are no longer used on Asimov — system
 *     clocks are externally fixed (no on-die clock-control surface).
 *     mod_cmn_cyprus.config_cmn_cyprus.clock_id is set to FWK_ID_NONE,
 *     so CMN setup runs immediately during start() without waiting for
 *     a clock-notification handshake.
 */

#include "asimov_acp.h"
#include "asimov_cfg_chains.h"
#include "asimov_cmn_dvm.h"
#include "asimov_cmn_mesh_qos.h"
#include "asimov_dsu_policy.h"
#include "asimov_cmn_ready.h"
#include "asimov_clk_provider.h"
#include "asimov_cti_handler.h"
#include "asimov_hemi_id.h"
#include "asimov_pll_query.h"
#include "asimov_ras_handler.h"
#include "asimov_reset_ctrl.h"
#include "cmn_node_id.h"
#include "platform_core.h"
#include "scp_mmap.h"
#include "asimov_endpoint_map.h"

#include <mod_asimov_system.h>
#include <mod_power_domain.h>
#include <mod_system_power.h>

#include <fwk_core.h>
#include <fwk_event.h>
#include <fwk_id.h>
#include <fwk_log.h>
#include <fwk_macros.h>
#include <fwk_module.h>
#include <fwk_module_idx.h>
#include <fwk_notification.h>
#include <fwk_status.h>

#include <fmw_cmsis.h>

#include <stdbool.h>
#include <stdint.h>
#include <asimov_boot_layout.h>
#include <asimov_system_map.h>

/*
 * AP entry point address.
 * TODO(asimov): In production this will come from the host via PCIe.
 * For now, use the shared BL31 boot allocation.
 */
#define AP_RVBAR_ADDR ASIMOV_BL31_BASE

/*
 * DSU peripheral-port (P0) route to the CMN Fast Status Registers.
 *
 * SAMv2 assigns the FSR leaf to PA 0xB8_0000_0000. P0 range 0 compares
 * PA[39:20] with an exclusive end, so start=0xB8000/end=0xB8001 selects the
 * containing 1 MiB envelope on every DSU. Equal endpoints disable the range.
 * Linux exposes only the implemented low 64 KiB register view; the wider
 * envelope is a hardware routing granule, not additional FSR storage.
 *
 * The integrated range comparator uses the C1-DSU TRM's exclusive-AEND0
 * semantics (some cfg_mgmt collateral incorrectly describes equality as a
 * 1 MiB match). On DSU reset release, the P0 FSR adapter samples the same
 * ASTART0 field as C1 range 0, accepts its low 128 KiB, and applies the local
 * 17-bit decode. Keep ASTART0/AEND0 immutable afterward; a later cfg_mgmt
 * write stages the next reset cycle for both captured decoders.
 */
#define ASIMOV_DSU_P0_FSR_BASE          ASIMOV_SAM_DSU_PP_FSR_BASE
#define ASIMOV_DSU_P0_FSR_ROUTE_SIZE \
    (UINT64_C(1) << CMN_CFG_MGMT_P0_RANGE0_ADDR_SHIFT)
#define ASIMOV_DSU_P0_FSR_WINDOW        0U
#define ASIMOV_DSU_P0_FSR_START_VALUE \
    ((uint32_t)(ASIMOV_DSU_P0_FSR_BASE >> \
                CMN_CFG_MGMT_P0_RANGE0_ADDR_SHIFT))
#define ASIMOV_DSU_P0_FSR_END_VALUE \
    (ASIMOV_DSU_P0_FSR_START_VALUE + 1U)

#if ((ASIMOV_DSU_P0_FSR_BASE & (ASIMOV_DSU_P0_FSR_ROUTE_SIZE - 1U)) != 0U)
#    error "DSU P0 FSR base must be aligned to the 1 MiB route granule"
#endif

#if ASIMOV_SAM_DSU_PP_FSR_RESERVATION_SIZE < ASIMOV_DSU_P0_FSR_ROUTE_SIZE
#    error "FSR reservation must contain the minimum P0 route granule"
#endif

#if ((ASIMOV_DSU_P0_FSR_BASE >> CMN_CFG_MGMT_P0_RANGE0_ADDR_SHIFT) > \
     CMN_CFG_MGMT_P0_RANGE0_ADDR_MASK)
#    error "DSU P0 FSR base exceeds the range-0 PA[39:20] comparator"
#endif

/* ACP metadata sink: the address map's two 4 MiB windows (asimov_acp.h). */
#if ASIMOV_ACP_METADATA_SIZE != ASIMOV_ACP_SINK_SIZE
#    error "ACP metadata must be two 4 MiB ACP windows (routing, fence)"
#endif

#if (ASIMOV_ACP_METADATA_BASE & (ASIMOV_ACP_WINDOW_SIZE - 1U)) != 0U
#    error "ACP metadata allocation must be 4 MiB aligned"
#endif

#if ((ASIMOV_ACP_METADATA_BASE + ASIMOV_ACP_METADATA_SIZE - 1U) >> 44) != 0U
#    error "ACP metadata allocation exceeds the ACP base PA[43:22] field"
#endif

/*
 * STATUS reads allowed per configuration-engine drain (a drain shifts at
 * most 128 bits at 2 GHz): a liveness bound, as for the CMN ready poll. A
 * timeout logs one CRIT line and fails mod_init instead of hanging it.
 */
#define ASIMOV_CFG_ENGINE_POLLS (200U * 1000U)

/*
 * AP MPIDR Aff3 normalization. Written into cmn_cfg_mgmt.CLUSTERIDAFF3
 * before reset release; clusteridaff3 feeds every DSU cluster's
 * CLUSTERIDAFF3 input, i.e. AP MPIDR_EL1.Aff3 for all 10 cores.
 *
 * CLUSTERIDAFF3 resets to 0 on both hemispheres (asimov 866abab90); the
 * hemisphere is read from SOCKET_ID.hemi_id instead. Firmware still writes
 * the AP affinity namespace explicitly, independently of that hardware
 * identity.
 *
 * Each Asimov hemisphere is an independent island (its own SCP, CMN, GIC,
 * 10-core AP, OS) with no cross-hemisphere namespace, so AP Aff3 need not
 * be unique across hemispheres. We run one single-hemisphere image per
 * island and the TF-A port accepts only Aff3=0 (plat_core_pos_by_mpidr
 * rejects Aff3 != 0). Both hemispheres reset to 0; the write keeps Aff3 at
 * 0x00 whatever the reset value, so the same TF-A boots on both.
 *
 * Hence ASIMOV_HEMI_ID stays 0x00 for BOTH islands. Do NOT set it to 0x01
 * for East: that would present Aff3=1 and the single-hemisphere TF-A would
 * reject East's cores. (Provisional: revisit only if a unified multi-
 * hemisphere namespace is introduced -- not planned, post CML/CCG removal.)
 */
#ifndef ASIMOV_HEMI_ID
#define ASIMOV_HEMI_ID 0x00U
#endif

/*
 * CMN logic-domain readiness bound. After RESET_CTRL_BOOT_HOLD_MASK releases
 * CMN reset, the CMN logic domain completes its P-channel ON handshake and sets
 * cmn_cfg_mgmt.CMN_STATUS.ready (asimov 3f1f44e1e). Firmware polls ready over
 * the local M7 APB sideband before the first HN-D mesh access (issued later by
 * cmn_cyprus_start). A timeout is fatal: the RTL M7 AXIM bridge returns SLVERR
 * for pre-ready requests, so proceeding cannot safely configure the mesh.
 *
 * The bound is an iteration budget, NOT wall-clock, because mod_init has no
 * timebase: css600_tsgen is halted at reset (CNTCR.EN=0) and the folded
 * CNTBase0 frame is a plain register of its broadcast (cmn_m7_reset_ctrl.sv,
 * cntpct_r <= cntvalueb), so CNTPCT reads a constant until
 * asimov_system_enable_sys_counter() runs from start(). A CNTPCT delta taken
 * here never advances and can therefore never expire, which would turn this
 * readiness gate into an unbounded spin — and mod_sp805_start() has not armed
 * the watchdog yet, so nothing would recover it. Same pre-timebase idiom as
 * CDNS_XSPI_POLL_RETRY_LIMIT in mod_cdns_xspi.
 *
 * Each iteration is an AHB read across the M7-to-CMN path, so the budget does
 * not convert to a fixed microsecond figure: it is a liveness backstop, not a
 * calibrated timeout, and is deliberately generous.
 */
#define ASIMOV_CMN_STATUS_READY_SPIN_LIMIT (100U * 1000U)

/*
 * Number of witness/CFGM_PERIPHBASE read pairs
 * asimov_system_cfgm_periphbase_verified() will take before declaring the
 * strap lost. Repetition covers a transient only; a single clean pair is
 * already proof (see that function). Bounded by iteration count for the same
 * no-timebase reason as ASIMOV_CMN_STATUS_READY_SPIN_LIMIT above.
 */
#define ASIMOV_CFGM_PERIPHBASE_VERIFY_ATTEMPTS 4U

/*
 * PPU PWPR encoding (mirrors upstream module/ppu_v1/src/ppu_v1.h:64-72,
 * 99-100; that header is internal to mod_ppu_v1 and not part of its
 * public API, so the values are replicated here).
 *
 *   PWPR.POLICY     = bits [3:0]
 *   PWPR.DYNAMIC_EN = bit  [8]
 *   POLICY value 8  = ON
 *   POLICY value 7  = FUNC_RET
 *   POLICY value 0  = OFF
 *
 * PWPR = 0x008  →  static ON,    DYNAMIC_EN=0  (autonomous FSM disabled)
 * PWPR = 0x100  →  dynamic mode, autonomous target = OFF       (state-destroying)
 * PWPR = 0x107  →  dynamic mode, autonomous target = FUNC_RET  (state-preserving)
 */
#define PPU_V1_PWPR_OFFSET           0x000U
#define PPU_V1_PWPR_STATIC_ON        0x008U
#define PPU_V1_PWPR_DYNAMIC_OFF      0x100U

/*
 * Cluster PPU operating-mode policy. PWPR.OP_POLICY occupies bits [19:16]; 0x7 =
 * ALL SLICES / FULL L3 RAM (C1 DSU TRM 107804 §5.4.2, Tables 5-3/5-4). On this C1
 * instance (DIRECT_CONNECT=0, L3 present) a bare PWR_POLICY=ON (0x008) leaves
 * OP_POLICY=0 (ONE SLICE / SF-only) and the cluster never completes its OFF->ON
 * transition. The TRM-prescribed cluster-ON value (§5.7.1, step 1) is 0x00070008.
 */
#define PPU_V1_PWPR_OP_ALLSLICE_FULLRAM  0x00070000U
#define PPU_V1_PWPR_CLUSTER_ON           (PPU_V1_PWPR_OP_ALLSLICE_FULLRAM | \
                                          PPU_V1_PWPR_STATIC_ON)

/*
 * Boot-progress ("POST-code") publishing.
 *
 * Publish a 4-bit boot-stage marker to cmn_m7_reset_ctrl.BOOT_STATUS.stage
 * (SCP_RESET_CTRL_BASE + 0x008) at each boot milestone. BOOT_STATUS is an
 * M7-local scratch CSR on the always-reachable reset_ctrl sideband, so the
 * write lands regardless of CMN / RNSAM / mesh state — the marker write
 * itself can never stall. The codes are monotonic, so the last value
 * observed in BOOT_STATUS is the furthest point boot reached: it gives
 * early-boot progress before the SCP console is up, and a post-mortem
 * "how far did BL2 get" reading after a hang.
 *
 * The code table is the silicon-facing boot-progress contract documented in
 * firmware_boot_spec ("Boot-status register"). Codes 0xA-0xF are reserved
 * there for debug instrumentation and are not published here.
 */
enum asimov_boot_stage {
    ASIMOV_BOOT_STAGE_MODINIT_ENTRY   = 0x1U, /* asimov_system init entered    */
    ASIMOV_BOOT_STAGE_MODINIT_DONE    = 0x2U, /* straps+reset+CMN_STATUS ok */
    ASIMOV_BOOT_STAGE_START_ENTRY     = 0x3U, /* start(): module init complete  */
    ASIMOV_BOOT_STAGE_SYSCNT_DONE     = 0x4U, /* css600_tsgen enabled (mesh I/O ok) */
    ASIMOV_BOOT_STAGE_AP_EVENT_POSTED = 0x5U, /* AP-boot event queued           */
    ASIMOV_BOOT_STAGE_AP_EVENT_RUN    = 0x6U, /* AP-boot event handler entered  */
    ASIMOV_BOOT_STAGE_DVM_DONE        = 0x7U, /* CMN DVM domain configured      */
    ASIMOV_BOOT_STAGE_SETSTATE_DONE   = 0x8U, /* primary-core set_state(ON) issued */
    ASIMOV_BOOT_STAGE_PRIMARY_CORE_ON = 0x9U, /* primary core PD reached ON     */
};

static inline void asimov_system_set_boot_stage(enum asimov_boot_stage stage)
{
    *(volatile uint32_t *)(SCP_RESET_CTRL_BASE +
                           SCP_RESET_CTRL_BOOT_STATUS_OFFSET) =
        (uint32_t)((unsigned int)stage & 0xFU);
}

/* Module context */
struct asimov_system_ctx {
    /* Power domain module restricted API pointer */
    struct mod_pd_restricted_api *pd_restricted_api;

    /* The only RESET_CTRL writer (asimov_reset_ctrl.h) */
    struct asimov_reset_ctrl reset_ctrl;

    /* Physical SAM, OCM included, verified and RN traffic admitted */
    bool ocm_checkpoint;

    /* Hemisphere: cmn_cfg_mgmt.SOCKET_ID.hemi_id, the HEMI_ID strap */
    uint8_t hemi_id;

    /* clk_core as read back from CAR (asimov_clk_provider.h) */
    struct asimov_clk_provider clk_provider;
};

static struct asimov_system_ctx asimov_system_ctx = {
    .reset_ctrl = {
        .ctrl = (volatile uint32_t *)(SCP_RESET_CTRL_BASE +
                                      SCP_RESET_CTRL_CTRL_OFFSET),
        .status = (const volatile uint32_t *)(SCP_RESET_CTRL_BASE +
                                              SCP_RESET_CTRL_STATUS_OFFSET),
        .runtime_mask = RESET_CTRL_RUNTIME_MASK,
    },
    .clk_provider = ASIMOV_CLK_PROVIDER_INIT,
};

/* Empty module configuration (no per-module config data) */
const struct fwk_module_config config_asimov_system = { 0 };

/*
 * Program RVBAR for all DSUs via the cmn_cfg_mgmt per-DSU RVBAR slots.
 *
 * Per Mike Bly's P0-6 resolution (2026-05-04), per-DSU RVBAR slots live
 * in cmn_cfg_mgmt at offsets 0x000-0x02C (8 B per DSU: LO at +0x00, HI
 * at +0x04). RVBAR is shared between both PEs in a DSU. TF-A sets the
 * same BL31 entry address for all cores, so a single write per DSU is
 * functionally sufficient.
 *
 * MUST be called before deasserting cluster reset (RESET_CTRL DSU bits).
 * On silicon and silicon-faithful FVP, the cluster samples its RVBAR
 * input at cluster nSRESET deassert; writing RVBAR after that point is
 * a no-op until the next per-core warm reset. Mirror that ordering
 * here so AP cores boot to AP_RVBAR_ADDR on cold boot.
 */
static void asimov_system_program_dsu_rvbar(void)
{
    unsigned int cluster_count = platform_get_cluster_count();
    unsigned int cluster_idx;

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] Setting AP RVBAR to 0x%08x%08x",
        (unsigned int)(AP_RVBAR_ADDR >> 32),
        (unsigned int)(AP_RVBAR_ADDR & 0xFFFFFFFFUL));

    for (cluster_idx = 0; cluster_idx < cluster_count; cluster_idx++) {
        volatile uint32_t *rvbar_lo = (volatile uint32_t *)(
            SCP_CMN_CFG_MGMT_BASE + CMN_CFG_MGMT_RVBAR_LO(cluster_idx));
        volatile uint32_t *rvbar_hi = (volatile uint32_t *)(
            SCP_CMN_CFG_MGMT_BASE + CMN_CFG_MGMT_RVBAR_HI(cluster_idx));

        *rvbar_lo = (uint32_t)(AP_RVBAR_ADDR & 0xFFFFFFFFUL);
        __DSB();
        *rvbar_hi = (uint32_t)(AP_RVBAR_ADDR >> 32);
        __DSB();
    }
}

/* Both halves now carry meaningful state. Verify every DSU while reset is
 * held; the CFGM witness below is not a substitute for this check. DSBs
 * separate each transfer through the M7 APB bridge in both build modes. */
static bool asimov_system_dsu_rvbar_verified(void)
{
    unsigned int i;

    for (i = 0; i < platform_get_cluster_count(); i++) {
        const uint32_t lo = *(volatile uint32_t *)(SCP_CMN_CFG_MGMT_BASE +
            CMN_CFG_MGMT_RVBAR_LO(i));
        __DSB();
        const uint32_t hi = *(volatile uint32_t *)(SCP_CMN_CFG_MGMT_BASE +
            CMN_CFG_MGMT_RVBAR_HI(i));
        __DSB();
        if ((lo != (uint32_t)(AP_RVBAR_ADDR & CMN_CFG_MGMT_RVBAR_LO_MASK)) ||
            (hi != (uint32_t)(AP_RVBAR_ADDR >> 32))) {
            FWK_LOG_CRIT("[ASIMOV SYSTEM] DSU%u RVBAR readback FAILED", i);
            return false;
        }
    }
    return true;
}

/* CMN endpoint decoders are independent of RN-SAM routing. Program every
 * populated NID228/NID136 child while CMN remains in reset, using PA[47:12]
 * register encoding (not byte addresses in the LO register). */
static bool asimov_system_program_cmn_children(void)
{
    static const struct asimov_endpoint_decoder slots[] = {
        ASIMOV_ENDPOINT_DECODER_INITIALIZERS
    };
    unsigned i;
    for (i = 0; i < sizeof(slots) / sizeof(slots[0]); i++) {
        volatile uint32_t *lo = (volatile uint32_t *)(
            slots[i].lo_address);
        volatile uint32_t *hi = (volatile uint32_t *)(slots[i].hi_address);
        uint32_t expected_lo = slots[i].lo_value;
        uint32_t expected_hi = slots[i].hi_value;
        *lo = expected_lo;
        __DSB();
        *hi = expected_hi;
        __DSB();
        uint32_t actual_lo = *lo;
        __DSB();
        uint32_t actual_hi = *hi;
        __DSB();
        if (actual_lo != expected_lo || actual_hi != expected_hi) {
            FWK_LOG_CRIT("[ASIMOV SYSTEM] CMN child base FAILED +0x%x",
                         (unsigned int)(slots[i].lo_address -
                                        ASIMOV_ENDPOINT_CFG_MGMT_BASE));
            FWK_LOG_FLUSH();
            return false;
        }
    }
    FWK_LOG_INFO("[ASIMOV SYSTEM] CMN child bases verified");
    return true;
}

/*
 * Force AP MPIDR Aff3 to ASIMOV_HEMI_ID (0x00) in cmn_cfg_mgmt before
 * reset release. See ASIMOV_HEMI_ID above: CLUSTERIDAFF3 resets to 0 on
 * both hemispheres, so the write keeps the value the single-hemisphere TF-A
 * accepts. Paired with the RVBAR programming that precedes it (both sampled
 * before CMN/DSU reset deassert). The hemisphere is read from
 * SOCKET_ID.hemi_id at the same time (asimov_system_hemisphere()).
 */
static void asimov_system_program_cluster_aff3(void)
{
    asimov_system_ctx.hemi_id = asimov_hemi_id_normalize(
        SCP_CMN_CFG_MGMT_BASE, (uint8_t)(ASIMOV_HEMI_ID & 0xFFU));
    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] Hemisphere %u (SOCKET_ID), AP Aff3 %u",
        (unsigned int)asimov_system_ctx.hemi_id,
        (unsigned int)(ASIMOV_HEMI_ID & 0xFFU));
}

/*
 * Strap the CMN-S3 configuration-aperture base (cmn_cfg_mgmt.CFGM_PERIPHBASE),
 * like RVBAR, BEFORE the CMN reset is deasserted: the CMN-S3 samples
 * CFGM_PERIPHBASE[19:0] = PA[47:28] at reset deassert. It is 0 at POR, so
 * without this strap the CMN config aperture is never mapped at SCP_CMN_BASE,
 * and cmn_cyprus's first config read (e.g. SCP_CMN_BASE + 0x10) returns a
 * decode error — boot then stalls before AP-core power-on.
 * SCP_CMN_CFGM_PERIPHBASE_VAL maps the aperture to SCP_CMN_BASE (see
 * scp_mmap.h for the window choice).
 *
 * Whether a missing strap is visible on the FVP depends on the pinned
 * terminus: models that do not consume CFGM_PERIPHBASE treat the write as
 * inert and place the aperture from a model parameter, so the gap appears
 * only on RTL/emulation. Models carrying the CFGM aperture gate abort a
 * configuration access whose aperture the strap does not select.
 */
static void asimov_system_program_cfgm_periphbase(void)
{
    volatile uint32_t *cfgm_periphbase = (volatile uint32_t *)(
        SCP_CMN_CFG_MGMT_BASE + CMN_CFG_MGMT_CFGM_PERIPHBASE);

    *cfgm_periphbase = (uint32_t)SCP_CMN_CFGM_PERIPHBASE_VAL;

    /*
     * No readback here. The old one lived in the FWK_LOG_INFO argument list,
     * so it compiled out entirely at the release log level (WARN) — which is
     * why a lost strap was invisible in exactly the build that lost it.
     * Verification is now unconditional code in
     * asimov_system_cfgm_periphbase_verified() below.
     */
    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] Strapped CMN CFGM_PERIPHBASE=0x%05x, 0x%08x",
        (unsigned int)SCP_CMN_CFGM_PERIPHBASE_VAL,
        (unsigned int)SCP_CMN_BASE);
}

/*
 * Guard the witness choice: the verification below distinguishes a genuine
 * read from a dropped one by the fact that the two expected values cannot be
 * confused. If AP_RVBAR_ADDR or the CMN aperture ever moves such that they
 * collide, the check would silently lose its ability to detect a drop.
 */
/*
 * Direction one: a dropped WITNESS read returns the preceding access's data.
 * If the witness's expected value equalled the strap value, that drop would
 * satisfy the witness test.
 */
#if ((AP_RVBAR_ADDR & CMN_CFG_MGMT_RVBAR_LO_MASK) == \
     SCP_CMN_CFGM_PERIPHBASE_VAL)
#    error "RVBAR_LO witness aliases CFGM_PERIPHBASE (dropped-witness direction)"
#endif
/*
 * Direction two: a dropped PERIPHBASE read returns the witness value, which
 * the read path then masks with CMN_CFG_MGMT_CFGM_PERIPHBASE_MASK. If the
 * MASKED witness equalled the strap value, that drop would satisfy the
 * strap test. Both directions must be excluded for the pair to be a proof.
 */
#if (((AP_RVBAR_ADDR & CMN_CFG_MGMT_RVBAR_LO_MASK) & \
      CMN_CFG_MGMT_CFGM_PERIPHBASE_MASK) == SCP_CMN_CFGM_PERIPHBASE_VAL)
#    error "Masked RVBAR_LO witness aliases CFGM_PERIPHBASE (dropped-read direction)"
#endif
/* The high SMS reset vector requires both RVBAR halves. The dedicated
 * readback above checks each pair before any DSU reset is released. */
#if ((AP_RVBAR_ADDR >> 40) != 0)
#    error "AP_RVBAR_ADDR exceeds C1's 40-bit physical address width"
#endif

/*
 * Confirm the CFGM_PERIPHBASE strap actually landed — by reading, never by
 * rewriting.
 *
 * The bespoke AHB-Lite-to-APB shim in cmn_m7_top.sv that serves the
 * cmn_cfg_mgmt / cmn_dsu_mgmt page (0x4400_4000-0x4400_4FFF) raises HREADYOUT
 * during its APB-completion cycle — accepting the master's next address phase
 * — but returns to A2P_IDLE without capturing it. Every second transfer of a
 * back-to-back run is therefore lost (Positron-AI-TSMC/asimov#2938, with the
 * ASIC team). At release optimisation the strap helpers inline into one run of
 * twelve stores, the even ones drop, and CFGM_PERIPHBASE — store twelve —
 * never arrives: the aperture stays at its POR 0 and cmn_cyprus stalls on its
 * first config read. A debug build keeps the calls separate and its extra idle
 * cycles mask the defect.
 *
 * A dropped access still completes HREADY=1/OKAY, and a dropped READ returns
 * the PREVIOUS APB access's data — cmn_apb_sync_2to1_bridge.sv holds
 * rsp_prdata_2g across transactions and never clears it. A lone readback
 * adjacent to the store therefore proves nothing. Reading a witness register
 * in the same page immediately before each CFGM_PERIPHBASE read makes both
 * drop phases self-identifying instead:
 *
 *   - a dropped CFGM_PERIPHBASE read returns the witness value zero,
 *     which masks to 0x00000 and can never equal SCP_CMN_CFGM_PERIPHBASE_VAL;
 *   - a dropped witness read returns SCP_CMN_CFGM_PERIPHBASE_VAL, which can
 *     never equal the zero low half of the high SMS reset vector.
 *
 * So a matching pair requires both accesses to have been genuinely captured,
 * and a genuinely captured read of an unstrapped CFGM_PERIPHBASE returns its
 * POR 0, not the strap value. There is no false-pass path. RVBAR_LO(0) is the
 * witness because firmware wrote it itself from a compile-time constant
 * earlier in this same mod_init (asimov_system_program_dsu_rvbar). That
 * expectation does rest on one property: RVBAR_LO(0) is the FIRST store of
 * the strap run, so it lands even on a part affected by asimov#2938, which
 * drops the transfer presented in a preceding access's completion cycle.
 * Adding any store to this page ahead of asimov_system_program_dsu_rvbar()
 * would shift that parity and invalidate the witness — keep it first.
 *
 * Only CFGM_PERIPHBASE is gated here. The same run also loses the five
 * RVBAR_HI writes on an affected part; those are harmless solely because
 * their intended value is 0 and POR is 0, which holds while AP_RVBAR_ADDR
 * fits in 32 bits (asserted below). A wider reset vector would make them a
 * live defect and want their own gate.
 *
 * The repeat count is verification against a transient, NOT a retry of the
 * write: this function issues reads only, and
 * asimov_system_program_cfgm_periphbase() above keeps its single store with no
 * loop and no inserted spacing. Re-issuing the write would mask asimov#2938
 * rather than report it.
 */
static bool asimov_system_cfgm_periphbase_verified(
    uint32_t *observed,
    uint32_t *witness)
{
    volatile uint32_t *rvbar_lo = (volatile uint32_t *)(
        SCP_CMN_CFG_MGMT_BASE + CMN_CFG_MGMT_RVBAR_LO(0));
    volatile uint32_t *cfgm_periphbase = (volatile uint32_t *)(
        SCP_CMN_CFG_MGMT_BASE + CMN_CFG_MGMT_CFGM_PERIPHBASE);
    unsigned int attempt;

    for (attempt = 0; attempt < ASIMOV_CFGM_PERIPHBASE_VERIFY_ATTEMPTS;
         attempt++) {
        /*
         * Witness first, PERIPHBASE second, with no other APB access in
         * between — that, not instruction adjacency, is what the aliasing
         * argument below needs.
         *
         * The two loads must NOT be adjacent on the bus. An unfixed shim
         * (asimov#2938) drops whichever transfer is presented in the
         * preceding access's completion cycle, so back-to-back loads would
         * lose the PERIPHBASE read and return the witness value instead —
         * failing the gate on every affected part whether or not the store
         * actually landed, and halting a debug build that boots today.
         * __DSB() retires the witness read before the PERIPHBASE address
         * phase is presented. It issues no APB traffic of its own, so the
         * witness remains the immediately preceding bus access and the
         * no-false-pass argument is unchanged. Spacing reads for
         * observability is not a workaround for #2938: the strap store
         * itself is still issued exactly once and is never re-tried.
         */
        uint32_t witness_val = *rvbar_lo;
        __DSB();
        uint32_t observed_val =
            *cfgm_periphbase & CMN_CFG_MGMT_CFGM_PERIPHBASE_MASK;

        *witness = witness_val;
        *observed = observed_val;

        if (witness_val ==
                (uint32_t)(AP_RVBAR_ADDR & CMN_CFG_MGMT_RVBAR_LO_MASK) &&
            observed_val == (uint32_t)SCP_CMN_CFGM_PERIPHBASE_VAL) {
            return true;
        }
    }

    return false;
}

/*
 * Program and prove the DSU peripheral-port route to the FSR before cluster
 * reset is released. AEND0 is exclusive; programming 0xB8000..0xB8001
 * selects exactly [0xB8_0000_0000, 0xB8_000F_FFFF].
 *
 * Keep this operation after CFGM_PERIPHBASE verification. Apart from making
 * that earlier strap's witness sequence easier to audit, it ensures an FSR
 * change cannot perturb the fail-closed gate that protects all CMN traffic.
 * The DSB between readbacks prevents an old back-to-back AHB/APB transfer-loss
 * defect from manufacturing a false match. Writes are not retried: any lost
 * or rejected strap is detected and boot remains behind reset.
 */
static bool asimov_system_program_dsu_fsr_p0(
    unsigned int *failed_dsu,
    uint32_t *observed_start,
    uint32_t *observed_end)
{
    const uint32_t start_strap = ASIMOV_DSU_P0_FSR_START_VALUE &
        CMN_CFG_MGMT_P0_RANGE0_ADDR_MASK;
    const uint32_t end_strap = ASIMOV_DSU_P0_FSR_END_VALUE &
        CMN_CFG_MGMT_P0_RANGE0_ADDR_MASK;
    const unsigned int cluster_count = platform_get_cluster_count();
    unsigned int cluster_idx;

    for (cluster_idx = 0; cluster_idx < cluster_count; cluster_idx++) {
        volatile uint32_t *astart = (volatile uint32_t *)(
            SCP_CMN_CFG_MGMT_BASE +
            CMN_CFG_MGMT_ASTART_P0(cluster_idx, ASIMOV_DSU_P0_FSR_WINDOW));
        volatile uint32_t *aend = (volatile uint32_t *)(
            SCP_CMN_CFG_MGMT_BASE +
            CMN_CFG_MGMT_AEND_P0(cluster_idx, ASIMOV_DSU_P0_FSR_WINDOW));

        *astart = start_strap;
        *aend = end_strap;
    }

    __DSB();

    for (cluster_idx = 0; cluster_idx < cluster_count; cluster_idx++) {
        volatile uint32_t *astart = (volatile uint32_t *)(
            SCP_CMN_CFG_MGMT_BASE +
            CMN_CFG_MGMT_ASTART_P0(cluster_idx, ASIMOV_DSU_P0_FSR_WINDOW));
        volatile uint32_t *aend = (volatile uint32_t *)(
            SCP_CMN_CFG_MGMT_BASE +
            CMN_CFG_MGMT_AEND_P0(cluster_idx, ASIMOV_DSU_P0_FSR_WINDOW));
        const uint32_t start =
            *astart & CMN_CFG_MGMT_P0_RANGE0_ADDR_MASK;

        __DSB();

        const uint32_t end = *aend & CMN_CFG_MGMT_P0_RANGE0_ADDR_MASK;

        *failed_dsu = cluster_idx;
        *observed_start = start;
        *observed_end = end;

        if ((start != start_strap) || (end != end_strap)) {
            return false;
        }
    }

    return true;
}

/*
 * Enable the ARM Generic Timer system counter (css600_tsgen) at boot.
 *
 * The counter is halted at reset (CNTCR.EN resets to 0). Until enabled it
 * does not count, so its broadcast (dsu_cntvalueb) — which feeds every DSU
 * CNTVALUEB and the M7's own CNTBase0 frame — stays frozen, and AP
 * CNTPCT/CNTVCT (Linux timekeeping) never advances. The SCP owns enabling
 * it; TF-A defers (it overrides bl31_platform_setup to skip the CNTCR write
 * and uses a compile-time frequency).
 *
 * The css600_tsgen control port lives in the NIC-400 peripheral fabric at
 * SCP_SYS_CNTCONTROL_BASE (0x2A43_0000), reachable only over the mesh —
 * there is no working M7 APB sideband (see scp_mmap.h). So this MUST run
 * after mod_cmn_cyprus has programmed the RNSAM I/O region, i.e. from
 * start() (not mod_init()). Sequence: disable, set FID0 to the count
 * frequency, then set EN. (Unlike the multi-FID upstream mod_gtimer,
 * css600_tsgen is single-FID — CNTCR is bits [1:0] only, with no
 * FCREQ/FCACK frequency-change handshake — so setting EN is the whole
 * enable.)
 *
 * Silicon note: the SCP's own gtimer reads CNTPCT from the same css600_tsgen
 * broadcast, so it is frozen until this runs. On the FVP this is invisible:
 * both the AP clusters and the SCP gtimer run off independent free-running
 * BasePlatform reference counters (bp.reference_cntvalueb / scp_refcounter),
 * decoupled from this write. On silicon, early-boot timing must not depend
 * on the system counter before this point (use SysTick / cycle counts).
 * Tracked as a silicon bring-up item under STORY-465.
 */
static void asimov_system_enable_sys_counter(void)
{
    volatile uint32_t *cntcr =
        (volatile uint32_t *)(SCP_SYS_CNTCONTROL_BASE + SYS_CNT_CNTCR_OFFSET);
    volatile uint32_t *cntfid0 =
        (volatile uint32_t *)(SCP_SYS_CNTCONTROL_BASE + SYS_CNT_CNTFID0_OFFSET);

    *cntcr   = 0u; /* halt while reprogramming */
    *cntfid0 = (uint32_t)SYS_CNT_FREQ_HZ;
    *cntcr   = (uint32_t)SYS_CNT_CNTCR_EN;

    /* CNTFID0 in whole MHz, so the line fits fwk_log's 64 columns. */
    _Static_assert((SYS_CNT_FREQ_HZ % 1000000UL) == 0UL,
                   "CNTFID0 is a whole number of MHz");
    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] System counter enabled: %u MHz @ 0x%08x",
        (unsigned int)(SYS_CNT_FREQ_HZ / 1000000UL),
        (unsigned int)SCP_SYS_CNTCONTROL_BASE);
}

/*
 * Power on the primary core (cluster 0, core 0) with a composite state
 * that also powers on its cluster and SYSTOP. RVBAR for all DSUs is
 * already programmed by mod_init() before any of this runs — see the
 * comment on asimov_system_program_dsu_rvbar() for why that ordering
 * matters on silicon-faithful FVP and silicon.
 */
/*
 * Stage the cluster PPU operating-mode policy (ALL SLICE / FULL L3 RAM) before the
 * framework powers the cluster on. ppu_v1's cluster_on issues request_power_mode(ON),
 * which sets PWR_POLICY=ON while *preserving* OP_POLICY[19:16] — so pre-writing
 * PWPR=0x00070008 here makes the framework's ON request resolve to the full
 * 0x00070008 (ON + ALL SLICE / FULL RAM). It cannot be deferred to after the cluster
 * is ON: ppu_v1_request_operating_mode() requires PWSR=ON first, which this C1
 * instance never reaches while OP_POLICY=0. See C1 DSU TRM 107804 §5.7.1.
 *
 * Scope: this covers the primary cluster brought up here at boot (what the cmn_tlm
 * emulation exercises). Secondary clusters powered at runtime via PSCI/SCMI go
 * through ppu_v1 cluster_on directly and need the same op-policy in the driver path
 * — tracked as a follow-up (see PR description).
 */
static void asimov_system_stage_cluster_op_policy(unsigned int cluster_idx)
{
    volatile uint32_t *pwpr = (volatile uint32_t *)
        (SCP_CLUSTER_PPU_BASE(cluster_idx) + PPU_V1_PWPR_OFFSET);

    *pwpr = PPU_V1_PWPR_CLUSTER_ON;

    /* PWPR: policy ON, operating mode ALL SLICE/FULL RAM. */
    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] Staged cluster %u PPU PWPR=0x%08x (ON)",
        cluster_idx, (unsigned int)PPU_V1_PWPR_CLUSTER_ON);
}

static int asimov_system_init_primary_core(void)
{
    int status;

    FWK_LOG_INFO("[ASIMOV SYSTEM] Powering on primary core (CLUS0CORE0)...");

    /*
     * Stage the cluster operating-mode policy before the composite set_state, so the
     * framework's cluster_on resolves to PWPR=0x00070008 instead of a bare 0x008
     * (which leaves the L3/slices off and never reaches ON). Primary cluster = 0.
     */
    asimov_system_stage_cluster_op_policy(0);

    /*
     * Power on the primary core via the framework's composite set_state.
     * The mock_ppu system PPU element ensures report_power_state_transition
     * is called for SYSTOP, enabling the cascade to cluster and core PPUs.
     *
     * Composite state: SYSTOP=ON, cluster=ON, core=ON
     * The power_domain module walks the tree:
     *   SYSTOP → system_power → mock_ppu (reports transition)
     *   cluster → ppu_v1 (writes cluster PPU_PWPR=ON via utility bus)
     *   core → ppu_v1 (writes core PPU_PWPR=ON, enables dynamic mode)
     */
    status = asimov_system_ctx.pd_restricted_api->set_state(
        FWK_ID_ELEMENT(FWK_MODULE_IDX_POWER_DOMAIN, 0),
        false,
        MOD_PD_COMPOSITE_STATE(
            MOD_PD_LEVEL_2,
            0,
            MOD_PD_STATE_ON,
            MOD_PD_STATE_ON,
            MOD_PD_STATE_ON));

    if (status != FWK_SUCCESS) {
        FWK_LOG_ERR(
            "[ASIMOV SYSTEM] Failed to power on primary core (%d)", status);
    } else {
        FWK_LOG_INFO("[ASIMOV SYSTEM] Primary core power-on initiated");
        asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_SETSTATE_DONE);
    }

    return status;
}

/*
 * System power driver API: system_shutdown
 */
static int asimov_system_shutdown(
    enum mod_pd_system_shutdown system_shutdown)
{
    FWK_LOG_INFO("[ASIMOV SYSTEM] System shutdown request (%d)", system_shutdown);

    /* TODO(asimov): Implement proper shutdown/reset via platform mechanism */
    NVIC_SystemReset();

    return FWK_E_DEVICE;
}

static const struct mod_system_power_driver_api
    asimov_system_power_driver_api = {
        .system_shutdown = asimov_system_shutdown,
    };

/*
 * Pin the static-only PPU power policy on a core after it transitions to ON.
 *
 * --------------------------------------------------------------------------
 * Why this exists  (firmware_boot_spec §7.3.2)
 * --------------------------------------------------------------------------
 * Asimov runs at a single Operating Point with no DVFS, no on-die power
 * switches, and no retention rails (PTCR §3.1.10, §5.8). The runtime
 * power model is two physical states only:
 *
 *   ON  — clocks running, core executing
 *   OFF — PSCI CPU_OFF: clocks gated + reset asserted, state lost
 *
 * The PPU autonomous dynamic-mode transition path is *not* used. No PSCI
 * CPU_SUSPEND, no FUNC_RET-as-Linux-visible-state, no per-core idle clock
 * gating below the PSCI boundary.
 *
 * --------------------------------------------------------------------------
 * The latent trap we are closing
 * --------------------------------------------------------------------------
 * Upstream mod_ppu_v1 unconditionally enables dynamic mode after every
 * core set_state(ON). See scp-firmware/module/ppu_v1/src/mod_ppu_v1.c
 * around lines 434-435:
 *
 *   ppu_v1_set_power_mode(ppu, PPU_V1_MODE_ON, ...);  // PWPR = 0x008
 *   ppu_v1_dynamic_enable(ppu, PPU_V1_MODE_OFF);      // PWPR = 0x100
 *
 * That second write puts the PPU in dynamic mode with autonomous-target =
 * OFF. On a DEVPACTIVE drop the PPU would transition the core to OFF
 * (reset asserted, architectural state lost) — *not* FUNC_RET.
 *
 * This does not manifest at runtime today only because the firmware never
 * writes cmn_dsu_mgmt + 0x120 WAKEREQ. It stays at its reset value 0x3FF
 * (all 10 core wake-bits asserted), pinning COREWAKEREQUEST high so
 * DEVPACTIVE never drops. The autonomous FSM is enabled but cannot fire.
 *
 * That is a fragile invariant. Anyone touching WAKEREQ later — for debug,
 * MPMM bring-up, thermal experiments, or as a stepping stone toward the
 * STORY-371 autonomous-idle path — would inadvertently activate the
 * autonomous-to-OFF transition and lose Linux state on the next WFI.
 *
 * To make the static-only intent explicit at the register level (and stop
 * depending on the WAKEREQ-stuck-at-reset invariant), we re-write
 * PWPR = 0x008 after each core PD reaches ON. Subscribed for both the
 * cold-boot primary and every runtime CPU_ON-driven secondary.
 *
 * --------------------------------------------------------------------------
 * Future path (out of scope here; tracked under STORY-371)
 * --------------------------------------------------------------------------
 * Adopting state-preserving autonomous idle (clocks gated on WFI, core
 * resumes from IRQ without losing state) requires TWO firmware changes:
 *   1. Manage cmn_dsu_mgmt WAKEREQ to deassert COREWAKEREQUEST on idle
 *      and re-assert on wake.
 *   2. Replace the PWPR=0x008 write here with PWPR=0x107 so the dynamic-
 *      mode autonomous target is FUNC_RET (state-preserving), not OFF.
 * Neither is in scope here.
 */
static void asimov_system_pin_core_static_on(unsigned int core_pd_idx)
{
    unsigned int cluster_idx = core_pd_idx / CORES_PER_CLUSTER;
    unsigned int core_idx    = core_pd_idx % CORES_PER_CLUSTER;
    volatile uint32_t *pwpr  = (volatile uint32_t *)
        (SCP_CORE_PPU_BASE(cluster_idx, core_idx) + PPU_V1_PWPR_OFFSET);

    *pwpr = PPU_V1_PWPR_STATIC_ON;

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] Pinned CLUS%uCORE%u PPU PWPR=0x008 (static ON)",
        cluster_idx, core_idx);

    /*
     * Primary core (PD element 0) reached ON: publish the furthest boot
     * stage. This is the deepest BOOT_STATUS code on the cold-boot path.
     */
    if (core_pd_idx == 0U) {
        asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_PRIMARY_CORE_ON);
    }
}

/*
 * Enable dynamic mode on a cluster's C1-SME2 (CME) PPU once the cluster is ON.
 *
 * The pinned RTL builds one CME per cluster (C1_DSU_DynamIQ_Cluster_1.yaml
 * NUM_CME: 1) with PPU_RST_STATE=FALSE: every PPU, the CME's included, resets
 * in STATIC mode with the unit OFF. TRM 107804 requires the SME2-unit PPU to
 * be programmed in DYNAMIC mode before any core executes streaming-SVE — in
 * static mode a core issuing its first SSVE instruction stalls until the PPU
 * allows the ON transition. In dynamic mode the unit powers itself on when a
 * core sends it work and back off only when all cores have
 * PSTATE.SM = PSTATE.ZA = 0 (no live streaming state to lose), so the
 * static-only rationale for core PPUs above (state-destroying autonomous OFF)
 * does not apply here: dynamic IS the Arm-recommended operating model for the
 * CME, and there is no CME wake-request pin to manage (COREWAKEREQUEST covers
 * cores only).
 *
 * Written on EVERY core-ON notification, not once per cluster: a cluster can
 * power off and back on at runtime (PSCI CPU_OFF of both cores takes the
 * cluster down), and CME PPU state is not guaranteed to be retained across a
 * cluster power cycle — a once-only latch would leave the CME PPU static-off
 * after the cycle and reintroduce the SSVE stall. A core reaching ON
 * guarantees the parent cluster is ON (the access precondition for the CME
 * PPU registers), and the write is idempotent, so re-arming every time is
 * cheap and robust.
 *
 * FastModel note: the FVP accepts CME PPU writes but they are inert (the
 * model powers the CME autonomously; terminus DD-12). This write is required
 * on silicon and harmless on the model.
 */
static void asimov_system_enable_cme_dynamic(unsigned int cluster_idx)
{
    volatile uint32_t *pwpr = (volatile uint32_t *)
        (SCP_CME_PPU_BASE(cluster_idx, 0) + PPU_V1_PWPR_OFFSET);

    *pwpr = PPU_V1_PWPR_DYNAMIC_OFF;

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] CLUS%u CME0 PPU PWPR=0x100 (dynamic; SME2 ready)",
        cluster_idx);
}

/*
 * Framework module interface
 */

static bool asimov_system_probe_read32(uintptr_t addr, uint32_t *value);

/* An XMS or SPM chain load did not finish: report it and stop boot. */
static int asimov_system_cfg_failed(void)
{
    FWK_LOG_CRIT("[ASIMOV SYSTEM] XMS/SPM cfg load FAILED");
    FWK_LOG_FLUSH();
    return FWK_E_DEVICE;
}

static int asimov_system_mod_init(
    fwk_id_t module_id,
    unsigned int unused,
    const void *unused2)
{
    asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_MODINIT_ENTRY);

    /*
     * Read the reset arbiter's RESET_SYNDROME register and log the most-
     * recent reset cause. The POR bit is sticky until the next cold POR;
     * the warm-reset bits are also set across the warm reset and clear
     * via RESET_SYNDROME_CLR. Check warm-reset bits first; fall through
     * to POR when no warm-reset bit is set.
     */
    uint32_t syndrome = *(volatile uint32_t *)(SCP_RESET_CTRL_BASE +
                                               SCP_RESET_CTRL_SYNDROME_OFFSET);

    if (syndrome & RESET_SYNDROME_M7_LOCKUP) {
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Reset cause: M7 LOCKUP");
    } else if (syndrome & RESET_SYNDROME_WDOGRESET_SYS) {
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] Reset cause: watchdog bite (full-scope)");
    } else if (syndrome & RESET_SYNDROME_SYSRESETREQ) {
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Reset cause: M7 SYSRESETREQ");
    } else if (syndrome & RESET_SYNDROME_POR) {
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Reset cause: cold POR");
    } else {
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] Reset cause: unknown (RESET_SYNDROME 0x%08x)",
            (unsigned int)syndrome);
    }

    /*
     * Program the per-DSU RVBAR slots in cmn_cfg_mgmt BEFORE we deassert
     * cluster reset below. Silicon samples cluster RVBAR at nSRESET
     * deassert, so writing RVBAR after the reset release lands too late.
     * See asimov_system_program_dsu_rvbar() for the slot layout.
     */
    asimov_system_program_dsu_rvbar();
    if (!asimov_system_dsu_rvbar_verified()) {
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Halting boot before reset release");
        FWK_LOG_FLUSH();
        return FWK_E_DEVICE;
    }

    /*
     * Normalize AP MPIDR Aff3 (CLUSTERIDAFF3) before reset release, so
     * cmn_cfg_mgmt presents the value before CMN/DSU reset is deasserted.
     */
    asimov_system_program_cluster_aff3();

    /*
     * Strap the CMN-S3 config-aperture base (CFGM_PERIPHBASE) before reset
     * release — same reason as RVBAR: the CMN samples it at reset deassert.
     * Without it the config aperture is unmapped and cmn_cyprus's first
     * config read decode-errors, stalling boot before AP-core power-on.
     * See asimov_system_program_cfgm_periphbase().
     */
    asimov_system_program_cfgm_periphbase();

    /*
     * Prove the strap landed before releasing CMN/DSU reset. The CMN samples
     * CFGM_PERIPHBASE at reset deassert, so this is the last point at which a
     * lost strap can still be reported instead of silently producing an
     * unstrapped mesh. __DSB() drains the posted store first: region 0 of
     * config_armv7m_mpu is TEX 0 / C 0 / B 1 / S 1, i.e. bufferable Device.
     */
    __DSB();

    uint32_t cfgm_observed = 0U;
    uint32_t cfgm_witness = 0U;

    if (!asimov_system_cfgm_periphbase_verified(
            &cfgm_observed, &cfgm_witness)) {
        /*
         * Three short lines rather than one: fwk_log truncates at
         * FMW_LOG_COLUMNS (80) and the "[ASIMOV SYSTEM] " tag plus the
         * timestamp prefix already spend 31 of those columns.
         *
         * A failure here does not distinguish "the write was dropped" from
         * "the write landed but both verification reads were dropped". Either
         * way this is an asimov#2938 part and the strap cannot be proven, so
         * the correct action is the same: report and stop.
         */
        FWK_LOG_CRIT("[ASIMOV SYSTEM] CFGM_PERIPHBASE strap FAILED");
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] want 0x%05x got 0x%05x witness 0x%08x",
            (unsigned int)SCP_CMN_CFGM_PERIPHBASE_VAL,
            (unsigned int)cfgm_observed,
            (unsigned int)cfgm_witness);
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Halting boot before reset release");

        /*
         * The flush is load-bearing, not decorative. Release builds define
         * FWK_LOG_BUFFERED (FMW_LOG_BUFFER_SIZE 4 KiB) and nothing drains the
         * ring until fwk_core's idle loop, which this path never reaches. The
         * framework turns a non-success init() return into fwk_trap(), and
         * arch_exceptions.c prints a fault only when FWK_LOG_BUFFERED is
         * undefined — so without this call the halt would be silent in exactly
         * the build that needs the message.
         */
        FWK_LOG_FLUSH();

        /*
         * Returning before the RESET_CTRL write below leaves CMN, GIC and the
         * DSUs held in reset, so nothing is ever issued into an unstrapped
         * mesh. BOOT_STATUS is deliberately not advanced: it stays at
         * MODINIT_ENTRY (0x1), which firmware_boot_spec 10.4 already defines
         * as "boot stopped advancing here", and which needs no UART. That spec
         * reserves 0xA-0xF for debug use and bars production firmware from
         * writing them, so no dedicated fatal code is invented here.
         */
        return FWK_E_DEVICE;
    }

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] CFGM_PERIPHBASE strap verified (0x%05x)",
        (unsigned int)cfgm_observed);

    if (!asimov_system_program_cmn_children())
        return FWK_E_DEVICE;

    /*
     * Route each DSU's peripheral port to the final FSR address before the
     * DSUs sample ASTART0/AEND0 at reset release. A failed readback is fatal:
     * allowing Linux to probe a partially programmed set would make FSR
     * availability depend on which DSU executes the access.
     */
    unsigned int fsr_failed_dsu = 0U;
    uint32_t fsr_observed_start = 0U;
    uint32_t fsr_observed_end = 0U;

    if (!asimov_system_program_dsu_fsr_p0(
            &fsr_failed_dsu, &fsr_observed_start, &fsr_observed_end)) {
        FWK_LOG_CRIT("[ASIMOV SYSTEM] DSU P0 FSR strap FAILED");
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] DSU%u want 0x%05x..0x%05x",
            fsr_failed_dsu,
            (unsigned int)ASIMOV_DSU_P0_FSR_START_VALUE,
            (unsigned int)ASIMOV_DSU_P0_FSR_END_VALUE);
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] got 0x%05x..0x%05x",
            (unsigned int)fsr_observed_start,
            (unsigned int)fsr_observed_end);
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Halting boot before reset release");
        FWK_LOG_FLUSH();
        return FWK_E_DEVICE;
    }

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] DSU P0 FSR=0x%08x%08x DSUs=%u",
        (unsigned int)(ASIMOV_DSU_P0_FSR_BASE >> 32),
        (unsigned int)(ASIMOV_DSU_P0_FSR_BASE & UINT32_MAX),
        platform_get_cluster_count());

    /* ACP bases and publisher enable, before SPM leaves reset. */
    asimov_acp_configure(SCP_CMN_CFG_MGMT_BASE, ASIMOV_ACP_METADATA_BASE);

    /*
     * Every cluster needs ICINVAL/OUTER/TLBI broadcast on its CHI requester.
     * Write the complete SMP policy even when it matches POR. The helper
     * verifies reset holds and requested storage, then allows the minimum
     * delivery time. Cluster initialization samples the physical inputs.
     */
    struct asimov_dsu_policy_failure dsu_policy_failure;

    if (!asimov_dsu_policy_configure(&dsu_policy_failure)) {
        FWK_LOG_CRIT("[ASIMOV SYSTEM] DSU broadcast policy FAILED");
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] addr 0x%08x want 0x%03x got 0x%03x",
            (unsigned int)dsu_policy_failure.address,
            (unsigned int)dsu_policy_failure.expected,
            (unsigned int)dsu_policy_failure.observed);
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Halting boot before reset release");
        FWK_LOG_FLUSH();
        return FWK_E_DEVICE;
    }

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] DSU broadcast=0x%03x DEFAULTP=0 DSUs=%u",
        (unsigned int)CMN_DSU_MGMT_BROADCAST_SMP,
        (unsigned int)CMN_DSU_MGMT_DSU_COUNT);

    /*
     * XMS configuration chain, while XMS is held (asimov_cfg_chains.h). The
     * FVP has no configuration engines and faults the access, so a faulting
     * probe skips both chain loads, with one INFO line. A drain that never
     * finishes stops boot (asimov_system_cfg_failed()).
     */
    uint32_t cfg_probe;
    const bool cfg_engines = asimov_system_probe_read32(
        SCP_XMS_CFG_BASE + offsetof(xms_cfg_t, STATUS), &cfg_probe);

    if (!cfg_engines)
        FWK_LOG_INFO("[ASIMOV SYSTEM] XMS/SPM cfg skipped: no engines");
    else if (!asimov_cfg_load_xms(SCP_XMS_CFG_BASE, ASIMOV_CFG_ENGINE_POLLS))
        return asimov_system_cfg_failed();

    /*
     * Release every block from external reset except the two PCIe controller
     * subsystems. RESET_CTRL is 0x1FFFF at POR (all 17 blocks held: CMN, GIC,
     * DSU0..4, XMS, CPS, TWS, SLS, SPM, C2C, HRA, SMS, and PCIe0..1). The
     * arbiter's per-output 2-flop CDC takes care of synchronising into each
     * subsystem's clock domain. We do this in mod_init so the resets are
     * released before any other module's start() phase touches the
     * corresponding subsystem (notably cmn_cyprus_start).
     *
     * hold_pcie[16:15] stay asserted (RESET_CTRL_BOOT_HOLD_MASK): each
     * controller leaves reset only when its owner releases it through the
     * reset-control API, after programming what must precede the release.
     * HRA is released here, so the always-on PCIe register blocks are
     * reachable while the controllers are held. PCIe PERST# remains an
     * independent host-controlled input.
     */
    const volatile uint32_t *reset_status = asimov_system_ctx.reset_ctrl.status;

    FWK_LOG_INFO(
        "[ASIMOV SYSTEM] Releasing subsystem resets (PCIe0-1 held)");
    asimov_reset_ctrl_boot(
        &asimov_system_ctx.reset_ctrl, RESET_CTRL_BOOT_HOLD_MASK);

    uint32_t status = *reset_status & RESET_CTRL_ALL;
    if (status != RESET_CTRL_BOOT_HOLD_MASK) {
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] Reset deassert failed; RESET_STATUS = 0x%05x",
            (unsigned int)status);
    } else {
        FWK_LOG_INFO("[ASIMOV SYSTEM] Subsystem resets released");
    }

    /*
     * SPM configuration chain: its 2-wire transport is in the SPM reset
     * domain, so wait until SPM reads released (the release is only a
     * request), then for the release to reach the transport pipes (the RTL
     * boot test's 500-iteration settle), then load.
     */
    if (cfg_engines) {
        unsigned int i;

        for (i = 0; (*reset_status & RESET_CTRL_SPM) != 0U; i++) {
            if (i == ASIMOV_CFG_ENGINE_POLLS)
                return asimov_system_cfg_failed();
        }
        for (i = 0; i < 500U; i++)
            (void)*reset_status;
        if (!asimov_cfg_load_spm(SCP_SPM_RDT_CFG_BASE, ASIMOV_CFG_ENGINE_POLLS))
            return asimov_system_cfg_failed();
    }

    /*
     * Poll cmn_cfg_mgmt.CMN_STATUS.ready before the first mesh/HN-D access.
     * That access is issued later by cmn_cyprus_start (a separate module's
     * start() phase), so polling at the end of asimov_system mod_init runs
     * first. Read over the local M7 APB sideband (0x44004000) — independent of
     * the HN-D mesh path itself. CMN reset was just released above; the logic
     * domain sets ready after its P-channel ON handshake.
     */
    volatile uint32_t *cmn_status = (volatile uint32_t *)(
        SCP_CMN_CFG_MGMT_BASE + CMN_CFG_MGMT_CMN_STATUS);
    /*
     * Iteration budget, not wall-clock — see
     * ASIMOV_CMN_STATUS_READY_SPIN_LIMIT for why no timebase exists yet.
     *
     * CMN_STATUS sits on the same page as the CFGM_PERIPHBASE strap, so an
     * individual read can be dropped and return stale prdata (asimov#2938). A
     * poll loop is self-correcting — it simply re-reads until ready sets — but
     * the value printed on the failure path can be a stale sample, so treat it
     * as indicative rather than authoritative.
     */
    uint32_t cmn_st = 0U;
    if (!asimov_cmn_wait_ready(cmn_status,
            ASIMOV_CMN_STATUS_READY_SPIN_LIMIT, &cmn_st)) {
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] CMN not ready: status=0x%08x",
            (unsigned int)cmn_st);
        FWK_LOG_CRIT("[ASIMOV SYSTEM] Halting before mesh access");
        FWK_LOG_FLUSH();
        return FWK_E_DEVICE;
    } else {
        FWK_LOG_INFO("[ASIMOV SYSTEM] CMN logic domain ready");
    }

    /*
     * Publish MODINIT_DONE only when subsystem resets have also settled.
     * CMN readiness is already mandatory above. BOOT_STATUS must not advance
     * to 0x2 when another subsystem's reset remains asserted.
     *
     * RESET_STATUS is re-sampled here rather than reusing the immediate
     * post-write readback above: the arbiter's per-output 2-flop CDC can
     * lag the RESET_CTRL_BOOT_HOLD_MASK write, and the CMN_STATUS poll has
     * since provided ample settling time. A transient deassert lag must not
     * permanently suppress the 0x2 marker when resets did release and
     * boot proceeded.
     */
    if ((*reset_status & RESET_CTRL_ALL) == RESET_CTRL_BOOT_HOLD_MASK &&
        (cmn_st & CMN_STATUS_READY) != 0U) {
        asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_MODINIT_DONE);
    }

    /*
     * Read clk_core back from CAR (read-only; see the provider below). The
     * Fixed ramp may still be running this early after POR, so a consumer
     * that needs the rate reads again on its own tick.
     */
    (void)mod_asimov_system_refresh_clk_core();

    return FWK_SUCCESS;
}

/*
 * clk_core provider (asimov-scp-firmware #151 decision (b)): read-only, over
 * the M7's PLL agent at SCP_PLL_AGENT_BASE (asimov_pll_query.h). When it
 * reads and what it publishes is asimov_clk_provider.c; this file supplies
 * the register access and the fault-surviving probe, and logs.
 *
 * The first access to the agent is the probe: the FVPs map nothing at
 * 0x4408_xxxx (terminus #335), and a plain read there is a precise BusFault
 * that stops the M7 before the AP boots. A faulting agent leaves clk_core
 * unknown for good and logs at ERR; it is never replaced by a default rate.
 * A silent agent (the emulation benches tie the link off) also leaves
 * clk_core unknown for good, after one frame.
 */

/*
 * STATUS reads per frame, first for tx_busy to clear, then for resp_valid.
 * A one-word READ and a three-word response take about 120 link clocks
 * (19 a word, CRC word included; car_1b_transmitter.sv), about 1.2 us with
 * clk_core on its 100 MHz reference, and a STATUS read takes a few hclk
 * (clk_core/2) cycles. 2048 is a wide margin. A silent agent spends it
 * once; an agent stuck busy, or a lost response, spends it on a read after
 * which the provider backs off (asimov_clk_provider.h).
 */
#define ASIMOV_PLL_QUERY_POLLS 2048U

static uint32_t asimov_pll_mmio_read(uintptr_t addr)
{
    return *(volatile uint32_t *)addr;
}

static void asimov_pll_mmio_write(uintptr_t addr, uint32_t value)
{
    *(volatile uint32_t *)addr = value;
    __DSB();
}

static const struct asimov_pll_io asimov_pll_mmio = {
    .read = asimov_pll_mmio_read,
    .write = asimov_pll_mmio_write,
};

static const struct asimov_pll_query_cfg asimov_pll_query_cfg = {
    .agent_base = SCP_PLL_AGENT_BASE,
    .resp_polls = ASIMOV_PLL_QUERY_POLLS,
};

/*
 * Read a register the M7 may not reach. With FAULTMASK set, CCR.BFHFNMIGN
 * makes the core ignore a precise data bus fault on the load and record it
 * in CFSR (ARMv7-M CCR.BFHFNMIGN), so the read reports the fault instead of
 * taking it. On the pinned FVP a read of the agent's STATUS returns 0 with
 * CFSR PRECISERR and BFARVALID set.
 */
static bool asimov_system_probe_read32(uintptr_t addr, uint32_t *value)
{
    const uint32_t bus_faults = SCB_CFSR_PRECISERR_Msk |
        SCB_CFSR_IMPRECISERR_Msk | SCB_CFSR_BFARVALID_Msk;
    uint32_t ccr = SCB->CCR;
    bool ok;

    __disable_fault_irq();
    SCB->CFSR = bus_faults;
    SCB->CCR = ccr | SCB_CCR_BFHFNMIGN_Msk;
    __DSB();
    __ISB();
    *value = *(volatile uint32_t *)addr;
    __DSB();
    ok = (SCB->CFSR & bus_faults) == 0U;
    SCB->CFSR = bus_faults;
    SCB->CCR = ccr;
    __DSB();
    __ISB();
    __enable_fault_irq();

    return ok;
}

static const struct asimov_clk_provider_io asimov_clk_provider_io = {
    .pll = &asimov_pll_mmio,
    .cfg = &asimov_pll_query_cfg,
    .probe = asimov_system_probe_read32,
};

/* Log what a read that published nothing found (only when it changed). */
static void asimov_system_log_clk_core(const struct asimov_pll_reading *r)
{
    if (r->result != ASIMOV_PLL_QUERY_DONE) {
        FWK_LOG_WARN(
            "[ASIMOV SYSTEM] clk_core unknown: CAR read %s",
            asimov_pll_query_result_name(r->result));
        return;
    }
    if (r->verdict == ASIMOV_PLL_VERDICT_MISMATCH) {
        FWK_LOG_ERR(
            "[ASIMOV SYSTEM] clk_core unknown: %s",
            asimov_pll_verdict_name(r->verdict));
    } else {
        FWK_LOG_WARN(
            "[ASIMOV SYSTEM] clk_core unknown: %s",
            asimov_pll_verdict_name(r->verdict));
    }
    FWK_LOG_WARN(
        "[ASIMOV SYSTEM] CAR st0 0x%04x words 0x%04x 0x%04x 0x%04x",
        (unsigned int)r->state.status0, (unsigned int)r->state.applied[0],
        (unsigned int)r->state.applied[1], (unsigned int)r->state.applied[2]);
}

const struct mod_asimov_system_clk_core *mod_asimov_system_get_clk_core(void)
{
    return &asimov_system_ctx.clk_provider.clk;
}

const struct mod_asimov_system_clk_core *mod_asimov_system_refresh_clk_core(void)
{
    struct asimov_clk_provider *provider = &asimov_system_ctx.clk_provider;
    struct asimov_pll_reading reading;

    switch (asimov_clk_provider_refresh(
        provider, &asimov_clk_provider_io, &reading)) {
    case ASIMOV_CLK_REFRESH_ABSENT:
        FWK_LOG_ERR("[ASIMOV SYSTEM] CAR agent bus error: clk_core unknown");
        break;
    case ASIMOV_CLK_REFRESH_SILENT:
        FWK_LOG_WARN("[ASIMOV SYSTEM] CAR agent silent: clk_core unknown");
        break;
    case ASIMOV_CLK_REFRESH_UNKNOWN:
        asimov_system_log_clk_core(&reading);
        break;
    case ASIMOV_CLK_REFRESH_PUBLISHED:
        FWK_LOG_INFO(
            "[ASIMOV SYSTEM] clk_core %lu MHz from the Fixed PLL, final",
            (unsigned long)(reading.hz / 1000000U));
        break;
    default:
        break;
    }

    return &provider->clk;
}

/*
 * Reset-control API. Only the blocks in RESET_CTRL_RUNTIME_MASK change after
 * boot; asimov_reset_ctrl_set() refuses the rest with FWK_E_ACCESS.
 */
static int asimov_system_reset_hold(enum mod_asimov_system_reset_block block)
{
    return asimov_reset_ctrl_set(
        &asimov_system_ctx.reset_ctrl, (unsigned int)block, true);
}

static int asimov_system_reset_release(
    enum mod_asimov_system_reset_block block)
{
    return asimov_reset_ctrl_set(
        &asimov_system_ctx.reset_ctrl, (unsigned int)block, false);
}

static int asimov_system_reset_status(
    enum mod_asimov_system_reset_block block,
    bool *held)
{
    return asimov_reset_ctrl_held(
        &asimov_system_ctx.reset_ctrl, (unsigned int)block, held);
}

static const struct mod_asimov_system_reset_ctrl_api
    asimov_system_reset_ctrl_api = {
        .hold = asimov_system_reset_hold,
        .release = asimov_system_reset_release,
        .status = asimov_system_reset_status,
    };

void asimov_system_ocm_checkpoint_reached(void)
{
    asimov_system_ctx.ocm_checkpoint = true;
    FWK_LOG_INFO("[ASIMOV SYSTEM] OCM checkpoint passed");
}

unsigned int asimov_system_hemisphere(void)
{
    return asimov_system_ctx.hemi_id;
}

static bool asimov_system_ocm_checkpoint_passed(void)
{
    return asimov_system_ctx.ocm_checkpoint;
}

static const struct mod_asimov_system_boot_api asimov_system_boot_api = {
    .ocm_checkpoint_passed = asimov_system_ocm_checkpoint_passed,
};

static int asimov_system_bind(fwk_id_t id, unsigned int round)
{
    if (round > 0)
        return FWK_SUCCESS;

    return fwk_module_bind(
        FWK_ID_MODULE(FWK_MODULE_IDX_POWER_DOMAIN),
        FWK_ID_API(FWK_MODULE_IDX_POWER_DOMAIN, MOD_PD_API_IDX_RESTRICTED),
        &asimov_system_ctx.pd_restricted_api);
}

static int asimov_system_process_bind_request(
    fwk_id_t requester_id,
    fwk_id_t pd_id,
    fwk_id_t api_id,
    const void **api)
{
    switch (fwk_id_get_api_idx(api_id)) {
    case MOD_ASIMOV_SYSTEM_API_IDX_SYSTEM_POWER_DRIVER:
        *api = &asimov_system_power_driver_api;
        break;
    case MOD_ASIMOV_SYSTEM_API_IDX_RESET_CTRL:
        *api = &asimov_system_reset_ctrl_api;
        break;
    case MOD_ASIMOV_SYSTEM_API_IDX_BOOT:
        *api = &asimov_system_boot_api;
        break;
    default:
        return FWK_E_PARAM;
    }

    return FWK_SUCCESS;
}

static int asimov_system_start(fwk_id_t id)
{
    int status;
    unsigned int core_pd_idx;

    /*
     * Force the boot banner to print whatever the log level. The framework
     * emits it lazily on the first FWK_LOG at/above the active level. BL2
     * logs at INFO or finer in both build modes (scp_ramfw/Firmware.cmake),
     * so its INFO lines would print it too; this CRIT line keeps the banner
     * independent of that setting, as BL1's does at its release level of
     * WARN. CRIT is always compiled in. See
     * product/asimov/scp_ramfw/include/fmw_log.h.
     */
    FWK_LOG_CRIT("[ASIMOV SYSTEM] SCP RAM firmware (BL2) starting");
    asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_START_ENTRY);

    status = asimov_ras_handlers_install();
    if (status != FWK_SUCCESS) {
        FWK_LOG_ERR(
            "[ASIMOV SYSTEM] RAS handler install failed (%d)", status);
        return status;
    }

    status = asimov_cti_handlers_install();
    if (status != FWK_SUCCESS) {
        FWK_LOG_ERR(
            "[ASIMOV SYSTEM] CTI handler install failed (%d)", status);
        return status;
    }

    /*
     * Enable the system counter now that RNSAM is up (CMN ran its start()
     * before ours). Must precede AP core release so CNTPCT is live when the
     * AP first reads it. See asimov_system_enable_sys_counter().
     */
    asimov_system_enable_sys_counter();
    asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_SYSCNT_DONE);

    /*
     * Subscribe to the post-transition power-state notification for every
     * core PD element. Triggered both for the cold-boot primary (when
     * asimov_system_process_event → set_state ON completes its cascade)
     * and for every runtime CPU_ON-driven secondary. See
     * asimov_system_pin_core_static_on() for the why.
     *
     * Element indices 0..(NUMBER_OF_CLUSTERS*CORES_PER_CLUSTER - 1) are
     * core PDs per the tree in config_power_domain.c (cores first, then
     * clusters, then SYSTOP).
     */
    for (core_pd_idx = 0;
         core_pd_idx < NUMBER_OF_CLUSTERS * CORES_PER_CLUSTER;
         core_pd_idx++) {
        status = fwk_notification_subscribe(
            mod_pd_notification_id_power_state_transition,
            FWK_ID_ELEMENT(FWK_MODULE_IDX_POWER_DOMAIN, core_pd_idx),
            id);
        if (status != FWK_SUCCESS) {
            FWK_LOG_ERR(
                "[ASIMOV SYSTEM] PD transition subscribe failed, core %u (%d)",
                core_pd_idx, status);
            return status;
        }
    }

    /*
     * Post a self-targeted event to trigger AP core release during the
     * runtime event loop. We can't call init_primary_core() directly
     * from start() because the power_domain set_state API requires the
     * event queue to be running.
     *
     * By the time start() runs, all modules are initialized and the CMN
     * RNSAM is programmed (CMN runs during its own start() phase, which
     * happens before ours since CMN is earlier in the module list).
     */
    struct fwk_event event = {
        .source_id = id,
        .target_id = id,
        .id = FWK_ID_EVENT(FWK_MODULE_IDX_ASIMOV_SYSTEM, 0),
    };

    /*
     * Publish AP_EVENT_POSTED — and its log line — only once the event is
     * actually queued: a failed fwk_put_event must leave neither BOOT_STATUS
     * nor the boot log claiming the AP-boot event was scheduled (the log
     * marker and the stage code are correlated by the boot-status tests).
     */
    status = fwk_put_event(&event);
    if (status == FWK_SUCCESS) {
        FWK_LOG_INFO("[ASIMOV SYSTEM] Scheduling AP boot (event posted)");
        asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_AP_EVENT_POSTED);
    }

    return status;
}

static int asimov_system_process_event(
    const struct fwk_event *event,
    struct fwk_event *resp_event)
{
    int status;

    FWK_LOG_INFO("[ASIMOV SYSTEM] Processing AP boot event...");
    asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_AP_EVENT_RUN);

    /*
     * Program only the DVM registers before power-up. Hardware SCI is the
     * CMN reset-default interface, and each DSU owns its wired SYSCOREQ/ACK
     * handshake during the PPU ON transition. Firmware must not write the
     * mutually-exclusive software SCI controls; this path does not claim to
     * observe whether the hardware handshake has completed.
     */
    status = asimov_cmn_dvm_program();
    if (status != FWK_SUCCESS) {
        FWK_LOG_ERR(
            "[ASIMOV SYSTEM] CMN DVM programming failed, AP held (%d)",
            status);
        return status;
    }

    asimov_system_set_boot_stage(ASIMOV_BOOT_STAGE_DVM_DONE);

    /*
     * HN-S -> SMS route overrides and HN-S POCQ class caps, while the mesh
     * is still idle. A failure with verified plain XY routing / reset caps is
     * functionally correct, so it is reported and the boot continues. An
     * unverified routing state (FWK_E_STATE) may leave a stale override table
     * active; it is reported at CRIT and the boot still continues.
     */
    status = asimov_cmn_mesh_qos_program();
    if (status == FWK_E_STATE) {
        FWK_LOG_CRIT(
            "[ASIMOV SYSTEM] CMN mesh routing unverified, booting on (%d)",
            status);
    } else if (status != FWK_SUCCESS) {
        FWK_LOG_ERR(
            "[ASIMOV SYSTEM] CMN mesh QoS programming incomplete (%d)",
            status);
    }

    return asimov_system_init_primary_core();
}

static int asimov_system_process_notification(
    const struct fwk_event *event,
    struct fwk_event *resp_event)
{
    struct mod_pd_power_state_transition_notification_params *params =
        (struct mod_pd_power_state_transition_notification_params *)event->params;

    if (params->state != MOD_PD_STATE_ON)
        return FWK_SUCCESS;

    /*
     * source_id is the core PD element. We subscribed only for core PDs
     * (indices 0..(NUMBER_OF_CLUSTERS*CORES_PER_CLUSTER - 1)), so the
     * element index is the core_pd_idx for
     * asimov_system_pin_core_static_on().
     */
    unsigned int core_pd_idx = fwk_id_get_element_idx(event->source_id);

    asimov_system_pin_core_static_on(core_pd_idx);

    /* Core ON implies its cluster is ON — the CME PPU is now accessible. */
    asimov_system_enable_cme_dynamic(core_pd_idx / CORES_PER_CLUSTER);

    /*
     * This notification is delivered after the core PD reaches ON, so its
     * cluster's DSU (RN-F) is powered and can answer DVM broadcasts. Admit it
     * to HN-D DVM domain 0 now. The bitmap is indexed by hardware LDID, which
     * is strapped per crosspoint and is NOT the cluster index — see
     * CLUSTER_TO_RNF_LDID_INIT in cmn_node_id.h. Idempotence makes the second
     * core notification harmless. This post-power update neither drives nor
     * proves completion of the separate hardware SCI handshake.
     */
    {
        static const unsigned int cluster_to_rnf_ldid[] =
            CLUSTER_TO_RNF_LDID_INIT;
        unsigned int cluster = core_pd_idx / CORES_PER_CLUSTER;

        if (cluster < FWK_ARRAY_SIZE(cluster_to_rnf_ldid)) {
            asimov_cmn_dvm_add_member(cluster_to_rnf_ldid[cluster]);
        } else {
            FWK_LOG_ERR(
                "[ASIMOV SYSTEM] cluster %u out of range for LDID map",
                cluster);
        }
    }

    return FWK_SUCCESS;
}

const struct fwk_module module_asimov_system = {
    .type = FWK_MODULE_TYPE_DRIVER,
    .event_count = 1,
    .api_count = MOD_ASIMOV_SYSTEM_API_COUNT,
    .init = asimov_system_mod_init,
    .bind = asimov_system_bind,
    .process_bind_request = asimov_system_process_bind_request,
    .start = asimov_system_start,
    .process_event = asimov_system_process_event,
    .process_notification = asimov_system_process_notification,
};
