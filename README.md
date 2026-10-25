# arch-lean-kernel-builder
An opinionated script to build a lean Linux kernel for Arch/CachyOS Linux

# Steps

1. Adjust the included and excluded features in `configure_kernel.py`
2. Run `build_kernel.py`
3. `paru -U /path/to/resulting/kernel.tar.zstd`
