# Android VM Workstation Pro

The app is for linux only still
A QEMU/KVM and Android SDK frontend for Linux with a VirtualBox-style interface. Built to create, customize, and run Android-x86 virtual machines without typing long QEMU or ADB commands manually.

## Features
- **VirtualBox-style Manager UI:** Menu bar, icon toolbar (`New`, `Settings`, `Discard`, `Start`, `Stop`, `APK`, `About`), OS version tags, tabbed settings dialog, and hardware summary with a live screen preview.
- **VM & Virtual Disk Wizard:** Two-step setup that auto-detects Android-x86 base ISOs (`2.2` to `6.0`) and creates `QCOW2`, `VDI`, or `VMDK` virtual disks.
- **Custom Android-x86 ISO Builder (`make-phone-iso.sh`):** Patches donor `build.prop` device info, boot animations, audio, and compatible APKs into bootable Android-x86 ISOs.
- **Boot Animation Creator:** Generates uncompressed `bootanimation.zip` files with custom text, colors, resolution, and a live preview frame.
- **ADB Quick Tools:** Screen rotation toggle, PNG screenshots saved to `~/Pictures`, live `build.prop` & DPI editor, filtered `logcat` crash viewer, APK installer, and root ADB shell.
- **8 UI Themes:** `VirtualBox Classic`, `VMware Dark`, `macOS Aqua`, `Windows XP Luna`, `Ubuntu Ambiance`, `Cyberpunk Neon`, `Dracula Pro`, and `Nord Frost`.

## Installation (Ubuntu / Debian)
Grab `android-vm-workstation-pro_2.2.0_all.deb` from the **Releases** tab and install it:

```bash
sudo apt install ./android-vm-workstation-pro_2.2.0_all.deb
```

Launch it from your app menu or run:
```bash
android-vm-workstation
```

---
Made by Adrian (built with help from Gemini AI)
