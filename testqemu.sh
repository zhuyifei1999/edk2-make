#! /bin/bash
set -e

DIR="$PWD"
WORK_DIR="$( mktemp -d )"

cd "$WORK_DIR"

function cleanup_tmp {
  cd "$DIR"
  rm -rf "$WORK_DIR"
}

trap cleanup_tmp EXIT

mkdir -p rootfs/EFI/Boot/
cp $1 rootfs/EFI/Boot/bootx64.efi

qemu-system-x86_64 --enable-kvm \
  -bios /usr/share/edk2-ovmf/OVMF_CODE.fd \
  -m 256M \
  -drive format=raw,file=fat:rw:rootfs \
  -net none
