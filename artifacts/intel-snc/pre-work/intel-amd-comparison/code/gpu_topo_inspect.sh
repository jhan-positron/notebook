#!/usr/bin/env bash
# gpu_topo_inspect.sh -- GPU + PCIe + NUMA topology for inference-TPS work
# Read-only. Safe on CI/CD. Run as:
#   bash gpu_topo_inspect.sh 2>&1 | tee gpu_topo_$(hostname)_$(date +%Y%m%d).log
# sudo gets a bit more (NIC firmware, full lspci), but not required.

set +e
hr() { printf '\n========== %s ==========\n' "$1"; }

hr "META"
date; hostname; uname -r
[ -r /etc/os-release ] && grep PRETTY_NAME /etc/os-release

# ---------- NVIDIA ----------
hr "NVIDIA driver + GPUs (nvidia-smi)"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi
  echo "--- query specific fields ---"
  nvidia-smi --query-gpu=index,name,pci.bus_id,pci.domain,driver_version,memory.total,compute_cap,power.limit \
    --format=csv
  echo "--- nvidia-smi topo -m (GPU-GPU + GPU-NIC + NUMA affinity) ---"
  nvidia-smi topo -m
  echo "--- nvidia-smi topo -mp (per-PCIe-path) ---"
  nvidia-smi topo -mp 2>/dev/null
else
  echo "nvidia-smi not present"
fi

# ---------- AMD GPU ----------
hr "AMD GPU (rocm-smi) -- if any"
if command -v rocm-smi >/dev/null; then
  rocm-smi --showtopo
  rocm-smi --showhw
  rocm-smi --showproductname
else
  echo "rocm-smi not present"
fi

# ---------- Intel / Habana / other accelerators ----------
hr "Other accelerators (Intel GPU / Gaudi / etc.)"
command -v intel_gpu_top >/dev/null && echo "intel_gpu_top present"
command -v xpu-smi      >/dev/null && xpu-smi discovery 2>/dev/null | head -50
command -v hl-smi       >/dev/null && hl-smi
ls /dev/dri/ 2>/dev/null
ls /dev/accel* 2>/dev/null
ls /dev/habanalabs* 2>/dev/null

# ---------- PCIe topology, all accelerators + NICs ----------
hr "lspci -tv (PCIe tree)"
lspci -tv 2>/dev/null

hr "lspci accelerators + NICs + storage (verbose, key fields)"
# 3D/VGA, processing accel, NICs, NVMe, storage
lspci -nn 2>/dev/null | grep -iE '3d|vga|display|processing|ethernet|infiniband|nvme|raid|sas|sata'

hr "PCIe link state per GPU/accel (need to enumerate)"
# For each GPU-like device, dump speed + width
if command -v lspci >/dev/null; then
  for bdf in $(lspci -nn | grep -iE '3d|vga|display|processing' | awk '{print $1}'); do
    echo "--- $bdf ---"
    lspci -s "$bdf" -nn | head -1
    sudo -n lspci -s "$bdf" -vv 2>/dev/null | grep -E 'LnkCap:|LnkSta:|NUMA node' | head -6 || \
      lspci -s "$bdf" -vv 2>/dev/null | grep -E 'LnkCap:|LnkSta:|NUMA node' | head -6
  done
fi

hr "NIC link state (matters if inference does RDMA)"
for bdf in $(lspci -nn | grep -iE 'ethernet|infiniband' | awk '{print $1}'); do
  echo "--- $bdf ---"
  lspci -s "$bdf" -nn | head -1
  sudo -n lspci -s "$bdf" -vv 2>/dev/null | grep -E 'LnkCap:|LnkSta:|NUMA node' | head -3 || \
    lspci -s "$bdf" -vv 2>/dev/null | grep -E 'LnkCap:|LnkSta:|NUMA node' | head -3
done

# ---------- NUMA affinity of accelerators ----------
hr "NUMA node per accelerator/NIC (from sysfs)"
for d in /sys/bus/pci/devices/*; do
  cls=$(cat "$d/class" 2>/dev/null)
  # match Display (0x03xxxx), Processing accel (0x12xxxx), Network (0x02xxxx)
  case "$cls" in
    0x030000|0x030200|0x038000|0x120000|0x020000)
      bdf=$(basename "$d")
      numa=$(cat "$d/numa_node" 2>/dev/null)
      local_cpus=$(cat "$d/local_cpulist" 2>/dev/null)
      vendor=$(cat "$d/vendor" 2>/dev/null)
      device=$(cat "$d/device" 2>/dev/null)
      printf 'bdf=%s class=%s vendor=%s device=%s numa_node=%s local_cpus=%s\n' \
        "$bdf" "$cls" "$vendor" "$device" "$numa" "$local_cpus"
      ;;
  esac
done

# ---------- IOMMU / VFIO ----------
hr "IOMMU + VFIO"
grep -E 'iommu|amd_iommu' /proc/cmdline
ls /sys/class/iommu/ 2>/dev/null
dmesg 2>/dev/null | grep -iE 'iommu|vfio' | head -15

# ---------- IRQ affinity for the GPUs + NICs ----------
hr "IRQ affinity for accelerator/NIC interrupts"
if [ -r /proc/interrupts ]; then
  # show header + lines that mention nvidia/amdgpu/mlx/ice/ena/i40e
  awk 'NR==1 || /nvidia|amdgpu|mlx|ice|ena|i40e|hpa|hpasm|gaudi|habanalabs|xpu/' /proc/interrupts | head -30
fi
# Show smp_affinity_list for first matching IRQ
for irq_dir in /proc/irq/*/; do
  name=$(ls "$irq_dir" 2>/dev/null | head -1)
  af=$(cat "$irq_dir/smp_affinity_list" 2>/dev/null)
  # only print irqs whose folder contains 'nvidia' or 'mlx' etc
  for sub in "$irq_dir"*; do
    [ -d "$sub" ] || continue
    base=$(basename "$sub")
    case "$base" in
      *nvidia*|*amdgpu*|*mlx*|*ice*|*ena*|*habanalabs*|*gaudi*)
        printf 'irq=%s subname=%s smp_affinity_list=%s\n' "$(basename "$irq_dir")" "$base" "$af"
        ;;
    esac
  done
done | head -40

# ---------- Inference framework hints ----------
hr "Inference framework / Python env hints"
command -v python3 >/dev/null && python3 --version
command -v pip     >/dev/null && pip list 2>/dev/null | grep -iE \
  'vllm|tgi|sglang|triton|torch|transformers|accelerate|deepspeed|tensorrt|llama|exllama|optimum|onnx|cuda|rocm|hip|intel-extension|oneapi' \
  | head -30
# what's currently running (without invading anything)
ps -eo pid,ppid,user,etime,cmd --sort=-pcpu 2>/dev/null | head -25 | grep -iE \
  'vllm|tgi|sglang|triton|llama|python|infer|serve|tensorrt|trtllm|ray' | head -10

# ---------- CUDA / driver versions visible to system ----------
hr "Library versions (read-only)"
ls /usr/local/cuda* 2>/dev/null | head -5
[ -r /usr/local/cuda/version.json ] && cat /usr/local/cuda/version.json
ldconfig -p 2>/dev/null | grep -iE 'libcuda|libcudart|libnccl|librccl|libze_loader|libhsa' | head -10

# ---------- DONE ----------
hr "DONE"
date
