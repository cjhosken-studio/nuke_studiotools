import os
import sys
import re

try:
    import nuke
    IN_NUKE = True
except ImportError:
    IN_NUKE = False

if IN_NUKE:
    # 1. Add the nuke_studiotools plugin dir and its nodes/ subdir to sys.path
    #    so ST_Read / ST_Write modules are importable from knobChanged callbacks.
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _nodes_dir = os.path.join(_this_dir, "nodes")

    for _d in (_this_dir, _nodes_dir):
        if os.path.isdir(_d) and _d not in sys.path:
            sys.path.insert(0, _d)

    # Register nodes/ as a Nuke plugin path so node definitions are found
    if os.path.isdir(_nodes_dir):
        nuke.pluginAddPath(_nodes_dir)

    # 2. Load the user's /public/pipeline/nuke plugin tree (same logic as the
    #    existing /public/pipeline/nuke/init.py but driven by the ST_NUKE_PLUGIN_PATH
    #    env var so there's no hardcoded path)
    nuke_plugin_root = os.environ.get("ST_NUKE_PLUGIN_PATH", "")
    if nuke_plugin_root and os.path.isdir(nuke_plugin_root):
        for item in os.listdir(nuke_plugin_root):
            full_path = os.path.join(nuke_plugin_root, item)
            if os.path.isdir(full_path):
                nuke.pluginAddPath(full_path)
        nuke.tprint(f"[Studio Tools] Loaded Nuke pipeline plugins from: {nuke_plugin_root}")
    else:
        nuke.tprint("[Studio Tools] ST_NUKE_PLUGIN_PATH not set or not found — skipping pipeline plugin load.")
