#!/bin/bash
set -e

if [ "$#" -lt 3 ]; then
    echo "Usage:   $0 <base-android-x86.iso> <donor-file.zip_or_img> <output.iso>"
    echo "Example: $0 android-x86-4.4-r5.iso motox_firmware.zip motox-x86-4.4.iso"
    exit 1
fi

BASE_ISO="$(realpath "$1")"
DONOR_INPUT="$(realpath "$2")"
OUT_ISO="$(realpath -m "$3")"
WORK_DIR="$HOME/Downloads/iso_builder_work"

echo "==> Checking required tools..."
for cmd in simg2img unsquashfs mksquashfs xorriso unzip zip; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Installing missing tools..."
        sudo apt update && sudo apt install -y squashfs-tools android-sdk-libsparse-utils xorriso isolinux unzip zip p7zip-full
        break
    fi
done

echo "==> Cleaning up old workspace..."
true 2>/dev/null || true
sudo umount "$WORK_DIR/x86_sys" 2>/dev/null || true
sudo umount "$WORK_DIR/donor_sys" 2>/dev/null || true
sudo rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"/{iso_mount,iso_work,x86_sys,donor_sys,donor_extract}

echo "==> Processing donor input: $(basename "$DONOR_INPUT")"
DONOR_IMG=""

if [[ "$DONOR_INPUT" == *.zip ]]; then
    echo "Extracting donor ZIP..."
    unzip -q "$DONOR_INPUT" -d "$WORK_DIR/donor_extract"
    
    # Check for nested image zip (like Google Nexus factory images)
    INNER_ZIP=$(find "$WORK_DIR/donor_extract" -name "image-*.zip" | head -n 1)
    if [ -n "$INNER_ZIP" ]; then
        unzip -q "$INNER_ZIP" -d "$WORK_DIR/donor_extract/inner"
    fi

    # Check for Samsung .tar or .tar.md5 inside the zip (prioritizing AP_ package)
    TAR_FILE=$(find "$WORK_DIR/donor_extract" -name "AP_*.tar*" -o -name "*.tar.md5" -o -name "*.tar" | head -n 1)
    if [ -n "$TAR_FILE" ]; then
        echo "Unpacking Samsung tar archive: $(basename "$TAR_FILE")..."
        tar -xf "$TAR_FILE" -C "$WORK_DIR/donor_extract" --wildcards "*system.img*" 2>/dev/null || tar -xf "$TAR_FILE" -C "$WORK_DIR/donor_extract"
    fi

    # Case A: Motorola split sparsechunks (system.img_sparsechunk.0, .1, etc.)
    SPARSE_CHUNKS=$(find "$WORK_DIR/donor_extract" -name "system.img_sparsechunk*" | sort -V)
    if [ -n "$SPARSE_CHUNKS" ]; then
        echo "Merging Motorola sparsechunk files..."
        simg2img $SPARSE_CHUNKS "$WORK_DIR/donor_raw.img"
        DONOR_IMG="$WORK_DIR/donor_raw.img"
    else
        # Case B: Single system.img inside the zip
        FOUND_IMG=$(find "$WORK_DIR/donor_extract" -name "system.img" -o -name "system.img.ext4" | head -n 1)
        if [ -n "$FOUND_IMG" ]; then
            DONOR_IMG="$FOUND_IMG"
        fi
    fi
elif [[ "$DONOR_INPUT" == *.tar* ]]; then
    echo "Extracting Samsung tar archive..."
    tar -xf "$DONOR_INPUT" -C "$WORK_DIR/donor_extract" --wildcards "*system.img*" 2>/dev/null || tar -xf "$DONOR_INPUT" -C "$WORK_DIR/donor_extract"
    DONOR_IMG=$(find "$WORK_DIR/donor_extract" -name "system.img" -o -name "system.img.ext4" | head -n 1)
else
    DONOR_IMG="$DONOR_INPUT"
fi

