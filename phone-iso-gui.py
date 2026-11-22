import sys; sys.argv[0] = "android-vm-workstation"
#!/usr/bin/env python3
import gi, glob, json, os, socket, subprocess, threading, time
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf

WORK_DIR = "/home/kriskaadrian/Downloads"
HOME = os.path.expanduser("~")
DONE_DIR = os.path.join(WORK_DIR, "doneisos")
DISK_DIR, SHOT_DIR, PROF_DIR = [os.path.join(DONE_DIR, x) for x in ("disks", "screenshots", "profiles")]
SCRIPT_PATH = os.path.join(WORK_DIR, "make-phone-iso.sh")
for d in [DONE_DIR, DISK_DIR, SHOT_DIR, PROF_DIR]: os.makedirs(d, exist_ok=True)

THEMES = {
    "VMware Dark": ("#181a1f", "#111317", "#20232a", "#e5e7eb", "#2563eb", "#16a34a"),
    "VirtualBox Light": ("#f3f4f6", "#e5e7eb", "#ffffff", "#111827", "#1d4ed8", "#15803d"),
    "Android Emerald": ("#0d1411", "#080d0b", "#131f1a", "#ecfdf5", "#059669", "#10b981"),
    "Cyber Neon": ("#0b0c14", "#07080e", "#121524", "#e0f2fe", "#7c3aed", "#06b6d4"),
    "Xperia Cosmic": ("#140f24", "#0c0917", "#1e1636", "#f3e8ff", "#9333ea", "#c084fc"),
    "OnePlus Obsidian": ("#121212", "#0a0a0a", "#1c1c1c", "#fafafa", "#eb0028", "#dc2626"),
    "Samsung Midnight": ("#0b1120", "#060a14", "#111b33", "#e2e8f0", "#0284c7", "#38bdf8"),
    "Retro Amber CRT": ("#141008", "#0c0904", "#1f180c", "#fef3c7", "#d97706", "#f59e0b"),
}

def make_css(t):
    bg, sb, card, fg, acc, pwr = THEMES[t]
    return f"window, dialog, menubar, menu, list, row, label, checkbutton label {{ background: {bg}; color: {fg}; }} .sidebar list, .sidebar row, .sidebar label {{ background: {sb}; color: {fg}; }} .card label, .card checkbutton label {{ background: {card}; color: {fg}; }} .sidebar {{ background: {sb}; border-right: 1px solid {acc}; }} .card {{ background: {card}; border: 1px solid {acc}; border-radius: 6px; padding: 12px; }} .thumb-box {{ background: #050608; border: 2px solid {acc}; border-radius: 6px; padding: 8px; }} .power-on {{ background: {pwr}; color: #fff; font-weight: bold; }} .power-off {{ background: #dc2626; color: #fff; font-weight: bold; }} .build-btn {{ background: {acc}; color: #fff; font-weight: bold; }}".encode()
