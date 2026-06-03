"""
ST_Read — Studio Tools Pipeline Read Node
plugins/nuke_studiotools/nodes/ST_Read.py

Creates a pipeline-aware Group node that wraps a native Read node.
Scans ST_CWD for published and versioned deliverables (images, EXR, USD, etc.)
and exposes a version dropdown that live-updates the Read path.

Usage (called from menu.py):
    import ST_Read
    ST_Read.create()
"""

import os
import re

try:
    import nuke
    _IN_NUKE = True
except ImportError:
    _IN_NUKE = False


# ---------------------------------------------------------------------------
# Supported read extensions (images + USD for reference)
# ---------------------------------------------------------------------------
_READ_EXTS = {".exr", ".png", ".tiff", ".tif", ".jpg", ".jpeg",
              ".dpx", ".cin", ".hdr", ".tex",
              ".usd", ".usda", ".usdc", ".abc"}

# Sequence pattern — replaces frame numbers with ####
_FRAME_PAT = re.compile(r"\.(\d{2,8})\.(exr|png|tiff?|jpg|jpeg|dpx|cin|hdr|tex)$",
                         re.IGNORECASE)


# ---------------------------------------------------------------------------
# Disk scanning helpers
# ---------------------------------------------------------------------------

def _scan_deliverables(task_path):
    """
    Scans versions/ and published/ under task_path for renderable files.

    Returns a list of dicts:
        {
            "label":    display name shown in the dropdown,
            "path":     absolute path (with #### for sequences),
            "category": "published" | "versions",
            "version":  version string e.g. "v003" or "",
        }
    """
    results = []
    if not task_path or not os.path.isdir(task_path):
        return results

    for category in ("published", "versions"):
        cat_dir = os.path.join(task_path, category)
        if not os.path.isdir(cat_dir):
            continue

        for root, _dirs, files in os.walk(cat_dir, followlinks=True):
            seen_sequences = set()
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext not in _READ_EXTS:
                    continue

                full = os.path.join(root, f)
                rel  = os.path.relpath(full, task_path)

                # Collapse frame sequences to #### notation
                seq_match = _FRAME_PAT.search(f)
                if seq_match:
                    seq_base = _FRAME_PAT.sub(
                        lambda m: f".{'#' * len(m.group(1))}.{m.group(2)}", f
                    )
                    seq_path = os.path.join(root, seq_base)
                    if seq_path in seen_sequences:
                        continue
                    seen_sequences.add(seq_path)
                    display_path = seq_path
                    abs_path = seq_path
                else:
                    display_path = full
                    abs_path = full

                # Extract version string from directory name
                ver_match = re.search(r"_v(\d+)", os.path.basename(root), re.IGNORECASE)
                ver_str = f"v{int(ver_match.group(1)):03d}" if ver_match else ""

                label = f"[{category}]  {os.path.relpath(display_path, task_path)}"
                results.append({
                    "label":    label,
                    "path":     abs_path,
                    "category": category,
                    "version":  ver_str,
                })

    return results


# ---------------------------------------------------------------------------
# knobChanged callback (stored as a module-level function so Nuke can
# serialise the call as a string into the script)
# ---------------------------------------------------------------------------

def _on_knob_changed():
    """Called by Nuke whenever any knob on an ST_Read node changes."""
    node = nuke.thisNode()
    knob = nuke.thisKnob()

    if knob.name() in ("version_selector", "inputChange"):
        _sync_read_path(node)


def _sync_read_path(node):
    """Updates the internal Read node's file knob from the selected version."""
    try:
        entries = node["_entries"].value()   # JSON-encoded list stored as string
        import json
        items = json.loads(entries) if entries.strip() else []
    except Exception:
        items = []

    idx = node["version_selector"].value()
    if not items or idx >= len(items):
        return

    selected = items[int(idx)]
    path = selected.get("path", "")

    # Update display knob
    node["resolved_path"].setValue(path)

    # Push into the internal Read node
    try:
        with node:
            read = nuke.toNode("Read1")
            if read:
                read["file"].setValue(path)
                read["reload"].execute()
    except Exception as e:
        nuke.tprint(f"[ST_Read] Failed to update Read node: {e}")


