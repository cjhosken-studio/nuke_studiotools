import nuke
import sys
import os
import subprocess
import importlib

def install_package(package_name, import_name=None):
    if not import_name:
        import_name = package_name

    if importlib.util.find_spec(import_name):
        return

    app_exe = sys.executable
    python_exe = os.path.join(os.path.dirname(app_exe), "python")
    
    if sys.platform == "win32":
        python_exe += ".exe"
    
    cmd = [python_exe, "-m", "pip", "install", package_name]
    subprocess.check_call(cmd)

packages = [("numpy", "numpy"), ("PyYAML", "yaml")]

for p in packages:
    if len(p) > 1:
        install_package(p[0], p[1])
    else:
        install_package(p[0])

from nodes.studiotools_asset import (
    create_studiotools_asset_node,
    studiotools_asset_reload,
    studiotools_asset_knob_changed,
)

from nodes.studiotools_publish import (
    create_studiotools_publish_node,
    studiotools_publish_knob_changed,
    studiotools_asset_publish
)

nuke.pluginAddPath(os.path.join(os.path.dirname(__file__), "plugins", "mmColorTarget_v3.1"))