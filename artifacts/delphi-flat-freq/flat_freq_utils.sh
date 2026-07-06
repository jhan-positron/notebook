#!/usr/bin/env bash
# flat_freq_utils.sh (v3, 2026-07-06) — flat-frequency utilities for the
# delphi Xeon 6962P hosts.
#
# Usage:
#   source flat_freq_utils.sh
#   flat_freq_apply                    # all 144 cores flat-high
#   flat_freq_apply "27-46,51-70,75-94,99-118"
#                                      # 2-tier: listed cores (+HT siblings,
#                                      # added automatically) flat-high
#                                      # ~4100; ALL other cores flat-low
#                                      # (2700 MHz clip)
#   flat_freq_apply_tiers "27-46,51-70,75-94,99-118" "0,24-26,48-50,72-74,96-98"
#                                      # 3-tier: arg1 (+sibs) fast ~4100
#                                      # (CLOS0/TF-on); arg2 (+sibs) mid
#                                      # <=3900 (CLOS1); rest low <=2700
#                                      # (CLOS3). Example args = TRON app
#                                      # cores / TRON aux (TX,RX,rinzler,
#                                      # platform) cores.
#   flat_freq_revert                   # restore boot-default (PCT baseline)
#   flat_freq_status                   # show current SST/CLOS state
#   flat_freq_check                    # precondition checks only
#
# v3 addition (2026-07-06): flat_freq_apply_tiers — 3-tier shapes using
#   CLOS1 (800-3900) as a middle tier. MEASURED CONSTRAINT: the TF fast
#   tier grants 4100 whenever any other core runs >2700; 4400 needs ALL
#   others <=2700; there is no 4200 rung (ALLCORE_CEILING doc 2.5/2.6).
#   Benchmarked 2026-07-06 (gpt-oss + llama-8b, baseline grid): 3-tier ==
#   2-tier select mode within noise — the mid tier bought nothing for
#   those models; kept for workloads that load the aux cores harder.
#
# v2 changes vs v1 (evidence: workspace debug_3bda/
# ALLCORE_CEILING_HETERO_CLAUDE_20260702.md and e1e2_beat80_* run):
#   - turbo-freq is left ENABLED (boot default), not disabled: measured
#     back-to-back at the 80-core TRON shape this is 4100 MHz flat vs
#     3900 with the old disable recipe (+200 MHz). The TF high-priority
#     bucket applies to CLOS0 members and bypasses the TRL active-core
#     bucket, so no BIOS C-state change is needed either.
#   - selective mode: boost cores -> CLOS0 (2700-4400), everything else ->
#     CLOS3 (clipped at 2700). HT siblings of boost cores are always
#     included (threads of one core share the clock).
#   - CLOS0 and CLOS3 configs are explicitly (re)pinned on every apply:
#     `turbo-freq enable --auto` wipes ALL CLOS configs and `core-power
#     enable` resets CLOS2/CLOS3, so boot values cannot be assumed.
#     NEVER run `core-power enable` from these utilities.
#   - isst binary auto-detection: NOPASSWD sudo covers different paths per
#     host (3bda: /opt copy; 3af6: the workspace build).
#
# Expected frequencies under load (SSE/scalar; measured 2026-07-02..06):
#   <= ~20 busy cores per 24-core power domain (e.g. the TRON 80-core
#   shape): 4100 MHz flat (~4050 when both HT threads of each core work).
#   Whole-machine loads: package-power-bound ~3.2-3.6 GHz, still flat.
#   Selective (2-tier) mode: non-boost cores <= 2700 MHz.
#   3-tier mode: mid cores pinned at their 3900 cap when busy (measured
#   3888-3900), low cores <= 2700.
#
# Functions return non-zero on failure. Preconditions are only CHECKED here;
# fixing them (sudoers, modules, binary) is deliberately left to the admin.

FLAT_FREQ_ISST_CANDIDATES=(
    "${FLAT_FREQ_ISST:-}"
    /opt/intel-speed-select/intel-speed-select
    /home/jhan/workspace/intel-vs-amd/speed-select/workspace/intel-speed-select/intel-speed-select
)
FLAT_FREQ_ISST=""   # resolved by flat_freq_check

# One anchor CPU per power domain (6 domains: 3 per socket, 24 cores each).
FLAT_FREQ_ANCHORS=(0 24 48 72 96 120)
FLAT_FREQ_NCPU=288
FLAT_FREQ_CPU_MODEL="6962P"