class CreateDiskDialog(Gtk.Dialog):
    def __init__(self, parent, vm_name):
        super().__init__(title="Create Virtual Hard Disk", transient_for=parent, flags=0)
        self.set_default_size(580, 380)
        root = Gtk.Box(spacing=12, margin=12); self.get_content_area().pack_start(root, True, True, 0)
        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); banner.set_size_request(135, -1)
        banner.pack_start(Gtk.Label(label="<span size='50000'>💿</span>\n<b>Virtual Disk</b>", use_markup=True, justify=Gtk.Justification.CENTER), True, True, 0)
        root.pack_start(banner, False, False, 0)

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10); root.pack_start(col, True, True, 0)
        col.pack_start(Gtk.Label(label="<b>File location</b>", use_markup=True, xalign=0), False, False, 0)
        self.loc_e = Gtk.Entry(text=os.path.join(DONE_DIR, f"{vm_name}.qcow2"))
        col.pack_start(self.loc_e, False, False, 0)

        col.pack_start(Gtk.Label(label="<b>File size</b>", use_markup=True, xalign=0), False, False, 0)
        srow = Gtk.Box(spacing=8)
        self.sz_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 64, 1); self.sz_scale.set_value(4); self.sz_scale.set_draw_value(False)
        self.sz_spin = Gtk.SpinButton.new_with_range(1, 64, 1); self.sz_spin.set_value(4)
        self.sz_scale.connect("value-changed", lambda sc: self.sz_spin.set_value(int(sc.get_value())))
        self.sz_spin.connect("value-changed", lambda sp: self.sz_scale.set_value(sp.get_value()))
        srow.pack_start(self.sz_scale, True, True, 0); srow.pack_start(self.sz_spin, False, False, 0); srow.pack_start(Gtk.Label(label="GB"), False, False, 0)
        col.pack_start(srow, False, False, 0)

        split = Gtk.Box(spacing=16); col.pack_start(split, False, False, 4)
        fbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); fbox.pack_start(Gtk.Label(label="<b>Hard disk file type</b>", use_markup=True, xalign=0), False, False, 0)
        self.fmt_qcow = Gtk.RadioButton.new_with_label_from_widget(None, "QCOW (QEMU Copy-On-Write)")
        self.fmt_vdi = Gtk.RadioButton.new_with_label_from_widget(self.fmt_qcow, "VDI (VirtualBox Disk Image)")
        self.fmt_vmdk = Gtk.RadioButton.new_with_label_from_widget(self.fmt_qcow, "VMDK (Virtual Machine Disk)")
        for rb in (self.fmt_qcow, self.fmt_vdi, self.fmt_vmdk): fbox.pack_start(rb, False, False, 0)
        split.pack_start(fbox, True, True, 0)

        abox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); abox.pack_start(Gtk.Label(label="<b>Storage on physical hard disk</b>", use_markup=True, xalign=0), False, False, 0)
        self.alloc_dyn = Gtk.RadioButton.new_with_label_from_widget(None, "Dynamically allocated")
        self.alloc_fix = Gtk.RadioButton.new_with_label_from_widget(self.alloc_dyn, "Fixed size")
        abox.pack_start(self.alloc_dyn, False, False, 0); abox.pack_start(self.alloc_fix, False, False, 0)
        split.pack_start(abox, True, True, 0)

        self.add_buttons("< Back", Gtk.ResponseType.CANCEL, "Create", Gtk.ResponseType.OK); self.show_all()

    def create_disk_file(self):
        fmt = "qcow2" if self.fmt_qcow.get_active() else ("vdi" if self.fmt_vdi.get_active() else "vmdk")
        path = self.loc_e.get_text().strip()
        gb = int(self.sz_spin.get_value())
        cmd = ["qemu-img", "create", "-f", fmt]
        if self.alloc_fix.get_active() and fmt == "qcow2": cmd += ["-o", "preallocation=full"]
        cmd += [path, f"{gb}G"]
        subprocess.run(cmd)

class NewVMDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Create Virtual Machine", transient_for=parent, flags=0)
        self.set_default_size(620, 440)
        root = Gtk.Box(spacing=12, margin=12); self.get_content_area().pack_start(root, True, True, 0)
        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); banner.set_size_request(140, -1)
        banner.pack_start(Gtk.Label(label="<span size='50000'>💠</span>\n<b>New Android\nMachine</b>", use_markup=True, justify=Gtk.Justification.CENTER), True, True, 0)
        root.pack_start(banner, False, False, 0)

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); root.pack_start(col, True, True, 0)
        col.pack_start(Gtk.Label(label="<b>Name and operating system</b>", use_markup=True, xalign=0), False, False, 0)
        self.nm = Gtk.Entry(text="custom-android-device")
        self.base_e = Gtk.Entry(text=os.path.join(HOME, "Downloads", "android-x86-4.4-r5.iso"))
        self.don_e = Gtk.Entry(text=os.path.join(HOME, "Downloads"))
        self.ver_cb = Gtk.ComboBoxText()
        for v in [
            "Android 4.4 KitKat (32-bit x86)",
            "Android 6.0 Marshmallow (32/64-bit x86)",
            "Android 5.1 Lollipop (32-bit x86)",
            "Android 2.3 Gingerbread (32-bit x86)",
            "Android 2.2 Froyo (32-bit x86)",
        ]:
            self.ver_cb.append_text(v)
        self.ver_cb.set_active(0)
        self.ver_cb.connect("changed", self._on_ver_changed)

        for lbl, w, act in [("Name:", self.nm, None), ("Machine Folder:", Gtk.Label(label=DONE_DIR, xalign=0), None), ("Version:", self.ver_cb, None), ("Base Android ISO:", self.base_e, Gtk.FileChooserAction.OPEN), ("Donor ROM (.zip):", self.don_e, Gtk.FileChooserAction.OPEN)]:
            r = Gtk.Box(spacing=6); r.pack_start(Gtk.Label(label=lbl, width_chars=17, xalign=0), False, False, 0); r.pack_start(w, True, True, 0)
            if act is not None:
                br = Gtk.Button(label="📁"); br.connect("clicked", lambda _, e=w, a=act: self._pick(e, a)); r.pack_start(br, False, False, 0)
            col.pack_start(r, False, False, 0)

        col.pack_start(Gtk.Label(label="<b>Memory size</b>", use_markup=True, xalign=0), False, False, 0)
        mrow = Gtk.Box(spacing=8)
        self.mem_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 512, 4096, 256); self.mem_sc.set_value(2048); self.mem_sc.set_draw_value(False)
        self.mem_sp = Gtk.SpinButton.new_with_range(512, 4096, 256); self.mem_sp.set_value(2048)
        self.mem_sc.connect("value-changed", lambda sc: self.mem_sp.set_value(int(sc.get_value())))
        self.mem_sp.connect("value-changed", lambda sp: self.mem_sc.set_value(sp.get_value()))
        mrow.pack_start(self.mem_sc, True, True, 0); mrow.pack_start(self.mem_sp, False, False, 0); mrow.pack_start(Gtk.Label(label="MB"), False, False, 0)
        col.pack_start(mrow, False, False, 0)

        col.pack_start(Gtk.Label(label="<b>Hard disk</b>", use_markup=True, xalign=0), False, False, 0)
        self.hd_none = Gtk.RadioButton.new_with_label_from_widget(None, "Do not add a virtual hard disk")
        self.hd_new = Gtk.RadioButton.new_with_label_from_widget(self.hd_none, "Create a virtual hard disk now")
        self.hd_use = Gtk.RadioButton.new_with_label_from_widget(self.hd_none, "Use an existing virtual hard disk file")
        self.hd_new.set_active(True)
        for rb in (self.hd_none, self.hd_new, self.hd_use): col.pack_start(rb, False, False, 0)

        self.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Create", Gtk.ResponseType.OK); self.show_all()
        if self.run() == Gtk.ResponseType.OK:
            vm_nm = self.nm.get_text().strip() or "custom-android"
            if self.hd_new.get_active():
                dd = CreateDiskDialog(self, vm_nm)
                if dd.run() == Gtk.ResponseType.OK: dd.create_disk_file()
                dd.destroy()
            cmd = ["pkexec", "bash", SCRIPT_PATH, self.base_e.get_text().strip(), self.don_e.get_text().strip(), vm_nm]
            threading.Thread(target=lambda: (subprocess.run(cmd), GLib.idle_add(parent.refresh_vms)), daemon=True).start()
        self.destroy()

    def _on_ver_changed(self, cb):
        txt = cb.get_active_text() or ""
        dl = os.path.join(HOME, "Downloads")
        rules = [
            ("6.0", "android-x86-6.0-r3.iso", 2048),
            ("5.1", "android-x86-5.1-rc1.iso", 2048),
            ("4.4", "android-x86-4.4-r5.iso", 2048),
            ("2.3", "android-x86-2.3-RC1-eeepc.iso", 1024),
            ("2.2", "android-x86-2.2-r2-eeepc.iso", 1024),
        ]
        for tag, default_iso, ram in rules:
            if tag in txt:
                matches = sorted(glob.glob(os.path.join(dl, f"*{tag}*.iso")))
                chosen = matches if matches else os.path.join(dl, default_iso)
                self.base_e.set_text(chosen[0] if isinstance(chosen, list) else chosen)
                if hasattr(self, "mem_sp"): self.mem_sp.set_value(ram)
                break

    def _pick(self, ent, act):
        fc = Gtk.FileChooserDialog(title="Select File", parent=self, action=act)
        fc.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK)
        if fc.run() == Gtk.ResponseType.OK: ent.set_text(fc.get_filename())
        fc.destroy()

