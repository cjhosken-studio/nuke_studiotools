"""
ST_Write — Studio Tools Pipeline Write Node
plugins/nuke_studiotools/nodes/ST_Write.py

Creates a pipeline-aware Group node that wraps a native Write node.
Auto-constructs a versioned output path under:

    {ST_CWD}/wip/nuke/renders/{render_type}/{render_name}_v{VER}/
        {render_name}_v{VER}.####.{ext}

On render completion writes a metadata.yaml alongside the frames so the
Studio Tools workspace can track the output.

Usage (called from menu.py):
    import ST_Write
    ST_Write.create()
"""

import os
import re
from datetime import datetime

try:
    import nuke
    _IN_NUKE = True
except ImportError:
    _IN_NUKE = False


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_RENDER_TYPES = ["comp", "precomp", "plate", "roto", "grade", "matte", "light"]
_FILE_FORMATS = ["exr", "png", "tiff", "jpg", "dpx"]
_COLORSPACES  = ["linear", "sRGB", "Gamma2.2", "rec709", "ACES - ACEScg",
                 "Output - sRGB", "scene-linear Rec.709-sRGB"]


def _next_version(render_dir, render_name):
    """Scans render_dir for existing {render_name}_vNNN folders and returns next int."""
    version = 1
    if not os.path.isdir(render_dir):
        return version
    for entry in os.listdir(render_dir):
        if os.path.isdir(os.path.join(render_dir, entry)):
            m = re.match(rf"^{re.escape(render_name)}_v(\d+)$", entry, re.IGNORECASE)
            if m:
                version = max(version, int(m.group(1)) + 1)
    return version


def _resolve_path(node):
    """
    Computes the fully resolved output path for the Write node.
    Returns (abs_dir, abs_filepath_with_####, version_int).
    """
    task_path  = os.environ.get("ST_CWD", "")
    render_name = node["render_name"].value().strip() or "comp"
    render_name = re.sub(r"[^a-zA-Z0-9_]", "_", render_name)
    render_type = node["render_type"].value()
    file_fmt    = node["file_format"].value()

    render_root = os.path.join(task_path, "wip", "nuke", "renders", render_type)

    auto_ver = node["auto_version"].value()
    if auto_ver:
        version = _next_version(render_root, render_name)
    else:
        version = max(1, int(node["version_override"].value()))

    ver_str    = f"v{version:03d}"
    ver_folder = f"{render_name}_{ver_str}"
    out_dir    = os.path.join(render_root, ver_folder)
    filename   = f"{render_name}_{ver_str}.####.{file_fmt}"
    full_path  = os.path.join(out_dir, filename)

    return out_dir, full_path, version


def _update_resolved_path(node):
    """Recalculates and displays the resolved output path."""
    try:
        _out_dir, full_path, _ver = _resolve_path(node)
        node["resolved_path"].setValue(full_path)

        # Push path into the internal Write node
        with node:
            write = nuke.toNode("Write1")
            if write:
                write["file"].setValue(full_path)
    except Exception as e:
        node["resolved_path"].setValue(f"(error: {e})")


# ---------------------------------------------------------------------------
# Render + metadata
# ---------------------------------------------------------------------------

def _do_render():
    """Triggered by the Render button knob — executes the Write and writes metadata."""
    node = nuke.thisNode()

    out_dir, full_path, version = _resolve_path(node)
    render_name = node["render_name"].value().strip() or "comp"
    render_name = re.sub(r"[^a-zA-Z0-9_]", "_", render_name)
    file_fmt    = node["file_format"].value()

    # Create output directory
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as e:
        nuke.message(f"[ST_Write] Could not create output directory:\n{out_dir}\n\n{e}")
        return

    # Update write path one final time
    _update_resolved_path(node)

    # Determine frame range
    root = nuke.Root()
    first = int(root["first_frame"].value())
    last  = int(root["last_frame"].value())

    # Execute render
    with node:
        write = nuke.toNode("Write1")
        if not write:
            nuke.message("[ST_Write] Internal Write node not found.")
            return
        write["file"].setValue(full_path)
        fmt_str = node["file_format"].value()
        write["file_type"].setValue(fmt_str)
        cs = node["colorspace"].value().strip()
        if cs:
            try:
                write["colorspace"].setValue(cs)
            except Exception:
                pass

    try:
        nuke.execute(write, first, last)
    except Exception as e:
        nuke.message(f"[ST_Write] Render failed:\n{e}")
        return

    # Write metadata YAML
    _write_metadata(node, out_dir, full_path, version, first, last)

    nuke.message(
        f"✅ Render complete!\n\n"
        f"Name:    {render_name}_v{version:03d}\n"
        f"Frames:  {first}–{last}\n"
        f"Format:  {fmt_str.upper()}\n"
        f"Output:  {out_dir}"
    )
    nuke.tprint(f"[ST_Write] Rendered to: {full_path}")