# Boot-default CLOS partition, verified identical on delphi-3af6 and
# delphi-3bda (flat_freq_closfix runs of 2026-07-02): 16 PCT cores per
# package plus their HT siblings in CLOS0, everything else in CLOS3.
FLAT_FREQ_BOOT_CLOS0_RANGES=(0-1 18-19 36-37 54-55 72-73 90-91 108-109 126-127
                             144-145 162-163 180-181 198-199 216-217 234-235 252-253 270-271)
FLAT_FREQ_BOOT_CLOS3_RANGES=(2-17 20-35 38-53 56-71 74-89 92-107 110-125 128-143
                             146-161 164-179 182-197 200-215 218-233 236-251 254-269 272-287)

# Verification probes spanning both packages and HT siblings.
FLAT_FREQ_PROBES_BOOT_CLOS3=(2 50 74 143 200 280)
FLAT_FREQ_PROBES_BOOT_CLOS0=(0 36 108 127 180 271)

# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

_flat_freq_isst() {
    # intel-speed-select prints its results to stderr; fold it into stdout.
    if [[ ${EUID} -eq 0 ]]; then
        "${FLAT_FREQ_ISST}" "$@" 2>&1
    else
        sudo -n "${FLAT_FREQ_ISST}" "$@" 2>&1
    fi
}

_flat_freq_get_assoc() {
    local clos
    clos=$(_flat_freq_isst --cpu "$1" core-power get-assoc \
            | grep -oE 'clos:[0-9]+' | head -1 | cut -d: -f2) || true
    echo "${clos:-ERR}"
}

_flat_freq_assoc_counts() {
    # one ranged call; echoes e.g. "clos0=160 clos3=128"
    _flat_freq_isst --cpu 0-$((FLAT_FREQ_NCPU - 1)) core-power get-assoc \
        | grep -oE 'clos:[0-9]+' | sort | uniq -c \
        | awk '{printf "%sclos%s=%s", (NR>1?" ":""), substr($2,6), $1} END {print ""}'
}

_flat_freq_tf_state() {
    local st
    st=$(_flat_freq_isst --cpu "$1" perf-profile info \
            | grep -m1 -oE 'speed-select-turbo-freq:(enabled|disabled)' | cut -d: -f2) || true
    echo "${st:-ERR}"
}

_flat_freq_cmd_ok() {
    # _flat_freq_cmd_ok <output> <success-marker> <expected-count>
    local out="$1" marker="$2" want="$3" got lower
    got=$(printf '%s\n' "${out}" | grep -c "${marker}") || true
    lower="${out,,}"
    [[ "${got}" -eq "${want}" && "${lower}" != *fail* && "${lower}" != *error* ]]
}

_flat_freq_expand() {
    # "27-30,51" -> one cpu per line
    local tok
    for tok in ${1//,/ }; do
        if [[ "${tok}" == *-* ]]; then
            seq "${tok%-*}" "${tok#*-}"
        else
            echo "${tok}"
        fi
    done
}

_flat_freq_compress() {
    # cpu-per-line on stdin -> "a-b c d-e" range segments on one line
    sort -n | uniq | awk '
        NR==1 {s=$1; p=$1; next}
        $1 == p+1 {p=$1; next}
        {printf "%s ", (s==p ? s : s "-" p); s=$1; p=$1}
        END {if (NR) printf "%s\n", (s==p ? s : s "-" p)}'
}

_flat_freq_add_siblings() {
    # cpu-per-line on stdin -> cpus + their HT siblings (sysfs; +144 fallback)
    local cpu line
    while read -r cpu; do
        if line=$(cat "/sys/devices/system/cpu/cpu${cpu}/topology/thread_siblings_list" 2>/dev/null); then
            _flat_freq_expand "${line}"
        else
            echo "${cpu}"; echo $(( (cpu + FLAT_FREQ_NCPU / 2) % FLAT_FREQ_NCPU ))
        fi
    done | sort -n | uniq
}

_flat_freq_pin_configs() {
    # (re)pin CLOS0 fast window + CLOS3 slow clip on every power domain
    local cpu out rc=0
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 0 --weight 0 --min 2700 --max 4400) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos0 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 3 --weight 0 --min 800 --max 2700) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos3 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
    done
    return ${rc}
}

