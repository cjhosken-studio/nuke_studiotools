import os
import re

try:
    import nuke
    IN_NUKE = True
except ImportError:
    IN_NUKE = False

# --- Pipeline helpers ---

def get_task_context():
    """Returns pipeline context from env variables set by Studio Tools launcher."""
    return {
        "project_path": os.environ.get("ST_PROJECT"),
        "task_path":    os.environ.get("ST_CWD"),
        "task_name":    os.environ.get("ST_TASK"),
        "task_area":    os.environ.get("ST_TASKAREA"),
    }


def _scan_published_assets(task_path):
    """Returns list of (display_label, absolute_path) for all published USD assets
    reachable from the project sandbox (two levels up from task_path)."""
    sandbox_dir = os.path.dirname(os.path.dirname(task_path))
    assets = []
    if os.path.isdir(sandbox_dir):
        for root, dirs, files in os.walk(sandbox_dir, followlinks=True):
            if os.path.basename(root) == "published":
                for f in sorted(files):
                    if f.lower().endswith((".usd", ".usda", ".usdc")):
                        full_path = os.path.abspath(os.path.join(root, f))
                        rel_path  = os.path.relpath(full_path, sandbox_dir)
                        assets.append((rel_path, full_path))
    return sorted(assets, key=lambda x: x[0])


# --- Studio Tools menu actions ---

def load_usd_asset():
    """Presents a panel for selecting a published USD asset and reads it into a
    ReadGeo node (or a generic Read if ReadGeo is unavailable)."""
    if not IN_NUKE:
        print("[Studio Tools] Not running inside Nuke.")
        return

    ctx = get_task_context()
    task_path = ctx["task_path"]
    if not task_path:
        nuke.message("Studio Tools: Pipeline context not set!\n\nST_CWD environment variable is missing.")
        return

    assets = _scan_published_assets(task_path)
    if not assets:
        nuke.message("No published USD assets found in the active project.")
        return

    labels = [a[0] for a in assets]
    paths  = [a[1] for a in assets]

    panel = nuke.Panel("Studio Tools | Load USD Asset")
    panel.addEnumerationPulldown("Asset", " ".join(labels))
    if panel.show():
        selected_label = panel.value("Asset")
        try:
            idx = labels.index(selected_label)
        except ValueError:
            return
        selected_path = paths[idx]
        _load_asset_path(selected_path)


def _load_asset_path(filepath):
    """Creates a ReadGeo (or Read) node pointing at the given USD file."""
    if not IN_NUKE:
        return
    try:
        # ReadGeo3 is preferred for USD in Nuke 13+; fall back to ReadGeo2 / Read
        node = None
        for node_class in ("ReadGeo3", "ReadGeo2", "ReadGeo"):
            try:
                node = nuke.createNode(node_class, inpanel=False)
                break
            except Exception:
                continue

        if node is None:
            nuke.message(f"Could not create a ReadGeo node. Please open:\n{filepath}")
            return

        node["file"].setValue(filepath)
        asset_name = os.path.splitext(os.path.basename(filepath))[0]
        node["name"].setValue(re.sub(r"[^a-zA-Z0-9_]", "_", asset_name))
        nuke.tprint(f"[Studio Tools] Loaded USD asset: {filepath}")
    except Exception as e:
        nuke.message(f"Failed to load USD asset:\n{e}")


def poll_web_connection():
    """Called periodically by Nuke's idle loop to check for load_usd commands
    queued by Studio Tools from the web UI."""
    task_path = os.environ.get("ST_CWD")
    if not task_path:
        return

    try:
        import urllib.request
        import urllib.parse
        import json

        url = (
            f"http://localhost:8000/api/sessions/poll"
            f"?appType=nuke&taskPath={urllib.parse.quote(task_path)}"
        )
        with urllib.request.urlopen(url, timeout=0.2) as response:
            res = json.loads(response.read().decode())
            for cmd in res.get("commands", []):
                if cmd.get("command") == "load_usd":
                    fp = cmd.get("argument", "")
                    if fp and os.path.exists(fp):
                        _load_asset_path(fp)
                        nuke.tprint(f"[Studio Tools] Web Connection: Loaded {fp}")
    except Exception:
        pass  # Silence — server may not be running


# --- Register the Studio Tools menu and custom nodes ---

if IN_NUKE:
    # ── Nuke menu bar ──────────────────────────────────────────────────────
    _menu = nuke.menu("Nuke").addMenu("Studio Tools")
    _menu.addCommand(
        "Load USD Asset...",
        load_usd_asset,
        tooltip="Select a published USD asset from the project and import it as a ReadGeo node."
    )
    _menu.addSeparator()

    # ST_Read / ST_Write shortcuts in menu bar
    _menu.addCommand(
        "Create ST_Read Node",
        "import ST_Read; ST_Read.create()",
        tooltip="Create a pipeline-aware Read node that browses project deliverables."
    )
    _menu.addCommand(
        "Create ST_Write Node",
        "import ST_Write; ST_Write.create()",
        tooltip="Create a pipeline-aware Write node with auto-versioned output paths."
    )

    _menu.addSeparator()
    _menu.addCommand(
        "Pipeline Context",
        lambda: nuke.message(
            "Studio Tools Pipeline Context\n\n"
            f"Task:      {os.environ.get('ST_TASK', '(not set)')}\n"
            f"Task Area: {os.environ.get('ST_TASKAREA', '(not set)')}\n"
            f"CWD:       {os.environ.get('ST_CWD', '(not set)')}\n"
            f"Project:   {os.environ.get('ST_PROJECT', '(not set)')}"
        ),
        tooltip="Show current pipeline context (task, task area, paths)."
    )

    # ── Nodes toolbar (Tab key / node search) ──────────────────────────────
    _nodes_menu = nuke.menu("Nodes").addMenu("Studio Tools")

    _nodes_menu.addCommand(
        "ST_Read",
        "import ST_Read; ST_Read.create()",
        tooltip=(
            "Pipeline Read — scans the project's published and versioned "
            "deliverables and lets you select a version from a dropdown."
        )
    )

    _nodes_menu.addCommand(
        "ST_Write",
        "import ST_Write; ST_Write.create()",
        tooltip=(
            "Pipeline Write — auto-constructs a versioned render output path "
            "under wip/nuke/renders/ and writes metadata on completion."
        )
    )

    # ── Idle callback for web connection ───────────────────────────────────
    nuke.addOnScriptLoad(lambda: None)  # ensure module is resident
    try:
        nuke.addIdleCallback(poll_web_connection)
        nuke.tprint("[Studio Tools] Web Connection active and listening for load actions...")
    except Exception as _e:
        nuke.tprint(f"[Studio Tools] Warning: Failed to register idle callback: {_e}")

