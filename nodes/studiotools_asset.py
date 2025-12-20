import nuke
import os
import yaml

from utils.versions import strip_version_path, update_version_enum
from utils.io import find_frame_range
from utils import rgba

def create_studiotools_asset_node():
    grp = nuke.nodes.Group(name="StudioTools Asset")
    
    with grp:
        read = nuke.nodes.Read(name="ImageRead")
        
        read["raw"].setValue(1)
        
        geo = nuke.nodes.GeoImport(name="USDGeometry")
        
        switch = nuke.nodes.Switch(name="AssetSwitch")
        switch.setInput(0, read)
        switch.setInput(1, geo)
        
        output = nuke.nodes.Output(name="Output")
        output.setInput(0, switch)
        
        for n in nuke.allNodes():
            n.setSelected(False)
            
    path_knob = nuke.File_Knob("asset_path", "Asset Path")
    
    version_knob = nuke.Enumeration_Knob(
        "asset_version",
        "Version",
        []
    )
    
    reload_knob = nuke.PyScript_Knob("reload", "Reload")

    grp.addKnob(path_knob)
    grp.addKnob(version_knob)
    grp.addKnob(reload_knob)
    
    reload_knob.setCommand("studiotools_asset_reload(nuke.thisNode())")
    
    grp['knobChanged'].setValue("studiotools_asset_knob_changed()")

    grp["tile_color"].setValue(rgba(50, 50, 160))
    grp["note_font"].setValue("rounded")
    
    return grp
    
def set_studiotools_asset_paths(node):
    asset_name = os.path.basename(node["asset_path"].value())
    base_path = os.path.dirname(node["asset_path"].value())
    
    label = node['asset_version'].value()
    
    if "Latest" in label:
        version = ""
    
    if label == "Published":
        asset_root = os.path.join(base_path, "published", asset_name)
    else:
        if "Latest" in label:
            version = label.replace("Latest (", "").replace(")", "")
        else:
            version = label
            
        asset_root = os.path.join(base_path, "versions", f"{asset_name}_{version}")
        
    print(asset_root)
        
    if not os.path.exists(asset_root):
        return
            
    metadata_path = os.path.join(asset_root, "metadata.yaml")
    if not os.path.isfile(metadata_path):
        return
    
    with open(metadata_path, "r") as f:
        data = yaml.safe_load(f)
        
    if not data:
        return
    
    root = ""
    asset_type = ""
    
    if "root" in data:
        root = data["root"]
        
    if "type" in data:
        asset_type = data["type"]
    
    read = node.node("ImageRead")
    geo = node.node("USDGeometry")
    switch = node.node("AssetSwitch")
        
    print(asset_type)
        
    if asset_type == "usd":
        print("TESTING!!!")
        print(root)
        
        if root.endswith(".usdnc"):
            nuke.message(f"StudioTools Asset Error:\n\n The current asset is a .usdnc from Houdini non-commercial. Please update to a Commercial Houdini license to import into Nuke.")
        
        geo["file"].setValue(root.replace("\\", "/"))
        switch["which"].setValue(1)
        
    elif asset_type == "images":
        first, last = find_frame_range(root)
        
        read["file"].setValue(os.path.join(root, "render.####.exr").replace("\\", "/"))
        read["first"].setValue(first)
        read["last"].setValue(last)
        
        read["origfirst"].setValue(first)
        read["origlast"].setValue(last)
        
        switch["which"].setValue(0)
    
def studiotools_asset_reload(node):
    path = node['asset_path'].value()
    
    asset_root = strip_version_path(path)
    
    if node["asset_path"].value() != asset_root:
        node["asset_path"].setValue(asset_root)
        
    update_version_enum(node)
    
    set_studiotools_asset_paths(node)

        
def studiotools_asset_knob_changed():
    node = nuke.thisNode()
    knob = nuke.thisKnob()
    
    if knob.name() in {"asset_path", "asset_version"}:
        studiotools_asset_reload(node)