# Auto-detect and strip any vendor header before Android Sparse (3aff26ed) or Ext4 magic
if [ -n "$DONOR_IMG" ]; then
    OFFSET=$(python3 -c '
data = open("'"$DONOR_IMG"'", "rb").read(262144)
idx = data.find(b"\x3a\xff\x26\xed")
if idx != -1:
    print(idx)
else:
    idx2 = data.find(b"\x53\xef")
    print(idx2 - 1080 if idx2 >= 1080 else 0)
')
    if [ "$OFFSET" -gt 0 ]; then
        echo "Stripping $OFFSET-byte vendor header from $(basename "$DONOR_IMG")..."
        python3 -c '
with open("'"$DONOR_IMG"'", "rb") as src, open("'"$WORK_DIR"'/donor_stripped.img", "wb") as dst:
    src.seek('"$OFFSET"')
    while True:
        chunk = src.read(1048576)
        if not chunk: break
        dst.write(chunk)
'
        DONOR_IMG="$WORK_DIR/donor_stripped.img"
    fi
fi

# Mount donor system partition (or use extracted /system folder if it's a flashable ROM zip)
if [ -n "$DONOR_IMG" ]; then
    if simg2img "$DONOR_IMG" "$WORK_DIR/donor_raw.img" 2>/dev/null; then
        echo "Converting sparse system.img to raw ext4..."
        simg2img "$DONOR_IMG" "$WORK_DIR/donor_raw.img"
        sudo mount -o loop,ro,noload "$WORK_DIR/donor_raw.img" "$WORK_DIR/donor_sys"
    else
        sudo mount -o loop,ro,noload "$DONOR_IMG" "$WORK_DIR/donor_sys"
    fi
elif [ -d "$WORK_DIR/donor_extract/system" ]; then
    echo "Using extracted /system folder from flashable ROM zip..."
    sudo mount --bind "$WORK_DIR/donor_extract/system" "$WORK_DIR/donor_sys"
else
    echo "ERROR: Could not find system.img, sparsechunks, or /system folder in $DONOR_INPUT"
    exit 1
fi

echo "==> Unpacking base Android-x86 ISO..."
7z x -y "$BASE_ISO" -o"$WORK_DIR/iso_work" >/dev/null
cp -a "$WORK_DIR/iso_mount/." "$WORK_DIR/iso_work/"
true

echo "==> Unpacking and expanding x86 system.img (+1800MB)..."
sudo unsquashfs -d "$WORK_DIR/x86_sfs" "$WORK_DIR/iso_work/system.sfs"
sudo truncate -s +1800M "$WORK_DIR/x86_sfs/system.img"
sudo e2fsck -fy "$WORK_DIR/x86_sfs/system.img" || [ $? -le 2 ]
sudo resize2fs "$WORK_DIR/x86_sfs/system.img"
sudo mount -o loop,rw "$WORK_DIR/x86_sfs/system.img" "$WORK_DIR/x86_sys"

echo "==> Injecting & auto-deodexing donor apps..."
SKIP_APPS="VoiceCommand.apk VoiceExtension.apk AtciService.apk EngineerMode.apk YGPS.apk SchedulePowerOnOff.apk MtkFloatMenu.apk Omacp.apk BatteryWarning.apk MtkWeatherProvider.apk ThemeChooser.apk ThemesProvider.apk CyanogenAccount.apk CMSettingsProvider.apk WhisperPush.apk CyanogenSetupWizard.apk Screencast.apk VoicePlus.apk GoogleLoginService.apk GoogleServicesFramework.apk PrebuiltGmsCore.apk Phonesky.apk WebViewGoogle.apk AndroidWebView.apk SystemUI.apk Settings.apk SettingsProvider.apk Framework-res.apk twframework-res.apk TeleService.apk TelephonyProvider.apk ContactsProvider.apk MediaProvider.apk DownloadProvider.apk CalendarProvider.apk PackageInstaller.apk DefaultContainerService.apk InputDevices.apk Keyguard.apk Gmail2.apk SecSettings.apk SecSettingsProvider.apk"

mkdir -p "$WORK_DIR/deodex_tmp"
BOOTCLASSPATH_DIR="$WORK_DIR/donor_sys/framework"

for dir in app priv-app; do
    if [ -d "$WORK_DIR/donor_sys/$dir" ]; then
        find "$WORK_DIR/donor_sys/$dir" -maxdepth 2 -name "*.apk" | while read -r apk; do
            [ -e "$apk" ] || continue
            base=$(basename "$apk" .apk)
            filename=$(basename "$apk")
            if [ "$filename" = "SetupWizard.apk" ]; then
                continue
            fi
            if echo "$SKIP_APPS" | grep -qw "$filename"; then
                continue
            fi
            odex_file="$(dirname "$apk")/$base.odex"
            if [ -d "$(dirname "$apk")/oat" ]; then continue; fi
            if [ -f "$odex_file" ]; then
                if [ -f "$HOME/Downloads/baksmali.jar" ] && [ -f "$HOME/Downloads/smali.jar" ]; then
                    echo "  ~ Deodexing $dir/$filename..."
                    rm -rf "$WORK_DIR/deodex_tmp/out" "$WORK_DIR/deodex_tmp/classes.dex" "$WORK_DIR/deodex_tmp/$filename"
                    cp -f "$apk" "$WORK_DIR/deodex_tmp/$filename"
                    if java -jar "$HOME/Downloads/baksmali.jar" -a 8 -x "$odex_file" -d "$BOOTCLASSPATH_DIR" -o "$WORK_DIR/deodex_tmp/out" 2>/dev/null && \
                       java -jar "$HOME/Downloads/smali.jar" -a 8 "$WORK_DIR/deodex_tmp/out" -o "$WORK_DIR/deodex_tmp/classes.dex" 2>/dev/null; then
                        (cd "$WORK_DIR/deodex_tmp" && zip -q "$filename" classes.dex)
                        echo "  + [DEODEXED] $dir/$filename"
                        sudo cp -f "$WORK_DIR/deodex_tmp/$filename" "$WORK_DIR/x86_sys/$dir/"
                    else
                        echo "  ! Failed to deodex $filename (skipping)"
                    fi
                fi
            else
                echo "  + $dir/$filename"
                sudo cp -f "$apk" "$WORK_DIR/x86_sys/$dir/"
            fi
        done
    fi
done

echo "==> Injecting donor SetupWizard..."
WIZ_APK=$(find "$WORK_DIR/donor_sys/priv-app" "$WORK_DIR/donor_sys/app" -maxdepth 2 -name "SetupWizard.apk" 2>/dev/null | head -n 1)
if [ -n "$WIZ_APK" ]; then
    WIZ_DIR=$(dirname "$WIZ_APK")
    WIZ_BASE=$(basename "$WIZ_APK" .apk)
    WIZ_ODEX="$WIZ_DIR/$WIZ_BASE.odex"
    if [ -f "$WIZ_ODEX" ] && [ -f "$HOME/Downloads/baksmali.jar" ] && [ -f "$HOME/Downloads/smali.jar" ]; then
        echo "  ~ Deodexing SetupWizard.apk..."
        rm -rf "$WORK_DIR/deodex_wiz_auto"
        mkdir -p "$WORK_DIR/deodex_wiz_auto"
        cp -f "$WIZ_APK" "$WORK_DIR/deodex_wiz_auto/SetupWizard.apk"
        if java -jar "$HOME/Downloads/baksmali.jar" -a 8 -x "$WIZ_ODEX" -d "$BOOTCLASSPATH_DIR" -o "$WORK_DIR/deodex_wiz_auto/smali_out" 2>/dev/null && \
           java -jar "$HOME/Downloads/smali.jar" -a 8 "$WORK_DIR/deodex_wiz_auto/smali_out" -o "$WORK_DIR/deodex_wiz_auto/classes.dex" 2>/dev/null && \
           (cd "$WORK_DIR/deodex_wiz_auto" && zip -q SetupWizard.apk classes.dex); then
            sudo cp -f "$WORK_DIR/deodex_wiz_auto/SetupWizard.apk" "$([ -d "$WORK_DIR/x86_sys/priv-app" ] && echo "$WORK_DIR/x86_sys/priv-app" || echo "$WORK_DIR/x86_sys/app")/SetupWizard.apk"
            echo "  + [INJECTED DEODEXED] SetupWizard.apk"
        else
            echo "  ! Deodex failed for SetupWizard.apk; copying raw APK"
            sudo cp -f "$WIZ_APK" "$([ -d "$WORK_DIR/x86_sys/priv-app" ] && echo "$WORK_DIR/x86_sys/priv-app" || echo "$WORK_DIR/x86_sys/app")/SetupWizard.apk"
        fi
    else
        sudo cp -f "$WIZ_APK" "$([ -d "$WORK_DIR/x86_sys/priv-app" ] && echo "$WORK_DIR/x86_sys/priv-app" || echo "$WORK_DIR/x86_sys/app")/SetupWizard.apk"
        echo "  + [INJECTED] SetupWizard.apk"
    fi
else
    echo "  - No SetupWizard.apk found in donor image"
fi

# Also grab any standalone carrier/preload APKs (e.g. Samsung /system/preload or /system/hidden)
for extra_dir in preload hidden; do
    if [ -d "$WORK_DIR/donor_sys/$extra_dir" ]; then
        find "$WORK_DIR/donor_sys/$extra_dir" -name "*.apk" | while read -r extra_apk; do
            echo "  + [$extra_dir] $(basename "$extra_apk")"
            sudo cp -f "$extra_apk" "$WORK_DIR/x86_sys/app/"
        done
    fi
done

echo "==> Injecting donor audio, boot animation & device identity..."
[ -d "$WORK_DIR/donor_sys/media/audio" ] && sudo cp -rf "$WORK_DIR/donor_sys/media/audio/"* "$WORK_DIR/x86_sys/media/audio/"
if [ -f "$HOME/Downloads/bootanimation.zip" ]; then
    echo "  * Injecting custom boot animation..."
    sudo cp -f "$HOME/Downloads/bootanimation.zip" "$WORK_DIR/x86_sys/media/"
fi
if [ -f "$WORK_DIR/donor_sys/build.prop" ]; then
    for prop in ro.product.model ro.product.brand ro.product.name ro.product.device ro.product.manufacturer; do
        val=$(grep "^$prop=" "$WORK_DIR/donor_sys/build.prop" | head -n 1 | cut -d'=' -f2-)
        if [ -n "$val" ]; then
            echo "  * $prop=$val"
            sudo sed -i "s|^$prop=.*|$prop=$val|" "$WORK_DIR/x86_sys/build.prop"
        fi
    done
fi

sudo chmod 644 "$WORK_DIR/x86_sys/app/"*.apk $([ -d "$([ -d "$WORK_DIR/x86_sys/priv-app" ] && echo "$WORK_DIR/x86_sys/priv-app" || echo "$WORK_DIR/x86_sys/app")" ] && echo "$([ -d "$([ -d "$WORK_DIR/x86_sys/priv-app" ] && echo "$WORK_DIR/x86_sys/priv-app" || echo "$WORK_DIR/x86_sys/app")" ] && echo "$([ -d "$WORK_DIR/x86_sys/priv-app" ] && echo "$WORK_DIR/x86_sys/priv-app" || echo "$WORK_DIR/x86_sys/app")" || echo "$WORK_DIR/x86_sys/app")/" || echo "$WORK_DIR/x86_sys/app/")*.apk 2>/dev/null || true

echo "==> Unmounting and rebuilding bootable ISO..."
sudo umount "$WORK_DIR/donor_sys"
sudo umount "$WORK_DIR/x86_sys"

rm -f "$WORK_DIR/iso_work/system.sfs"
mksquashfs "$WORK_DIR/x86_sfs/" "$WORK_DIR/iso_work/system.sfs" -comp gzip

EFI_ARGS=""
[ -f "$WORK_DIR/iso_work/boot/grub/efi.img" ] && EFI_ARGS="-eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot -isohybrid-gpt-basdat"
xorriso -as mkisofs \
  -o "$OUT_ISO" \
  -b isolinux/isolinux.bin \
  -c isolinux/boot.cat \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  $EFI_ARGS \
  "$WORK_DIR/iso_work/"

echo "=========================================="
echo " SUCCESS! Created: $OUT_ISO"
echo "=========================================="
