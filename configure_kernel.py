#!/usr/bin/env python3

"""Generate the kernel .config inside the extracted tree.

Runs from PKGBUILD prepare(): starts from the running kernel's config, keeps only
modules listed in modprobed-db, then turns off debug, tracing and logging options.
"""

import gzip
import shutil
import subprocess
import sys
from pathlib import Path
import os
import re
import multiprocessing

PROC_CONFIG: Path = Path("/proc/config.gz")
MODPROBED_DB: Path = Path.home() / ".local/share/modprobed-db/modprobed.db"
LOCALVERSION: str = "-cachyos-local"

DISABLE: tuple[str, ...] = (
    "CC_OPTIMIZE_FOR_PERFORMANCE",
    "BLK_DEBUG_FS",
    "DEBUG_FS",
    "DEBUG_FS_ALLOW_ALL",
    "MODULE_DEBUGFS",
    "CFG80211_DEBUGFS",
    "MAC80211_DEBUGFS",
    "PCIE_DW_DEBUGFS",
    "RTW88_DEBUGFS",
    "DEBUG_INFO",  # also drops BTF; large, only needed by debuggers
    "DEBUG_KERNEL",  # gates lockdep, spinlock/mutex/VM debugging and most DEBUG_*
    "BPF",
    "HAVE_EBPF_JIT",
    "ARCH_WANT_DEFAULT_BPF_JIT",
    "IO_URING_BPF",
    "BPF_SYSCALL",
    "BPF_JIT",
    "BSD_PROCESS_ACCT",
    "CGROUP_FAVOR_DYNMODS",
    "CGROUP_RDMA",
    "CGROUP_DMEM",
    "CGROUP_HUGETLB",
    "CPUSETS",
    "CGROUP_CPUACCT",
    "CGROUP_PERF",
    "CGROUP_MISC",
    "CGROUP_DEBUG",
    "IO_URING",
    "AIO",
    "BLK_DEV_THROTTLING",
    "SHUFFLE_PAGE_ALLOCATOR",
    "KSM",
    "TRANSPARENT_HUGEPAGE",
    "IP_MROUTE",
    "SYN_COOKIES",
    "TCP_CONG_ADVANCED",
    "TCP_AO",
    "TCP_MD5SIG",
    "IPV6_ROUTER_PREF",
    "IPV6_OPTIMISTIC_DAD",
    "IPV6_MROUTE",
    "IPV6_SUBTREES",
    "IPV6_SEG6_LWTUNNEL",
    "IPV6_MULTIPLE_TABLES",
    "IPV6_SEG6_HMAC",
    "IPV6_RPL_LWTUNNEL",
    "IPV6_IOAM6_LWTUNNEL",
    "MPTCP",
    "NETWORK_SECMARK",
    "NETWORK_PHY_TIMESTAMPING",
    "NETFILTER",
    "NET_SCHED",
    "DCB",
    "MPLS",
    "NET_SWITCHDEV",
    "NET_L3_MASTER_DEV",
    "NET_NCSI",
    "PCPU_DEV_REFCNT",
    "RPS",
    "CGROUP_NET_PRIO",
    "CGROUP_NET_CLASSID",
    "BQL",
    "LWTUNNEL",
    "ANDROID_BINDER_IPC",
    "XFS_QUOTA",
    "XFS_POSIX_ACL",
    "XFS_RT",
    "XFS_SUPPORT_V4",
    "XFS_SUPPORT_ASCII_CI",
    "EXT4_FS_POSIX_ACL",
    "EXT4_FS_SECURITY",
    "F2FS_FAULT_INJECTION",
    "F2FS_FS_POSIX_ACL",
    "F2FS_FS_SECURITY",
    "FS_ENCRYPTION",
    "F2FS_FS_XATTR",
    "FS_VERITY",
    "KASAN",
    "KCSAN",
    "UBSAN",
    "KFENCE",
    "KMEMLEAK",
    "KGDB",
    "SLUB_DEBUG",
    "KCOV",
    "GCOV_KERNEL",
    "FTRACE",  # takes function and event tracers with it
    "PROFILING",
    "DYNAMIC_DEBUG",
    "ACPI_DEBUG",
    "PM_DEBUG",
    "KALLSYMS_ALL",
    "SECURITY_SELINUX",
    "SECURITY_SMACK",
    "SECURITY_TOMOYO",
    "LOCALVERSION_AUTO",
    "PREEMPT",
    "PSI",
    "TASKSTATS",
    "PROCESS_ACCT",
    "PRINTK_INDEX",
    "UCLAMP_TASK",
    "NUMA_BALANCING",
    "NUMA_BALANCING_DEFAULT_ENABLED",
    "CHECKPOINT_RESTORE",
    "BUG",
    "ELF_CORE",
    "PCSPKR_PLATFORM",
    "KEXEC",
    "KEXEC_CORE",
    "KEXEC_HANDOVER",
    "KEXEC_FILE",
    "AMD_SECURE_AVIC",
    "X86_CPU_RESCTRL",
    "KVM_INTEL",
    "VIRTUALIZATION",
    "KVM",
    "X86_FRED",
    "IA32_FEAT_CTL",
    "X86_AMD_PLATFORM_DEVICE",
    "IOSF_MBI",
    "HYPERVISOR_GUEST",
    "PROCESSOR_SELECT",
    "X86_MCE_AMD",
    "AMD_MEM_ENCRYPT",
    "X86_CPA_STATISTICS",
    "NUMA",
    "X86_SGX",
    "X86_USER_SHADOW_STACK",
    "INTEL_TDX_HOST",
    "RANDOMIZE_BASE",
    "MODIFY_LDT_SYSCALL",
    "CPU_MITIGATIONS",
    "SUSPEND",
    "HIBERNATION",
    "VIRTUALIZATION",
    "KPROBES",
    "STACKPROTECTOR",
    "VMAP_STACK",
    "RANDOMIZE_KSTACK_OFFSET",
    "LOCK_EVENT_COUNTS",
    "COREDUMP",
    "MEMORY_HOTREMOVE",
    "MEMORY_HOTPLUG",
    "PAGE_REPORTING",
    "MEMORY_FAILURE",
    "CMA",
    "MEM_SOFT_DIRTY",
    "IDLE_PAGE_TRACKING",
    "DAMON",
    "MCTP",
    "PAGE_POOL_STATS",
    "VIRTIO_BLK",
    "PVPANIC",
    "MD",
    "FUSION",
    "MACINTOSH_DRIVERS",
    "SPI",
    "MEDIA_SUPPORT",
    "VGA_SWITCHEROO",
    "DRM_I915_CAPTURE_ERROR",
    "DRM_XE",
    "TRACE_GPU_MEM",
    "DRM_ACCEL",
    "SND_USB",
    "USB_XHCI_DBGCAP",
    "USB_XHCI_SIDEBAND",
    "ACCESSIBILITY",
    "EDAC",
    "VIRT_DRIVERS",
    "VIRTIO_MENU",
    "VHOST_MENU",
    "STAGING",
    "CHROME_PLATFORMS",
    "MELLANOX_PLATFORM",
    "SURFACE_PLATFORMS",
    "SOUNDWIRE",
    "INTERCONNECT",
    "HTE",
    "BTRFS_FS",
    "SECURITY_APPARMOR",
    "SECURITY_YAMA",
    "SECURITY_LOCKDOWN_LSM",
    "IPE",
    "INTEGRITY",
    "FORTIFY_SOURCE",
    "HARDENED_USERCOPY",
    "DYNAMIC_DEBUG_CORE",
    "SYMBOLIC_ERRNAME",
    "DEBUG_KERNEL",
    "DEBUG_MISC",
    "MAGIC_SYSRQ",
    "UCLAMP_TASK",
    "AUDIT",
    "SLUB_DEBUG",
    "PAGE_POISONING",
    "DEBUG_RODATA_TEST",
    "SHRINKER_DEBUG",
    "DEBUG_MEMORY_INIT",
    "SCHEDSTATS",
    "STACKTRACE",
    "RCU_TRACE",
    "EARLY_PRINTK",
    "X86_DEBUG_FPU",
    "RUNTIME_TESTING_MENU",
    "MEMTEST",
    "CACHESTAT_SYSCALL",
    "KALLSYMS",
    "X86_POSTED_MSI",
    "X86_MPPARSE",
    "X86_INTEL_LPSS",
    "IOSF_MBI",
    "X86_KERNEL_IBT",
    "X86_INTEL_MEMORY_PROTECTION_KEYS",
    "CHED_CLUSTER",
    "SECURITY_SAFESETID",
    "SECURITYFS",
    "ATA_SFF",
    "HOTPLUG_PCI_PCIE",
    "PCIEAER",
    "PCIE_PTM",
    "PCI_STUB",
    "PCI_DOE",
    "PCI_IOV",
    "HOTPLUG_PCI",
    "VGA_ARB",
    "ZRAM_BACKEND_DEFLATE",
    "ZRAM_BACKEND_842",
    "ZRAM_BACKEND_LZ4",
    "ZRAM_BACKEND_LZ4HC",
    "ZRAM_BACKEND_LZO",
    "NVME_MULTIPATH",
    "MEGARAID_NEWGEN",
    "SCSI_LOWLEVEL",
    "IP_ADVANCED_ROUTER",
    "IP_MULTICAST",
    "INET_PSP",
    "SCSI_DH",
    "SCSI_CONSTANTS",
    "NET_FC",
    "NET_VENDOR_3COM",
    "NET_VENDOR_ADAPTEC",
    "NET_VENDOR_AGERE",
    "NET_VENDOR_ALACRITECH",
    "NET_VENDOR_ALIBABA",
    "NET_VENDOR_AMAZON",
    "NET_VENDOR_AMD",
    "NET_VENDOR_AQUANTIA",
    "NET_VENDOR_ARC",
    "NET_VENDOR_ASIX",
    "NET_VENDOR_ATHEROS",
    "NET_VENDOR_BROADCOM",
    "NET_VENDOR_CADENCE",
    "NET_VENDOR_CAVIUM",
    "NET_VENDOR_CHELSIO",
    "NET_VENDOR_CISCO",
    "NET_VENDOR_CORTINA",
    "NET_VENDOR_DAVICOM",
    "NET_VENDOR_DEC",
    "NET_VENDOR_DLINK",
    "NET_VENDOR_EMULEX",
    "NET_VENDOR_ENGLEDER",
    "NET_VENDOR_EZCHIP",
    "NET_VENDOR_FUNGIBLE",
    "NET_VENDOR_GOOGLE",
    "NET_VENDOR_HISILICON",
    "NET_VENDOR_HUAWEI",
    "NET_VENDOR_I825XX",
    "NET_VENDOR_INTEL",
    "NET_VENDOR_LITEX",
    "NET_VENDOR_MARVELL",
    "NET_VENDOR_MELLANOX",
    "NET_VENDOR_META",
    "NET_VENDOR_MICREL",
    "NET_VENDOR_MICROCHIP",
    "NET_VENDOR_MICROSEMI",
    "NET_VENDOR_MICROSOFT",
    "NET_VENDOR_MUCSE",
    "NET_VENDOR_MYRI",
    "NET_VENDOR_NI",
    "NET_VENDOR_NATSEMI",
    "NET_VENDOR_NETRONOME",
    "NET_VENDOR_8390",
    "NET_VENDOR_NVIDIA",
    "NET_VENDOR_OKI",
    "NET_VENDOR_PENSANDO",
    "NET_VENDOR_QLOGIC",
    "NET_VENDOR_BROCADE",
    "NET_VENDOR_QUALCOMM",
    "NET_VENDOR_RDC",
    "NET_VENDOR_RENESAS",
    "NET_VENDOR_ROCKER",
    "NET_VENDOR_SAMSUNG",
    "NET_VENDOR_SEEQ",
    "NET_VENDOR_SILAN",
    "NET_VENDOR_SIS",
    "NET_VENDOR_SOLARFLARE",
    "NET_VENDOR_SMSC",
    "NET_VENDOR_SOCIONEXT",
    "NET_VENDOR_STMICRO",
    "NET_VENDOR_SUN",
    "NET_VENDOR_SYNOPSYS",
    "NET_VENDOR_TEHUTI",
    "NET_VENDOR_TI",
    "NET_VENDOR_VERTEXCOM",
    "NET_VENDOR_VIA",
    "NET_VENDOR_WANGXUN",
    "NET_VENDOR_WIZNET",
    "NET_VENDOR_XILINX",
    "PSE_CONTROLLER",
    "USB_USBNET",
    "WLAN_VENDOR_ADMTEK",
    "WLAN_VENDOR_ATH",
    "WLAN_VENDOR_ATMEL",
    "WLAN_VENDOR_BROADCOM",
    "WLAN_VENDOR_INTEL",
    "WLAN_VENDOR_INTERSIL",
    "WLAN_VENDOR_MARVELL",
    "WLAN_VENDOR_MEDIATEK",
    "WLAN_VENDOR_MICROCHIP",
    "WLAN_VENDOR_PURELIFI",
    "WLAN_VENDOR_RALINK",
    "WLAN_VENDOR_RSI",
    "WLAN_VENDOR_SILABS",
    "WLAN_VENDOR_ST",
    "WLAN_VENDOR_TI",
    "WLAN_VENDOR_ZYDAS",
    "WLAN_VENDOR_QUANTENNA",
    "PINCTRL",
    "GPIOLIB",
    "WATCHDOG",
    "REGULATOR",
    "RC_CORE",
    "SND_OSSEMUL",
    "SND_PROC_FS",
    "SND_DEBUG",
    "SND_CTL_INPUT_VALIDATION",
    "SND_UTIMER",
    "SND_DRIVERS",
    "SND_PCI",
    "SND_HDA_INPUT_BEEP",
    "SND_HDA_INTEL_HDMI_SILENT_STREAM",
    "SND_SOC",
    "SND_X86",
    "PM_DEVFREQ",
    "MEMORY",
    "PWM",
    "RAS",
    "DAX",
    "DEBUG_KERNEL",
    "CFI",
    "KSTACK_ERASE",
    "WARN_CONTEXT_ANALYSIS",
    "PAGE_POISONING",
    "LTO_NONE",
)
ENABLE: tuple[str, ...] = (
    "DEBUG_FS_ALLOW_NONE",
    "RANDSTRUCT_NONE",
    "CC_OPTIMIZE_FOR_SIZE",
    "LTO",
    "LTO_CLANG",
    "HAS_LTO_CLANG",
    "LTO_CLANG_FULL",
    "AUTOFDO_CLANG",
    "PROPELLER_CLANG",
    "LOCALVERSION_AUTO",
    "PREEMPT_LAZY",
    "SCHED_CORE",
    "SCHED_CACHE",
    "INIT_STACK_NONE",
    "EXPERT",
    "UNWINDER_GUESS",
    "MFD_INTEL_LPSS_PCI",
    "PINCTRL_INTEL",
    "X86_NATIVE_CPU",
    "USB_RTL8152",
    "USB_NET_DRIVERS",
    "PCIEASPM_POWER_SUPERSAVE",
    "ZRAM_BACKEND_ZSTD",
    "SND_HDA_INTEL",
    "SND_HDA_CODEC_HDMI_INTEL",
    "SND_HDA_CODEC_REALTEK",
    "SND_HDA_CODEC_ALC269",
    "SECURITY",
    "SECURITY_PATH",
    "SECURITY_NETWORK",
    "SECURITY_LANDLOCK",
)  # local-only package, optimize for this CPU


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def check_modprobed_db(db: Path) -> None:
    if not db.is_file() or db.stat().st_size == 0:
        raise RuntimeError(f"modprobed-db database missing or empty: {db}")


