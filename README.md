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
## Tested Devices & Compatibility Notes

| Device Profile | Base ISO | Settings Used | What Happened / Test Notes |
| :--- | :--- | :--- | :--- |
| **Sony Xperia Z3 (`D6603`)** | `android-x86-6.0-r3.iso` | `2048–3072 MB` • `720x1280` • `VMware SVGA (2D)` | Booted cleanly with custom Xperia boot animation, Sony audio, and `build.prop` identity. ARM-only Sony system APKs must be stripped or they crash on x86. |
| **Acer Iconia Tab A500** | `android-x86-4.4-r5.iso` | `2048 MB` • `1280x800` • `VMware SVGA (2D)` | Widescreen tablet layout booted smoothly with original Acer ringtones/wallpaper and a generated white `acer` draw-in `bootanimation.zip`. Tegra 2 ARM APKs excluded to prevent force-closes. |
| **Samsung Galaxy S5 Active** | `android-x86-4.4-r5.iso` | `2048 MB` • `720x1280` • `VMware SVGA (2D)` | Stable desktop and app drawer when paired with `VMware SVGA (2D)` (`VirGL` caused black screens on older KitKat builds). |
| **Huawei IDEOS S7 Slim** | `android-x86-2.2-r2` / `4.4-r5` | `1024–2048 MB` • `800x480` / `1024x768` | `2.2` and `2.3` base ISOs booted fast with `USB Mouse` pointer mode (`usb-tablet` caused cursor offset on Froyo/Gingerbread); `4.4-r5` ran modern APKs best. |
| **Asus ZenFone 5** | `android-x86-4.4-r5.iso` | `2048 MB` • `720x1280` • `VMware SVGA (2D)` | Best app compatibility out of the box because the donor firmware is native Intel x86, so ZenUI apps and native `.so` libraries ran without ARM translation crashes. |

---
Made by Adrian (built with help from Gemini AI)