_flat_freq_assoc_segments() {
    # _flat_freq_assoc_segments <clos> <seg> [<seg>...]
    local clos="$1" seg out rc=0 n
    shift
    for seg in "$@"; do
        [[ -n "${seg}" ]] || continue
        if [[ "${seg}" == *-* ]]; then n=$(( ${seg#*-} - ${seg%-*} + 1 )); else n=1; fi
        out=$(_flat_freq_isst --cpu "${seg}" core-power assoc --clos "${clos}") || true
        _flat_freq_cmd_ok "${out}" 'assoc:success' "${n}" \
            || { echo "[FAIL] assoc clos${clos} ${seg}:"; printf '%s\n' "${out}" | head -6; rc=1; }
    done
    return ${rc}
}

# ---------------------------------------------------------------------------
# precondition checks (check only — print instructions, never fix)
# ---------------------------------------------------------------------------

flat_freq_check() {
    local ok=0

    local ncpu model
    ncpu=$(nproc 2>/dev/null) || ncpu=0
    model=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null) || model="unknown"
    if [[ "${ncpu}" -ne ${FLAT_FREQ_NCPU} || "${model}" != *"${FLAT_FREQ_CPU_MODEL}"* ]]; then
        echo "[FAIL] wrong machine: expected ${FLAT_FREQ_NCPU} logical CPUs on Xeon ${FLAT_FREQ_CPU_MODEL}"
        echo "       detected: ${ncpu} CPUs, ${model#*: }"
        echo "       Refusing to continue on this machine."
        return 1
    fi
    echo "[ ok ] machine: ${ncpu} CPUs, Xeon ${FLAT_FREQ_CPU_MODEL}"

    # binary auto-detection: first candidate that exists AND is runnable
    # (as root, or via passwordless sudo)
    FLAT_FREQ_ISST=""
    local cand
    for cand in "${FLAT_FREQ_ISST_CANDIDATES[@]}"; do
        [[ -n "${cand}" && -x "${cand}" ]] || continue
        if [[ ${EUID} -eq 0 ]] || sudo -n "${cand}" --version >/dev/null 2>&1; then
            FLAT_FREQ_ISST="${cand}"
            break
        fi
    done
    if [[ -z "${FLAT_FREQ_ISST}" ]]; then
        echo "[FAIL] no usable intel-speed-select binary (checked existence +"
        echo "       root/passwordless-sudo for each of):"
        for cand in "${FLAT_FREQ_ISST_CANDIDATES[@]}"; do
            [[ -n "${cand}" ]] && echo "         ${cand}"
        done
        echo "       Fix: build/copy a binary to one of those paths and add a"
        echo "       sudoers entry for that EXACT path, e.g.:"
        echo "         echo 'jhan ALL=(root) NOPASSWD: <path>' | \\"
        echo "           sudo tee /etc/sudoers.d/isst-flat-freq"
        ok=1
    else
        echo "[ ok ] binary: ${FLAT_FREQ_ISST} (root/NOPASSWD verified)"
    fi

    if [[ ! -e /dev/isst_interface ]]; then
        echo "[FAIL] /dev/isst_interface does not exist (ISST kernel modules not loaded)."
        echo "       To fix (as admin): sudo modprobe isst_if_mbox_pci isst_if_mmio isst_tpmi msr"
        ok=1
    else
        echo "[ ok ] /dev/isst_interface present"
    fi

    if [[ ${ok} -ne 0 ]]; then
        echo
        echo "Preconditions NOT met — fix the [FAIL] items above and re-run."
        return 1
    fi
    echo "All preconditions met."
    return 0
}

# ---------------------------------------------------------------------------
# apply flat frequency
#   flat_freq_apply              all cores flat-high
#   flat_freq_apply <cpulist>    listed cores (+HT siblings) high, rest low
# ---------------------------------------------------------------------------

flat_freq_apply() {
    flat_freq_check || return 1

    local boost_arg="${1:-}" cpu out rc=0
    local mode boost_cpus boost_segs slow_segs nboost

    if [[ -n "${boost_arg}" ]]; then
        mode="select"
        boost_cpus=$(_flat_freq_expand "${boost_arg}" | _flat_freq_add_siblings)
        while read -r cpu; do
            if (( cpu < 0 || cpu >= FLAT_FREQ_NCPU )); then
                echo "[FAIL] cpu ${cpu} out of range 0-$((FLAT_FREQ_NCPU - 1))"; return 1
            fi
        done <<< "${boost_cpus}"
        nboost=$(wc -l <<< "${boost_cpus}")
        boost_segs=$(_flat_freq_compress <<< "${boost_cpus}")
        slow_segs=$( { seq 0 $((FLAT_FREQ_NCPU - 1)); echo "${boost_cpus}"; echo "${boost_cpus}"; } \
                     | tr ' ' '\n' | sort -n | uniq -u | _flat_freq_compress )
        echo
        echo "== SELECTIVE flat freq: ${nboost} CPUs high (incl. HT siblings), $((FLAT_FREQ_NCPU - nboost)) low =="
        echo "   high (CLOS0, 2700-4400): ${boost_segs}"
        echo "   low  (CLOS3, <=2700):    ${slow_segs}"
    else
        mode="all"
        nboost=${FLAT_FREQ_NCPU}
        echo
        echo "== ALL-CORES flat freq: ${FLAT_FREQ_NCPU} CPUs -> CLOS0 (2700-4400) =="
    fi

    echo "== turbo-freq ENABLE (v2: TF stays on; +200 MHz vs the old disable recipe) =="
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        out=$(_flat_freq_isst --cpu "${cpu}" turbo-freq enable) || true
        _flat_freq_cmd_ok "${out}" 'enable:success' 1 \
            || { echo "[FAIL] turbo-freq enable on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power disable) || true
        _flat_freq_cmd_ok "${out}" 'disable:success' 1 \
            || { echo "[FAIL] core-power disable on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
    done

    echo "== pinning CLOS0 (2700-4400) and CLOS3 (800-2700) configs =="
    _flat_freq_pin_configs || rc=1

    echo "== associating =="
    if [[ "${mode}" == "all" ]]; then
        out=$(_flat_freq_isst --cpu 0-$((FLAT_FREQ_NCPU - 1)) core-power assoc --clos 0) || true
        if ! _flat_freq_cmd_ok "${out}" 'assoc:success' "${FLAT_FREQ_NCPU}"; then
            echo "[FAIL] assoc did not report ${FLAT_FREQ_NCPU} successes:"
            echo "       success count: $(printf '%s\n' "${out}" | grep -c 'assoc:success')/${FLAT_FREQ_NCPU}"
            rc=1
        fi
    else
        # slow first, then the boost set
        # shellcheck disable=SC2086
        _flat_freq_assoc_segments 3 ${slow_segs} || rc=1
        # shellcheck disable=SC2086
        _flat_freq_assoc_segments 0 ${boost_segs} || rc=1
    fi

    echo "== verifying =="
    local tf a bad=0 counts
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        tf=$(_flat_freq_tf_state "${cpu}")
        [[ "${tf}" == "enabled" ]] || { echo "   [bad] turbo-freq on anchor ${cpu}: ${tf} (want enabled)"; bad=1; }
    done
    out=$(_flat_freq_isst --cpu 0 core-power get-config --clos 0) || true
    [[ "${out}" == *"clos-min:2700"* && "${out}" == *"clos-max:4400"* ]] \
        || { echo "   [bad] clos0 config not 2700-4400"; bad=1; }
    out=$(_flat_freq_isst --cpu 0 core-power get-config --clos 3) || true
    [[ "${out}" == *"clos-max:2700"* ]] \
        || { echo "   [bad] clos3 max not 2700"; bad=1; }
    counts=$(_flat_freq_assoc_counts)
    if [[ "${mode}" == "all" ]]; then
        [[ "${counts}" == "clos0=${FLAT_FREQ_NCPU}" ]] \
            || { echo "   [bad] assoc counts: ${counts} (want clos0=${FLAT_FREQ_NCPU})"; bad=1; }
    else
        [[ "${counts}" == "clos0=${nboost} clos3=$((FLAT_FREQ_NCPU - nboost))" ]] \
            || { echo "   [bad] assoc counts: ${counts} (want clos0=${nboost} clos3=$((FLAT_FREQ_NCPU - nboost)))"; bad=1; }
        a=$(_flat_freq_get_assoc "$(head -1 <<< "${boost_cpus}")")
        [[ "${a}" == "0" ]] || { echo "   [bad] first boost cpu assoc: clos ${a}"; bad=1; }
    fi

    if [[ ${bad} -eq 0 && ${rc} -eq 0 ]]; then
        echo "   turbo-freq enabled; configs pinned; assoc: ${counts}"
        echo "FLAT FREQUENCY APPLIED (${mode} mode)."
        if [[ "${mode}" == "all" ]]; then
            echo "Expect 4100 MHz flat up to ~20 busy cores per 24-core power domain;"
        else
            echo "Expect boost cores 4100 MHz flat (~4050 with both HT threads busy);"
            echo "non-boost cores <= 2700 MHz."
        fi
        echo "whole-machine loads are package-power-bound (~3.2-3.6 GHz, still flat)."
        echo "Validate:  sudo turbostat --quiet --show Package,Core,CPU,Busy%,Bzy_MHz -i 5 -n 2"
        echo "NOTE: state does not survive a reboot — re-run flat_freq_apply after boot."
    else
        echo "[FAIL] flat frequency NOT cleanly applied — inspect with flat_freq_status,"
        echo "       or run flat_freq_revert / reboot to return to a known state."
        rc=1
    fi
    return ${rc}
}

# ---------------------------------------------------------------------------
# revert flat frequency (restore boot-default PCT baseline)
# ---------------------------------------------------------------------------

flat_freq_revert() {
    flat_freq_check || return 1

    local cpu out rc=0

    echo
    echo "== restoring baseline SST state: turbo-freq enable + core-power disable + boot CLOS configs =="
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        out=$(_flat_freq_isst --cpu "${cpu}" turbo-freq enable) || true
        _flat_freq_cmd_ok "${out}" 'enable:success' 1 \
            || { echo "[FAIL] turbo-freq enable on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power disable) || true
        _flat_freq_cmd_ok "${out}" 'disable:success' 1 \
            || { echo "[FAIL] core-power disable on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        # `core-power enable` (direct or via `turbo-freq enable --auto`) resets
        # CLOS configs; restore all four boot values (25500 = ratio 255 = the
        # "Max Turbo frequency" sentinel).
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 0 --weight 0 --min 2700 --max 4400) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos0 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 1 --weight 0 --min 0 --max 25500) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos1 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 2 --weight 0 --min 0 --max 25500) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos2 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 3 --weight 0 --min 800 --max 2700) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos3 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
    done

    echo "== restoring boot-default CLOS partition =="
    _flat_freq_assoc_segments 3 "${FLAT_FREQ_BOOT_CLOS3_RANGES[@]}" || rc=1
    _flat_freq_assoc_segments 0 "${FLAT_FREQ_BOOT_CLOS0_RANGES[@]}" || rc=1

    echo "== verifying =="
    local a tf bad=0 counts
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        tf=$(_flat_freq_tf_state "${cpu}")
        [[ "${tf}" == "enabled" ]] || { echo "   [bad] turbo-freq on anchor ${cpu}: ${tf} (want enabled)"; bad=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power get-config --clos 3) || true
        [[ "${out}" == *"clos-max:2700"* ]] \
            || { echo "   [bad] clos3 max on anchor ${cpu} not 2700"; bad=1; }
    done
    for cpu in "${FLAT_FREQ_PROBES_BOOT_CLOS3[@]}"; do
        a=$(_flat_freq_get_assoc "${cpu}")
        [[ "${a}" == "3" ]] || { echo "   [bad] cpu ${cpu} assoc: clos ${a} (want 3)"; bad=1; }
    done
    for cpu in "${FLAT_FREQ_PROBES_BOOT_CLOS0[@]}"; do
        a=$(_flat_freq_get_assoc "${cpu}")
        [[ "${a}" == "0" ]] || { echo "   [bad] cpu ${cpu} assoc: clos ${a} (want 0)"; bad=1; }
    done
    counts=$(_flat_freq_assoc_counts)
    [[ "${counts}" == "clos0=32 clos3=256" ]] \
        || { echo "   [bad] assoc counts: ${counts} (want clos0=32 clos3=256)"; bad=1; }

    if [[ ${bad} -eq 0 && ${rc} -eq 0 ]]; then
        echo "   turbo-freq enabled; boot CLOS partition + configs restored (${counts})"
        echo "REVERTED to boot-default state (PCT baseline: 8 fast cores/pkg, rest capped at 2700 under load)."
    else
        echo "[FAIL] revert incomplete — inspect manually, or reboot to let BIOS"
        echo "       reprogram the boot-default partition."
        rc=1
    fi
    return ${rc}
}

# ---------------------------------------------------------------------------
# status (read-only)
# ---------------------------------------------------------------------------

flat_freq_status() {
    flat_freq_check || return 1

    echo
    local cpu tf a err=0 counts
    echo "== turbo-freq state per power domain =="
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        tf=$(_flat_freq_tf_state "${cpu}")
        echo "   anchor ${cpu}: ${tf}"
        [[ "${tf}" == "ERR" ]] && err=1
    done

    echo "== CLOS frequency caps (anchor 0) =="
    _flat_freq_isst --cpu 0 core-power get-config --clos 0 | grep -E 'clos-min|clos-max' | sed 's/^ */   clos0 /' || true
    _flat_freq_isst --cpu 0 core-power get-config --clos 3 | grep -E 'clos-min|clos-max' | sed 's/^ */   clos3 /' || true

    echo "== association distribution (all ${FLAT_FREQ_NCPU} CPUs) =="
    counts=$(_flat_freq_assoc_counts)
    echo "   ${counts}"

    echo
    case "${counts}" in
        "clos0=${FLAT_FREQ_NCPU}")
            echo "STATE: FLAT-ALL — every CPU in CLOS0; no 2700 MHz clamp." ;;
        "clos0=32 clos3=256")
            echo "STATE: BOOT-DEFAULT (PCT partition) — non-PCT cores capped at 2700 under load."
            echo "       Run flat_freq_apply [cpulist] to fix." ;;
        clos0=*\ clos3=*)
            echo "STATE: FLAT-SELECT — ${counts%% *} CPUs boosted (CLOS0), rest clipped at 2700." ;;
        *)
            echo "STATE: MIXED/UNKNOWN (${counts}) — inspect per-CPU with get-assoc." ;;
    esac
    [[ ${err} -eq 0 ]] || { echo "WARN: some isst reads failed (ERR above)."; return 1; }
    return 0
}

