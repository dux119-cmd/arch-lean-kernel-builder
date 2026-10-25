#!/usr/bin/env python3

"""Render the PKGBUILD and the pacman install script for the kernel package."""

import hashlib
from pathlib import Path

from fetch import KernelRelease

PKGBASE: str = "linux-cachyos-local"

PKGBUILD_TEMPLATE: str = """\
pkgbase={pkgbase}
pkgname={pkgbase}
pkgver={version}
pkgrel=1
pkgdesc="Linux {version} with modprobed-db modules and trimmed debug options"
arch=(x86_64)
url="https://www.kernel.org"
license=(GPL-2.0-only)
makedepends=(bc cpio gettext libelf pahole perl python tar xz clang llvm lld)
options=(!debug !strip)
install={pkgbase}.install
source=("linux-$pkgver.tar.xz::{tarball_url}"
        configure_kernel.py)
sha256sums=({sums})

prepare() {{
  cd "linux-$pkgver"
  python3 "$srcdir/configure_kernel.py" "$PWD"
}}

build() {{
  cd "linux-$pkgver"
  make CC=clang LLVM=1 -j"$(nproc)" bzImage modules
}}

package() {{
  cd "linux-$pkgver"
  local kver moddir
  kver="$(make -s kernelrelease)"
  moddir="$pkgdir/usr/lib/modules/$kver"

  make INSTALL_MOD_PATH="$pkgdir/usr" INSTALL_MOD_STRIP=1 modules_install
  rm -f "$moddir/build" "$moddir/source"
  install -Dm644 "$(make -s image_name)" "$moddir/vmlinuz"
  printf '%s\\n' "$pkgbase" > "$moddir/pkgbase"

  install -d "$pkgdir/etc/mkinitcpio.d"
  cat > "$pkgdir/etc/mkinitcpio.d/$pkgbase.preset" <<EOF
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-$pkgbase"
PRESETS=('default' 'fallback')
default_image="/boot/initramfs-$pkgbase.img"
fallback_image="/boot/initramfs-$pkgbase-fallback.img"
fallback_options="-S autodetect"
EOF
}}
"""

INSTALL_SCRIPT: str = """\
KBASE=linux-cachyos-local
LIMINE_CONF=/boot/limine.conf

add_limine_entry() {
  local version="$1" cmdline
  if [[ ! -f $LIMINE_CONF ]]; then
    echo "==> $LIMINE_CONF not found, add a boot entry for $KBASE manually" >&2
    return 0
  fi
  pacman -Qq limine-mkinitcpio-hook &>/dev/null && return 0
  pacman -Qq limine-entry-tool &>/dev/null && return 0
  grep -qF "vmlinuz-$KBASE" "$LIMINE_CONF" && return 0
  cmdline="$(sed 's/BOOT_IMAGE=[^ ]* *//' /proc/cmdline)"
  cat >> "$LIMINE_CONF" <<EOF

/Local kernel $version
    protocol: linux
    path: boot():/vmlinuz-$KBASE
    module_path: boot():/initramfs-$KBASE.img
    cmdline: $cmdline
EOF
}

post_install() {
  add_limine_entry "$1"
}

post_upgrade() {
  add_limine_entry "$1"
}
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_pkgbuild(release: KernelRelease, configure_script: Path) -> str:
    """The kernel tarball is fetched by makepkg and marked SKIP; the local script is hashed."""
    sums = f"'SKIP' '{_sha256(configure_script)}'"
    return PKGBUILD_TEMPLATE.format(
        pkgbase=PKGBASE,
        version=release.version,
        tarball_url=release.url,
        sums=sums,
    )
