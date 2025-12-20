import os
import re
import json
import nuke
    
VERSION_RE = re.compile(r"(.*?)(?:_v\d+)$")
    
def strip_version_path(path):
    path = os.path.normpath(path)
    base = os.path.basename(path)
    
    match = VERSION_RE.match(base)
    if not match:
        return path
    
    asset_name = match.group(1)
    versions_dir = os.path.dirname(path)
    
    asset_root = os.path.join(
        os.path.dirname(versions_dir),
        asset_name
    )
    
    return asset_root

def version_int_to_string(version_number):
    return f"v{version_number:03d}"

def version_string_to_int(version_string):
    return int(version_string.replace("v", ""))

def list_asset_versions(asset_root):
    versions_dir = os.path.join(os.path.dirname(asset_root),
        "versions"
    )
    
    print(versions_dir)
    
    if not os.path.isdir(versions_dir):
        return []
    
    asset_name = os.path.basename(asset_root)
    
    versions = []
    
    for entry in os.listdir(versions_dir):
        if re.match(rf"{asset_name}_v\d+", entry):
            versions.append(entry)
            
    return sorted(versions)        

def build_version_menu(asset_root):
    asset_name = os.path.basename(asset_root)
    
    versions = list_asset_versions(asset_root)
    if not versions:
        return []
    
    menu = []
    newest = versions[-1]
    
    if os.path.exists(os.path.join(os.path.dirname(asset_root), "published", asset_name)):
        label = "Published"
        menu.append(label)
            
    newest_label = f"Newest ({newest})"
    menu.append(newest_label)
    
    for v in versions:
        label = v.replace(asset_name + "_", "")
        menu.append(label)
        
    return menu

def update_version_enum(node):
    asset_root = node["asset_path"].value()
    
    menu = build_version_menu(asset_root)
    if not menu:
        return
    
    node["asset_version"].setValues(menu)