# ---------------------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "This file is meant to be sourced, not executed:"
    echo "  source ${0}"
    echo "  flat_freq_apply [cpulist] | flat_freq_revert | flat_freq_status | flat_freq_check"
    exit 1
fi

# ---------------------------------------------------------------------------
# 3-tier apply (v3 addition, 2026-07-06)
#   flat_freq_apply_tiers <fast_cpulist> <mid_cpulist>
#     fast (+HT sibs) -> CLOS0 (2700-4400, TF on)  ~4100 MHz under load
#     mid  (+HT sibs) -> CLOS1 (800-3900)          <= 3900 MHz
#     rest            -> CLOS3 (800-2700)          <= 2700 MHz
#   MEASURED CONSTRAINT: the TF fast tier grants 4100 whenever any other
#   core runs >2700; 4400 needs ALL others <=2700. There is no 4200 rung.
#   Revert with flat_freq_revert (re-assocs every cpu to the boot 0/3 map).
# ---------------------------------------------------------------------------

flat_freq_apply_tiers() {
    flat_freq_check || return 1
    local fast_arg="${1:-}" mid_arg="${2:-}" cpu out rc=0
    if [[ -z "${fast_arg}" || -z "${mid_arg}" ]]; then
        echo "usage: flat_freq_apply_tiers <fast_cpulist> <mid_cpulist>"; return 1
    fi

    local fast_cpus mid_cpus overlap fast_segs mid_segs low_segs nfast nmid
    fast_cpus=$(_flat_freq_expand "${fast_arg}" | _flat_freq_add_siblings)
    mid_cpus=$(_flat_freq_expand "${mid_arg}" | _flat_freq_add_siblings)
    while read -r cpu; do
        if (( cpu < 0 || cpu >= FLAT_FREQ_NCPU )); then
            echo "[FAIL] cpu ${cpu} out of range 0-$((FLAT_FREQ_NCPU - 1))"; return 1
        fi
    done <<< "${fast_cpus}"$'\n'"${mid_cpus}"
    overlap=$( { echo "${fast_cpus}"; echo "${mid_cpus}"; } | sort -n | uniq -d )
    if [[ -n "${overlap}" ]]; then
        echo "[FAIL] fast/mid overlap after HT-sibling expansion: $(_flat_freq_compress <<< "${overlap}")"
        return 1
    fi
    nfast=$(wc -l <<< "${fast_cpus}"); nmid=$(wc -l <<< "${mid_cpus}")
    fast_segs=$(_flat_freq_compress <<< "${fast_cpus}")
    mid_segs=$(_flat_freq_compress <<< "${mid_cpus}")
    low_segs=$( { seq 0 $((FLAT_FREQ_NCPU - 1)); echo "${fast_cpus}"; echo "${fast_cpus}"; \
                  echo "${mid_cpus}"; echo "${mid_cpus}"; } \
                | tr ' ' '\n' | sort -n | uniq -u | _flat_freq_compress )

    echo
    echo "== 3-TIER freq: ${nfast} fast / ${nmid} mid / $((FLAT_FREQ_NCPU - nfast - nmid)) low (HT sibs included) =="
    echo "   fast (CLOS0, 2700-4400, ~4100 under load): ${fast_segs}"
    echo "   mid  (CLOS1, 800-3900):                    ${mid_segs}"
    echo "   low  (CLOS3, 800-2700):                    ${low_segs}"

    echo "== turbo-freq ENABLE =="
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        out=$(_flat_freq_isst --cpu "${cpu}" turbo-freq enable) || true
        _flat_freq_cmd_ok "${out}" 'enable:success' 1 \
            || { echo "[FAIL] turbo-freq enable on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
        out=$(_flat_freq_isst --cpu "${cpu}" core-power disable) || true
        _flat_freq_cmd_ok "${out}" 'disable:success' 1 \
            || { echo "[FAIL] core-power disable on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
    done

    echo "== pinning CLOS0 (2700-4400), CLOS1 (800-3900), CLOS3 (800-2700) =="
    _flat_freq_pin_configs || rc=1
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        out=$(_flat_freq_isst --cpu "${cpu}" core-power config --clos 1 --weight 0 --min 800 --max 3900) || true
        _flat_freq_cmd_ok "${out}" 'config:success' 1 \
            || { echo "[FAIL] clos1 config on cpu ${cpu}:"; printf '%s\n' "${out}"; rc=1; }
    done

    echo "== associating =="
    # shellcheck disable=SC2086
    _flat_freq_assoc_segments 3 ${low_segs} || rc=1
    # shellcheck disable=SC2086
    _flat_freq_assoc_segments 1 ${mid_segs} || rc=1
    # shellcheck disable=SC2086
    _flat_freq_assoc_segments 0 ${fast_segs} || rc=1

    echo "== verifying =="
    local a tf bad=0 counts
    for cpu in "${FLAT_FREQ_ANCHORS[@]}"; do
        tf=$(_flat_freq_tf_state "${cpu}")
        [[ "${tf}" == "enabled" ]] || { echo "   [bad] turbo-freq on anchor ${cpu}: ${tf} (want enabled)"; bad=1; }
    done
    out=$(_flat_freq_isst --cpu 0 core-power get-config --clos 1) || true
    [[ "${out}" == *"clos-max:3900"* ]] || { echo "   [bad] clos1 max not 3900"; bad=1; }
    counts=$(_flat_freq_assoc_counts)
    [[ "${counts}" == "clos0=${nfast} clos1=${nmid} clos3=$((FLAT_FREQ_NCPU - nfast - nmid))" ]] \
        || { echo "   [bad] assoc counts: ${counts} (want clos0=${nfast} clos1=${nmid} clos3=$((FLAT_FREQ_NCPU - nfast - nmid)))"; bad=1; }
    a=$(_flat_freq_get_assoc "$(head -1 <<< "${fast_cpus}")")
    [[ "${a}" == "0" ]] || { echo "   [bad] first fast cpu assoc: clos ${a} (want 0)"; bad=1; }
    a=$(_flat_freq_get_assoc "$(head -1 <<< "${mid_cpus}")")
    [[ "${a}" == "1" ]] || { echo "   [bad] first mid cpu assoc: clos ${a} (want 1)"; bad=1; }

    if [[ ${bad} -eq 0 && ${rc} -eq 0 ]]; then
        echo "   turbo-freq enabled; 3 CLOS configs pinned; assoc: ${counts}"
        echo "3-TIER FREQUENCY APPLIED."
        echo "Expect fast ~4100 MHz under load (measured TF grant; no 4200 rung,"
        echo "4400 only if ALL other cores <=2700), mid <=3900, low <=2700."
        echo "Whole-machine loads are package-power-bound (~3.2-3.6 GHz)."
        echo "NOTE: state does not survive a reboot."
    else
        echo "[FAIL] 3-tier NOT cleanly applied — inspect flat_freq_status,"
        echo "       or run flat_freq_revert / reboot to return to a known state."
        rc=1
    fi
    return ${rc}
}