def _write_metadata(node, out_dir, full_path, version, first, last):
    """Writes a metadata.yaml alongside the render output."""
    task_path  = os.environ.get("ST_CWD", "")
    script_path = nuke.Root()["name"].value()

    render_name = re.sub(r"[^a-zA-Z0-9_]", "_", node["render_name"].value().strip() or "comp")
    render_type = node["render_type"].value()
    file_fmt    = node["file_format"].value()
    colorspace  = node["colorspace"].value().strip()

    lines = [
        f'type: "nuke_render"',
        f'application: "nuke"',
        f'application_version: "{nuke.NUKE_VERSION_STRING}"',
        f'task: "{os.environ.get("ST_TASK", "")}"',
        f'task_area: "{os.environ.get("ST_TASKAREA", "")}"',
        f'render_name: "{render_name}"',
        f'render_type: "{render_type}"',
        f'version: {version}',
        f'frame_range: "{first}-{last}"',
        f'file_format: "{file_fmt}"',
        f'colorspace: "{colorspace}"',
        f'output_path: "{full_path}"',
        f'source_script: "{script_path}"',
        f'date: "{datetime.now().isoformat()}"',
        f'published_by: "{os.environ.get("USER", "artist")}"',
    ]

    meta_path = os.path.join(out_dir, "metadata.yaml")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        nuke.tprint(f"[ST_Write] Metadata written: {meta_path}")
    except Exception as e:
        nuke.tprint(f"[ST_Write] Warning: Failed to write metadata: {e}")


# ---------------------------------------------------------------------------
# knobChanged callback
# ---------------------------------------------------------------------------

def _on_knob_changed():
    """Nuke calls this whenever any knob on ST_Write changes."""
    node = nuke.thisNode()
    knob = nuke.thisKnob()

    if knob.name() in ("render_name", "render_type", "file_format",
                        "auto_version", "version_override"):
        _update_resolved_path(node)


# ---------------------------------------------------------------------------
# Node factory
# ---------------------------------------------------------------------------

def create():
    """Creates and returns a new ST_Write Group node."""
    if not _IN_NUKE:
        raise RuntimeError("ST_Write can only be created inside Nuke.")

    task_name = os.environ.get("ST_TASK", "—")
    task_area = os.environ.get("ST_TASKAREA", "—")

    # Derive a sensible default render name from the task
    default_name = re.sub(r"[^a-zA-Z0-9_]", "_", task_name.lower()) if task_name != "—" else "comp"

    # --- Build the Group ---
    grp = nuke.nodes.Group(
        name="ST_Write",
        tile_color=0xCC4400FF,
        note_font_size=12,
    )
    grp.setName("ST_Write")

    with grp:
        # Input pass-through
        inp = nuke.nodes.Input(name="Input1")
        inp.setXYpos(0, -100)

        # Internal Write node
        write = nuke.nodes.Write(name="Write1")
        write.setXYpos(0, 0)
        write.setInput(0, inp)
        write["file_type"].setValue("exr")

        # Output for viewing upstream
        output = nuke.nodes.Output(name="Output1")
        output.setXYpos(0, 150)
        output.setInput(0, inp)

    # --- Custom knobs ---
    grp.addKnob(nuke.Tab_Knob("st_tab", "Studio Tools"))

    # Context info label
    info_knob = nuke.Text_Knob("context_info", "",
        f"<b style='color:#ff7043'>Task:</b> {task_name} &nbsp;&nbsp; "
        f"<b style='color:#ff7043'>Area:</b> {task_area}")
    info_knob.clearFlag(nuke.STARTLINE)
    grp.addKnob(info_knob)

    grp.addKnob(nuke.Text_Knob("div1", ""))

    # Render name
    name_knob = nuke.String_Knob("render_name", "Render Name", default_name)
    grp.addKnob(name_knob)

    # Render type
    type_knob = nuke.Enumeration_Knob("render_type", "Type", _RENDER_TYPES)
    grp.addKnob(type_knob)

    # File format
    fmt_knob = nuke.Enumeration_Knob("file_format", "Format", _FILE_FORMATS)
    grp.addKnob(fmt_knob)

    # Colorspace
    cs_knob = nuke.String_Knob("colorspace", "Colorspace", "linear")
    grp.addKnob(cs_knob)

    grp.addKnob(nuke.Text_Knob("div2", ""))

    # Auto version toggle
    auto_ver = nuke.Boolean_Knob("auto_version", "Auto Version", True)
    auto_ver.setFlag(nuke.STARTLINE)
    grp.addKnob(auto_ver)

    # Manual version override (only active when auto_version is OFF)
    ver_override = nuke.Int_Knob("version_override", "Version", 1)
    grp.addKnob(ver_override)

    grp.addKnob(nuke.Text_Knob("div3", ""))

    # Resolved path display
    resolved = nuke.File_Knob("resolved_path", "Output Path")
    resolved.setFlag(nuke.READ_ONLY)
    grp.addKnob(resolved)

    # Open folder
    open_btn = nuke.PyScript_Knob(
        "open_folder", "📂 Open Output Folder",
        "import ST_Write, os, subprocess; "
        "p = nuke.thisNode()['resolved_path'].value(); "
        "d = os.path.dirname(p) if p else ''; "
        "subprocess.Popen(['xdg-open', d]) if d and os.path.isdir(d) else None"
    )
    grp.addKnob(open_btn)

    grp.addKnob(nuke.Text_Knob("div4", ""))

    # Render button
    render_btn = nuke.PyScript_Knob(
        "render_btn", "▶  Render",
        "import ST_Write; ST_Write._do_render()"
    )
    grp.addKnob(render_btn)

    # knobChanged
    grp["knobChanged"].setValue(
        "import ST_Write; ST_Write._on_knob_changed()"
    )

    # Initial path resolution
    _update_resolved_path(grp)

    return grp