class VBoxSettingsModal(Gtk.Dialog):
    def __init__(self, parent):
        nm = os.path.basename(parent.selected_iso) if parent.selected_iso else "VM"
        super().__init__(title=f"{nm} - Settings", transient_for=parent, flags=0)
        self.set_default_size(640, 390)
        main = Gtk.Box(spacing=10, margin=10); self.get_content_area().pack_start(main, True, True, 0)
        cats = Gtk.ListBox(); cats.set_size_request(155, -1); stack = Gtk.Stack()
        for ico, tit in [("⚙", "General"), ("🖥", "System"), ("📺", "Display"), ("💿", "Storage"), ("🖱", "Input & Audio")]:
            r = Gtk.ListBoxRow(); r.cat = tit; r.add(Gtk.Label(label=f"  {ico}  {tit}", xalign=0, margin=8)); cats.add(r)
        cats.connect("row-selected", lambda _, r: stack.set_visible_child_name(r.cat) if r else None)
        main.pack_start(cats, False, False, 0); main.pack_start(stack, True, True, 0)

        p_gen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=10)
        p_gen.pack_start(Gtk.Label(label=f"<b>Name:</b> {nm}", use_markup=True, xalign=0), False, False, 0)
        p_gen.pack_start(Gtk.Label(label="<b>Type:</b> Linux / Android-x86 (32/64-bit)", use_markup=True, xalign=0), False, False, 0)
        stack.add_named(p_gen, "General")

        p_sys = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
        for l, w in [("Base Memory (MB):", parent.ram_cb), ("Processor(s):", parent.cpu_cb)]:
            if w.get_parent(): w.get_parent().remove(w)
            r = Gtk.Box(spacing=8); r.pack_start(Gtk.Label(label=l, width_chars=18, xalign=0), False, False, 0); r.pack_start(w, True, True, 0); p_sys.pack_start(r, False, False, 0)
        p_sys.pack_start(Gtk.Label(label="Acceleration: VT-x/AMD-V, Nested Paging, KVM Paravirtualization", xalign=0), False, False, 0)
        stack.add_named(p_sys, "System")

        p_dsp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
        for l, w in [("Display Preset:", parent.res_cb), ("Graphics Controller:", parent.gpu_cb)]:
            if w.get_parent(): w.get_parent().remove(w)
            r = Gtk.Box(spacing=8); r.pack_start(Gtk.Label(label=l, width_chars=18, xalign=0), False, False, 0); r.pack_start(w, True, True, 0); p_dsp.pack_start(r, False, False, 0)
        if parent.fs_chk.get_parent(): parent.fs_chk.get_parent().remove(parent.fs_chk)
        p_dsp.pack_start(parent.fs_chk, False, False, 0)
        stack.add_named(p_dsp, "Display")

        p_sto = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
        p_sto.pack_start(Gtk.Label(label=f"<b>IDE Secondary (Optical):</b> {nm}", use_markup=True, xalign=0), False, False, 0)
        if parent.disk_chk.get_parent(): parent.disk_chk.get_parent().remove(parent.disk_chk)
        p_sto.pack_start(parent.disk_chk, False, False, 0)
        stack.add_named(p_sto, "Storage")

        p_inp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
        if parent.ptr_cb.get_parent(): parent.ptr_cb.get_parent().remove(parent.ptr_cb)
        r = Gtk.Box(spacing=8); r.pack_start(Gtk.Label(label="Pointing Device:", width_chars=18, xalign=0), False, False, 0); r.pack_start(parent.ptr_cb, True, True, 0); p_inp.pack_start(r, False, False, 0)
        p_inp.pack_start(Gtk.Label(label="Audio: PulseAudio (ICH AC97)  |  Network: NAT (ADB 5555)", xalign=0), False, False, 0)
        stack.add_named(p_inp, "Input & Audio")

        self.add_buttons("Close", Gtk.ResponseType.OK); self.show_all(); cats.select_row(cats.get_row_at_index(0))
        self.run(); parent.update_vbox_details(); self.destroy()

class WorkstationApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Android VM Workstation Pro")
        self.set_default_size(1000, 650); self.cur_theme = "VMware Dark"
        self.css_p = Gtk.CssProvider(); self.css_p.load_from_data(make_css(self.cur_theme))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.css_p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.selected_iso = None; self.procs = {}
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL); self.add(paned)
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6); sb.get_style_context().add_class("sidebar"); sb.set_size_request(265, -1)
        new_b = Gtk.Button(label="+ Create New VM", margin=8); new_b.get_style_context().add_class("build-btn"); new_b.connect("clicked", lambda _: NewVMDialog(self)); sb.pack_start(new_b, False, False, 2)
        sb.pack_start(Gtk.Label(label="<b>  🧰  Tools  •  Virtual Machines</b>", use_markup=True, xalign=0), False, False, 2)
        self.listbox = Gtk.ListBox(); self.listbox.connect("row-selected", self.on_select_vm)
        sc = Gtk.ScrolledWindow(); sc.add(self.listbox); sb.pack_start(sc, True, True, 0)
        ref = Gtk.Button(label="Refresh Library", margin=8); ref.connect("clicked", lambda _: self.refresh_vms()); sb.pack_end(ref, False, False, 0)
        paned.add1(sb)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=16); paned.add2(box)
        self.vm_title = Gtk.Label(label="<b>Select a Device from Library</b>", use_markup=True, xalign=0); box.pack_start(self.vm_title, False, False, 0)
        bar = Gtk.Box(spacing=6)
        on_b = Gtk.Button(label="▶ Power On"); on_b.get_style_context().add_class("power-on"); on_b.connect("clicked", self.power_on)
        off_b = Gtk.Button(label="■ Power Off"); off_b.get_style_context().add_class("power-off"); off_b.connect("clicked", self.power_off)
        shot_b = Gtk.Button(label="Capture Thumbnail"); shot_b.connect("clicked", lambda _: self.capture_thumb(self.selected_iso))
        apk_b = Gtk.Button(label="Sideload APK..."); apk_b.connect("clicked", self.sideload_apk)
        ba_btn = Gtk.Button(label="🎬 Boot Animation"); ba_btn.connect("clicked", lambda _: BootAnimDialog(self)); bar.pack_start(ba_btn, False, False, 0)
        th_cb = self._combo(list(THEMES.keys()), 0); th_cb.connect("changed", self._set_theme)
        for ico, lbl, fn in [("💠", "New", lambda _: NewVMDialog(self)), ("⚙️", "Settings", lambda _: VBoxSettingsModal(self)), ("↩️", "Discard", lambda _: self._disk_action("reset")), ("➡️", "Start", self.power_on), ("⏹️", "Stop", self.power_off), ("📦", "APK", self.sideload_apk), ("ℹ️", "About", self._vbox_about)]:
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            vb.pack_start(Gtk.Label(label=f"<span size='large'>{ico}</span>", use_markup=True), False, False, 0)
            vb.pack_start(Gtk.Label(label=f"<small>{lbl}</small>", use_markup=True), False, False, 0)
            b_v = Gtk.Button(); b_v.add(vb); b_v.connect("clicked", fn); bar.pack_start(b_v, False, False, 0)
        bar.pack_end(th_cb, False, False, 0); bar.pack_end(Gtk.Label(label="Theme: "), False, False, 0)
        box.pack_start(bar, False, False, 0)
        cbar = Gtk.Box(spacing=6)
        for lbl, fn in [
            ("🔄 Rotate", self._adb_rotate),
            ("📸 Screenshot", self._adb_screenshot),
            ("💻 ADB Shell", self._adb_shell),
            ("🔁 Reboot", lambda _: self._adb_cmd("reboot")),
            ("📝 build.prop", lambda _: BuildPropDialog(self)),
            ("🐞 Logcat", lambda _: LogcatDialog(self)),
            ("📋 Clone Disk", lambda _: self._disk_action("clone")),
            ("🧹 Wipe Disk", lambda _: self._disk_action("reset")),
            ("🗑 Delete VM", lambda _: self._disk_action("delete")),
        ]:
            b_tool = Gtk.Button(label=lbl); b_tool.connect("clicked", fn); cbar.pack_start(b_tool, False, False, 0)
        box.pack_start(cbar, False, False, 2)
        split = Gtk.Box(spacing=12)
        tframe = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); tframe.get_style_context().add_class("thumb-box")
        self.thumb_img = Gtk.Image.new_from_icon_name("computer", Gtk.IconSize.DIALOG); self.thumb_img.set_size_request(300, 190)
        tframe.pack_start(self.thumb_img, True, True, 0); tframe.pack_start(Gtk.Label(label="<small>Live Screen Preview</small>", use_markup=True), False, False, 0)
        split.pack_start(tframe, False, False, 0)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); card.get_style_context().add_class("card")
        self.cpu_cb = self._combo(["1", "2", "4"], 1); self.ram_cb = self._combo(["1024", "2048", "3072", "4096"], 1)
        self.res_cb = self._combo(["720x1280", "1080x1920", "1280x800", "1024x768"], 0); self.gpu_cb = self._combo(["VMware SVGA (2D)", "VirGL 3D Accelerated", "Standard VGA"], 0)
        self.ptr_cb = self._combo(["USB Mouse", "Touchscreen Tablet (1:1)"], 0)
        self.fs_chk = Gtk.CheckButton(label="Start QEMU in Fullscreen (Ctrl+Alt+F exits)")
        self.disk_chk = Gtk.CheckButton(label="Attach Persistent Virtual Disk (.qcow2)", active=True); self.disk_chk.connect("toggled", lambda _: self.update_vbox_details())
        for lbl, w in [("CPU Cores:", self.cpu_cb), ("Memory (RAM):", self.ram_cb), ("Display Preset:", self.res_cb), ("QEMU Graphics:", self.gpu_cb), ("Pointer Mode:", self.ptr_cb)]:
            r = Gtk.Box(spacing=6); r.pack_start(Gtk.Label(label=lbl, width_chars=14, xalign=0), False, False, 0); r.pack_start(w, True, True, 0); card.pack_start(r, False, False, 0)
        card.pack_start(self.fs_chk, False, False, 0); card.pack_start(self.disk_chk, False, False, 0)
        split.pack_start(card, True, True, 0); box.pack_start(split, False, False, 0)
        det_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); det_card.get_style_context().add_class("card")
        det_card.pack_start(Gtk.Label(label="<b>📋 Machine Hardware Details</b>", use_markup=True, xalign=0), False, False, 2)
        det_card.pack_start(self._build_vbox_details(), True, True, 0)
        box.pack_start(det_card, True, True, 6); self.update_vbox_details()
        self.refresh_vms(); GLib.timeout_add(2500, self._poll_procs)
    def _combo(self, vals, idx):
        c = Gtk.ComboBoxText()
        for v in vals: c.append_text(v)
        c.set_active(idx); return c

    def _set_theme(self, cb):
        self.cur_theme = cb.get_active_text(); self.css_p.load_from_data(make_css(self.cur_theme))

    def _thumb_path(self, iso): return os.path.join(SHOT_DIR, os.path.basename(iso).replace(".iso", "") + ".ppm")

    def _load_thumb(self, iso):
        tp = self._thumb_path(iso) if iso else ""
        if tp and os.path.exists(tp):
            try: self.thumb_img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(tp).scale_simple(300, 190, GdkPixbuf.InterpType.BILINEAR)); return
            except Exception: pass
        self.thumb_img.set_from_icon_name("computer", Gtk.IconSize.DIALOG)

    def capture_thumb(self, iso):
        if iso and iso in self.procs and self.procs[iso].poll() is None:
            self._mon(iso, f"screendump {self._thumb_path(iso)}"); GLib.timeout_add(300, lambda: (self._load_thumb(self.selected_iso), False))

    def refresh_vms(self):
        sel = self.selected_iso
        for c in self.listbox.get_children(): self.listbox.remove(c)
        for iso in sorted(glob.glob(os.path.join(DONE_DIR, "*.iso"))):
            bn = os.path.basename(iso)
            ver = "6.0" if "6.0" in bn else "5.1" if "5.1" in bn else "4.4" if "4.4" in bn else "2.3" if "2.3" in bn else "2.2" if "2.2" in bn else "x86"
            run = iso in self.procs and self.procs[iso].poll() is None
            st = "<span foreground='#22c55e'>▶ Running</span>" if run else "⏻ Powered Off"
            row = Gtk.ListBoxRow(); row.iso_path = iso
            hb = Gtk.Box(spacing=8, margin=6)
            badge = Gtk.Label(label=f"<span background='#2563eb' foreground='#ffffff' weight='bold'> {ver} </span>", use_markup=True)
            hb.pack_start(badge, False, False, 0)
            hb.pack_start(Gtk.Label(label=f"<b>{bn}</b>\n<small>{st}</small>", use_markup=True, xalign=0), True, True, 0)
            row.add(hb); self.listbox.add(row)
            if iso == sel: self.listbox.select_row(row)
        self.listbox.show_all()

    def _poll_procs(self):
        dead = [k for k, p in self.procs.items() if p.poll() is not None]
        if dead:
            for k in dead: del self.procs[k]
            self.refresh_vms()
        if self.selected_iso in self.procs: self.capture_thumb(self.selected_iso)
        return True

    def on_select_vm(self, _, row):
        if row:
            self.selected_iso = row.iso_path; stem = os.path.basename(self.selected_iso).replace(".iso", "")
            pf = os.path.join(PROF_DIR, f"{stem}.json")
            if os.path.exists(pf):
                d = json.load(open(pf))
                for cb, k, opts in [(self.cpu_cb, "cpu", ["1","2","4"]), (self.ram_cb, "ram", ["1024","2048","3072","4096"]), (self.res_cb, "res", ["720x1280","1080x1920","1280x800","1024x768"]), (self.gpu_cb, "gpu", ["VMware SVGA (2D)","VirGL 3D Accelerated","Standard VGA"])]:
                    if d.get(k) in opts: cb.set_active(opts.index(d[k]))
            self.vm_title.set_markup(f"<b>{os.path.basename(self.selected_iso)}</b>  ({os.path.getsize(self.selected_iso)//1048576} MB)")
            self.update_vbox_details()
            self._load_thumb(self.selected_iso)

    def _mon(self, iso, cmd):
        sock = f"/tmp/vm_{os.path.basename(iso)}.sock"
        if os.path.exists(sock):
            try: s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(sock); s.settimeout(0.2); s.recv(512); s.sendall((cmd + "\n").encode()); time.sleep(0.15); s.close()
            except Exception: pass

    def _build_vbox_details(self):
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); sc.set_min_content_height(210)
        self.details_lbl = Gtk.Label(xalign=0, yalign=0, use_markup=True, margin=10); self.details_lbl.set_line_wrap(True)
        sc.add(self.details_lbl); return sc

    def update_vbox_details(self):
        if not hasattr(self, "details_lbl"): return
        iso = getattr(self, "selected_iso", None)
        if not iso:
            self.details_lbl.set_markup("<span foreground='#94a3b8'>Select a Virtual Machine from the left sidebar to inspect hardware details.</span>")
            return
        name = iso[4:] if iso.startswith("AVD:") else os.path.basename(iso)
        os_type = "Android SDK AVD (Goldfish / x86)" if iso.startswith("AVD:") else "Android-x86 Custom Image (32/64-bit)"
        ram = self.ram_cb.get_active_text() if hasattr(self, "ram_cb") else "2048"
        cpus = self.cpu_cb.get_active_text() if hasattr(self, "cpu_cb") else "2"
        res = self.res_cb.get_active_text() if hasattr(self, "res_cb") else "720x1280"
        gpu = self.gpu_cb.get_active_text() if hasattr(self, "gpu_cb") else "VMware SVGA (2D)"
        ptr = self.ptr_cb.get_active_text() if hasattr(self, "ptr_cb") else "USB Mouse"
        if iso.startswith("AVD:"):
            opt = "None (SDK System Image)"
            vd = os.path.expanduser(f"~/.android/avd/{name}.avd/userdata-qemu.img")
            vd_txt = f"userdata-qemu.img ({os.path.getsize(vd)//1048576} MB)" if os.path.exists(vd) else "Not created yet"
        else:
            sz = os.path.getsize(iso) // 1048576 if os.path.exists(iso) else 0
            opt = f"[Optical Drive] {name} ({sz} MB)"
            qd = iso.replace(".iso", ".qcow2")
            vd_txt = f"{os.path.basename(qd)} ({os.path.getsize(qd)//1048576} MB)" if os.path.exists(qd) else "None / Auto-create on boot"
        self.details_lbl.set_markup(f"""<b>🖥 General</b>
  <b>Name:</b>  {name}
  <b>Operating System:</b>  {os_type}

<b>⚙ System</b>
  <b>Base Memory:</b>  {ram} MB  |  <b>Processors:</b>  {cpus} CPU
  <b>Acceleration:</b>  KVM Hardware Virtualization (VT-x/AMD-V)

<b>📺 Display</b>
  <b>Resolution:</b>  {res}  |  <b>Graphics Controller:</b>  {gpu}

<b>💿 Storage</b>
  <b>IDE Secondary (Optical):</b>  {opt}
  <b>SATA / Virtual Disk:</b>  {vd_txt}

<b>🔊 Audio &amp; 🌐 Network</b>
  <b>Audio:</b>  PulseAudio (ICH AC97)  |  <b>Network:</b>  NAT (ADB 127.0.0.1:5555)

<b>🖱 USB &amp; Input</b>
  <b>USB Controller:</b>  OHCI / EHCI  |  <b>Pointer:</b>  {ptr}""")

    def _adb_cmd(self, cmd):
        threading.Thread(target=lambda: subprocess.run(f"~/platform-tools/adb connect 127.0.0.1:5555 >/dev/null 2>&1; ~/platform-tools/adb {cmd}", shell=True), daemon=True).start()

    def _adb_rotate(self, _):
        self._rot = 1 - getattr(self, "_rot", 0)
        self._adb_cmd(f"shell 'settings put system accelerometer_rotation 0; settings put system user_rotation {self._rot}'")

    def _adb_screenshot(self, _):
        os.makedirs(os.path.expanduser("~/Pictures"), exist_ok=True)
        out = os.path.expanduser(f"~/Pictures/AndroidVM_{int(time.time())}.png")
        threading.Thread(target=lambda: (subprocess.run(f"~/platform-tools/adb connect 127.0.0.1:5555 >/dev/null 2>&1; ~/platform-tools/adb exec-out screencap -p > '{out}'", shell=True), GLib.idle_add(lambda: self.vm_title.set_markup(f"<b>Saved Screenshot:</b> {os.path.basename(out)}"))), daemon=True).start()

    def _adb_shell(self, _):
        subprocess.Popen("x-terminal-emulator -e bash -c '~/platform-tools/adb connect 127.0.0.1:5555; ~/platform-tools/adb root; ~/platform-tools/adb shell; exec bash'", shell=True)

    def _disk_action(self, act):
        iso = getattr(self, "selected_iso", None)
        if not iso or iso.startswith("AVD:"): return
        qd = iso.replace(".iso", ".qcow2")
        if act == "clone" and os.path.exists(qd):
            shutil.copy2(qd, qd + f".bak_{int(time.time())}")
            self.vm_title.set_markup(f"<b>Cloned Disk:</b> {os.path.basename(qd)}.bak")
        elif act == "reset" and os.path.exists(qd):
            os.remove(qd); self.update_vbox_details()
            self.vm_title.set_markup(f"<b>Factory Reset Disk:</b> {os.path.basename(qd)} wiped")
        elif act == "delete":
            if os.path.exists(qd): os.remove(qd)
            if os.path.exists(iso): os.remove(iso)
            self.selected_iso = None; self.refresh_vms(); self.update_vbox_details()

    def _vbox_about(self, _):
        d = Gtk.Dialog(title="Android VM Workstation Pro - About", transient_for=self, flags=0); d.set_default_size(440, 240)
        b = d.get_content_area(); b.set_spacing(8); b.set_margin_start(18); b.set_margin_end(18); b.set_margin_top(14)
        b.pack_start(Gtk.Label(label="<span size='xx-large' weight='bold'>📦 Android VM Workstation Pro</span>\n<span size='x-large' foreground='#22c55e' weight='bold'>Version 2.0</span>", use_markup=True), False, False, 4)
        b.pack_start(Gtk.Label(label="VirtualBox-Inspired Custom Android Hypervisor\nQEMU/KVM + Android SDK AVD + Donor ROM Builder", justify=Gtk.Justification.CENTER), False, False, 4)
        d.add_buttons("Close", Gtk.ResponseType.CLOSE); d.show_all(); d.run(); d.destroy()

    def power_on(self, _):
        iso = self.selected_iso
        if not iso or (iso in self.procs and self.procs[iso].poll() is None): return
        sock = f"/tmp/vm_{os.path.basename(iso)}.sock"
        if os.path.exists(sock): os.remove(sock)
        gpu = self.gpu_cb.get_active_text(); disp = "gtk,gl=on,zoom-to-fit=on,grab-on-hover=on" if "VirGL" in gpu else "gtk,zoom-to-fit=on,grab-on-hover=on"
        vga = ["-vga", "virtio" if "VirGL" in gpu else ("std" if "Standard" in gpu else "vmware"), "-display", disp]
        ptr = "usb-tablet" if "Tablet" in self.ptr_cb.get_active_text() else "usb-mouse"
        cmd = ["qemu-system-x86_64", "-enable-kvm", "-name", f"Android Console • {os.path.basename(iso)}", "-m", self.ram_cb.get_active_text(), "-smp", self.cpu_cb.get_active_text(), "-cdrom", iso] + vga + ["-usb", "-device", ptr, "-device", "AC97", "-net", "nic", "-net", "user,hostfwd=tcp::5555-:5555", "-monitor", f"unix:{sock},server,nowait"]
        if self.fs_chk.get_active(): cmd.append("-full-screen")
        if self.disk_chk.get_active():
            qcow = os.path.join(DISK_DIR, os.path.basename(iso).replace(".iso", "") + ".qcow2")
            if not os.path.exists(qcow): subprocess.run(["qemu-img", "create", "-f", "qcow2", qcow, "4G"])
            cmd += ["-drive", f"file={qcow},format=qcow2,if=virtio"]
        env = os.environ.copy(); os.makedirs("/tmp/qemu_skin/gtk-3.0", exist_ok=True); open("/tmp/qemu_skin/gtk-3.0/gtk.css", "wb").write(make_css(self.cur_theme)); env["XDG_CONFIG_HOME"] = "/tmp/qemu_skin"
        self.procs[iso] = subprocess.Popen(cmd, cwd=WORK_DIR, env=env); self.refresh_vms()
        res = self.res_cb.get_active_text()
        def auto_res():
            time.sleep(2.8); self._mon(iso, "sendkey tab")
            for ch in f" UVESA_MODE={res}":
                if ch == "_": self._mon(iso, "sendkey shift-minus")
                else: self._mon(iso, f"sendkey {'spc' if ch == ' ' else ('equal' if ch == '=' else (f'shift-{ch.lower()}' if ch.isupper() else ch))}")
                time.sleep(0.03)
            self._mon(iso, "sendkey ret")
        threading.Thread(target=auto_res, daemon=True).start()

    def power_off(self, _):
        iso = self.selected_iso
        if iso in self.procs:
            proc = self.procs.pop(iso)
            threading.Thread(target=lambda: (self._mon(iso, "quit"), proc.kill()), daemon=True).start()
            self.refresh_vms()

    def sideload_apk(self, _):
        d = Gtk.FileChooserDialog(title="Select APK", parent=self, action=Gtk.FileChooserAction.OPEN)
        d.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        if d.run() == Gtk.ResponseType.ACCEPT:
            apk = d.get_filename()
            threading.Thread(target=lambda: (subprocess.run(["adb", "connect", "127.0.0.1:5555"]), subprocess.run(["adb", "-s", "127.0.0.1:5555", "install", "-r", apk])), daemon=True).start()
        d.destroy()

win = WorkstationApp(); win.connect("destroy", Gtk.main_quit); win.show_all(); Gtk.main()