#!/usr/bin/env python3

"""Build linux-cachyos-local as a pacman package via makepkg."""

import os
import shutil
import subprocess
from pathlib import Path

from fetch import KernelRelease, latest_stable
from pkgbuild import INSTALL_SCRIPT, PKGBASE, render_pkgbuild

HERE: Path = Path(__file__).resolve().parent
BUILD_ROOT: Path = Path.home() / ".cache" / "kbuild"


def stage(src: Path, build_dir: Path) -> Path:
    dst = build_dir / src.name
    shutil.copy2(src, dst)
    return dst


def build_dir_for(release: KernelRelease) -> Path:
    path = BUILD_ROOT / release.version
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    if os.geteuid() == 0:
        raise SystemExit("run as your normal user: makepkg refuses root")

    release = latest_stable()
    print(f"kernel {release.version}")

    build_dir = build_dir_for(release)
    configure = stage(HERE / "configure_kernel.py", build_dir)

    (build_dir / "PKGBUILD").write_text(render_pkgbuild(release, configure))
    (build_dir / f"{PKGBASE}.install").write_text(INSTALL_SCRIPT)

    # -s installs makedepends (uses sudo), -f overwrites old output, -c cleans the work tree
    subprocess.run(["makepkg", "-sfc"], cwd=build_dir, check=True)
    for pkg in sorted(build_dir.glob("*.pkg.tar.*")):
        print(f"built: {pkg}")


if __name__ == "__main__":
    main()