def _refresh():
    """Re-scans disk and rebuilds the version dropdown."""
    node = nuke.thisNode()
    _populate_node(node)


def _populate_node(node):
    """Scans disk and fills the version_selector knob."""
    import json
    task_path = os.environ.get("ST_CWD", "")
    items = _scan_deliverables(task_path)

    if not items:
        node["version_selector"].setValues(["(no deliverables found)"])
        node["_entries"].setValue("[]")
        node["resolved_path"].setValue("")
        return

    labels = [it["label"] for it in items]
    node["version_selector"].setValues(labels)
    node["_entries"].setValue(json.dumps(items))
    node["version_selector"].setValue(0)
    _sync_read_path(node)


# ---------------------------------------------------------------------------
# Node factory
# ---------------------------------------------------------------------------

def create():
    """Creates and returns a new ST_Read Group node."""
    if not _IN_NUKE:
        raise RuntimeError("ST_Read can only be created inside Nuke.")

    task_path = os.environ.get("ST_CWD", "")
    task_name = os.environ.get("ST_TASK", "—")
    task_area = os.environ.get("ST_TASKAREA", "—")

    # --- Build the Group ---
    grp = nuke.nodes.Group(
        name="ST_Read",
        tile_color=0x0099CCFF,
        note_font_size=12,
    )
    grp.setName("ST_Read")

    with grp:
        # Internal Read node
        read = nuke.nodes.Read(name="Read1")
        read.setXYpos(0, 0)

        # Output
        output = nuke.nodes.Output(name="Output1")
        output.setInput(0, read)
        output.setXYpos(0, 150)

    # --- Add custom knobs ---
    grp.addKnob(nuke.Tab_Knob("st_tab", "Studio Tools"))

    # Context info
    info_knob = nuke.Text_Knob("context_info", "",
        f"<b style='color:#00bcd4'>Task:</b> {task_name} &nbsp;&nbsp; "
        f"<b style='color:#00bcd4'>Area:</b> {task_area}")
    info_knob.clearFlag(nuke.STARTLINE)
    grp.addKnob(info_knob)

    grp.addKnob(nuke.Text_Knob("divider1", ""))

    # Version selector
    version_sel = nuke.Enumeration_Knob("version_selector", "Version", ["(scanning...)"])
    grp.addKnob(version_sel)

    # Resolved path (read-only display)
    resolved = nuke.File_Knob("resolved_path", "Path")
    resolved.setFlag(nuke.READ_ONLY)
    grp.addKnob(resolved)

    grp.addKnob(nuke.Text_Knob("divider2", ""))

    # Refresh button
    refresh_btn = nuke.PyScript_Knob(
        "refresh_btn", "↺ Refresh",
        "import ST_Read; ST_Read._refresh()"
    )
    grp.addKnob(refresh_btn)

    # Open in file manager
    open_btn = nuke.PyScript_Knob(
        "open_folder", "📂 Open Folder",
        "import ST_Read, os, subprocess; "
        "p = nuke.thisNode()['resolved_path'].value(); "
        "d = os.path.dirname(p) if p else ''; "
        "subprocess.Popen(['xdg-open', d]) if d and os.path.isdir(d) else None"
    )
    grp.addKnob(open_btn)

    # Hidden storage for serialised entry list
    entries_knob = nuke.String_Knob("_entries", "_entries", "[]")
    entries_knob.setFlag(nuke.INVISIBLE)
    grp.addKnob(entries_knob)

    # knobChanged callback
    grp["knobChanged"].setValue(
        "import ST_Read; ST_Read._on_knob_changed()"
    )

    # Populate on creation
    _populate_node(grp)

    return grp