def write_base_config(dest: Path) -> None:
    if not PROC_CONFIG.is_file():
        raise RuntimeError(
            "/proc/config.gz missing: the running kernel needs CONFIG_IKCONFIG_PROC"
        )
    with gzip.open(PROC_CONFIG, "rb") as src, dest.open("wb") as out:
        shutil.copyfileobj(src, out)


def scripts_config_args(config: Path) -> list[str]:
    args = ["--file", str(config)]
    for symbol in DISABLE:
        args += ["--disable", symbol]
    for symbol in ENABLE:
        args += ["--enable", symbol]
    args += ["--set-str", "LOCALVERSION", LOCALVERSION]
    args += ["--set-str", "SYSTEM_TRUSTED_KEYS", ""]
    args += ["--set-str", "SYSTEM_REVOCATION_KEYS", ""]
    return args


def tune_kernel_config(config_path=".config"):
    """
    Inspect host hardware and tune Linux kernel config settings in-place.
    Uses aggressive, lean fanout values for minimal latency.

    Args:
        config_path: Path to the .config file (default: ".config" in current directory)

    Returns:
        dict: The configuration values that were set
    """

    # Get system specs
    num_cpus = multiprocessing.cpu_count()

    # Get memory in MB from /proc/meminfo
    memory_mb = 0
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    memory_mb = int(line.split()[1]) // 1024
                    break
    except Exception as e:
        print(f"Warning: Could not read /proc/meminfo: {e}")

    # Aggressive lean tuning: minimize fanout for lower latency

    # RCU_FANOUT: very aggressive scaling
    if num_cpus <= 8:
        rcu_fanout = 16
    elif num_cpus <= 32:
        rcu_fanout = 32
    elif num_cpus <= 128:
        rcu_fanout = 48
    else:
        rcu_fanout = 64

    # RCU_FANOUT_LEAF: very lean, prioritize responsiveness
    rcu_fanout_leaf = max(4, num_cpus // 16)
    rcu_fanout_leaf = min(rcu_fanout_leaf, 8)  # Cap at 8

    # PGTABLE_LEVELS
    pgtable_levels = 5 if (memory_mb > 32768 or num_cpus > 64) else 4

    # NR_CPUS: round up to next power of 2
    nr_cpus = num_cpus
    if num_cpus & (num_cpus - 1) != 0:
        nr_cpus = 1 << num_cpus.bit_length()
    nr_cpus = min(nr_cpus, 512)

    config_values = {
        "CONFIG_RCU_FANOUT": rcu_fanout,
        "CONFIG_RCU_FANOUT_LEAF": rcu_fanout_leaf,
        "CONFIG_PGTABLE_LEVELS": pgtable_levels,
        "CONFIG_NR_CPUS_RANGE_BEGIN": 1,
        "CONFIG_NR_CPUS_RANGE_END": nr_cpus,
        "CONFIG_NR_CPUS_DEFAULT": nr_cpus,
        "CONFIG_NR_CPUS": nr_cpus,
    }

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        content = f.read()

    for key, value in config_values.items():
        pattern = rf"^(?:#\s*)?{re.escape(key)}(?:=.*)?$"
        replacement = f"{key}={value}"

        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content += f"\n{key}={value}"

    with open(config_path, "w") as f:
        f.write(content)

    print(f"Kernel config tuned for {num_cpus} CPUs and {memory_mb} MB RAM")
    print("\nConfiguration values set:")
    for key, value in sorted(config_values.items()):
        print(f"  {key}={value}")

    return config_values


def configure(tree: Path, db: Path) -> None:
    check_modprobed_db(db)
    config = tree / ".config"
    write_base_config(config)
    run(["sed", "-i", "s/select DEBUG_KERNEL//g", tree / "init/Kconfig"])
    run(
        ["make", "CC=clang", "LLVM=1", "-C", str(tree), f"LSMOD={db}", "localmodconfig"]
    )
    run([str(tree / "scripts/config"), *scripts_config_args(config)])
    tune_kernel_config(config)
    run(["make", "CC=clang", "LLVM=1", "-C", str(tree), "olddefconfig"])


if __name__ == "__main__":
    configure(Path(sys.argv[1]).resolve(), MODPROBED_DB)
