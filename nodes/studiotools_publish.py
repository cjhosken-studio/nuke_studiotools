import nuke
import nukescripts
import yaml

from utils import rgba
from utils.versions import *

def create_studiotools_publish_node():
    grp = nuke.nodes.Group(name="StudioTools Publish")
    
    with grp:
        input = nuke.nodes.Input(name="Input")
        write = nuke.nodes.Write(name="Write")
        export = nuke.nodes.GeoExport(name="USDExport")
        
        export["file_type"].setValue("usd")
        export["usd_file_format"].setValue("Crate")
        
        write["raw"].setValue(True)
        write["create_directories"].setValue(True)
        write["file_type"].setValue("exr")
        write["compression"].setValue("none")
        
        write.setInput(0, input)
        export.setInput(0, input)
        
        output = nuke.nodes.Output(name="Output")
        output.setInput(0, input)
        
        for n in nuke.allNodes():
            n.setSelected(False)

    grp.addKnob(nuke.Tab_Knob("StudioTools"))
    
    asset_knob = nuke.String_Knob("asset_name", "Asset Name")
    asset_knob.setValue("asset")
    grp.addKnob(asset_knob)

    version_knob = nuke.String_Knob("next_version", "")
    version_knob.clearFlag(nuke.STARTLINE)  # <-- same row
    version_knob.setEnabled(False)
    version_knob.setValue(get_next_version("asset"))
    grp.addKnob(version_knob)

    grp.addKnob(nuke.Text_Knob("divider", ""))
    
    asset_type_knob = nuke.Enumeration_Knob(
        "asset_type",
        "Asset Type",
        ["usd", "images"]
    )
    grp.addKnob(asset_type_knob)
    
    # Render mode
    mode_knob = nuke.Enumeration_Knob(
        "frame_mode",
        "Frames",
        ["Range", "Static"]
    )
    grp.addKnob(mode_knob)
    mode_knob.setValue("Range")

    # Frame range
    first_knob = nuke.Int_Knob("first_frame", "Frame Range")
    last_knob = nuke.Int_Knob("last_frame", "")
    grp.addKnob(first_knob)
    last_knob.clearFlag(nuke.STARTLINE)  # <-- same row
    grp.addKnob(last_knob)

    # Static frame
    static_knob = nuke.Int_Knob("static_frame", "Frame")
    grp.addKnob(static_knob)
    
    root = nuke.root()
    grp["first_frame"].setValue(int(root.firstFrame()))
    grp["last_frame"].setValue(int(root.lastFrame()))
    grp["static_frame"].setValue(int(nuke.frame()))
    grp["static_frame"].setVisible(False)
    
    publish_knob = nuke.PyScript_Knob("publish", "Publish")
    publish_knob.setFlag(nuke.STARTLINE)
    publish_knob.setCommand("studiotools_asset_publish(nuke.thisNode())")
    grp.addKnob(publish_knob)

    grp['knobChanged'].setValue("studiotools_publish_knob_changed()")

    grp["tile_color"].setValue(rgba(50, 50, 160))
    grp["note_font"].setValue("rounded")
    
    return grp

def studiotools_publish_knob_changed():
    node = nuke.thisNode()
    knob = nuke.thisKnob()
    
    if not knob:
        return

    if knob.name() == "frame_mode":
        is_static = node["frame_mode"].value() == "Static"

        node["first_frame"].setVisible(not is_static)
        node["last_frame"].setVisible(not is_static)
        node["static_frame"].setVisible(is_static)
    
    if knob.name() == "asset_name":
        asset_name = node["asset_name"].value().strip()
        
        next_version = get_next_version(asset_name)
        node["next_version"].setValue(next_version)
        
def get_next_version(asset_name):
    if not asset_name:
        return "v001"
        
    asset_root = get_asset_root_from_name(asset_name)
    current_version = version_string_to_int(os.path.basename(nuke.root().name()).replace("scene_", "").replace(".nk", ""))
        
    if not asset_root:
        return "v001"

    next_version = get_next_version_from_asset_root(asset_root)
    
    real_version = max(version_string_to_int(next_version), current_version)

    return version_int_to_string(real_version)
        
def get_publish_frames(node):
    if node["frame_mode"].value() == "Static":
        frame = int(node["static_frame"].value())
        return frame, frame
    else:
        return (
            int(node["first_frame"].value()),
            int(node["last_frame"].value())
        )
        
def studiotools_asset_publish(node):
    current = nuke.root().name()
    name = node['asset_name'].value()
    version = node["next_version"].value()
    asset_type = node["asset_type"].value()
    
    root = os.path.dirname(get_asset_root_from_name(name))
    versions_dir = os.path.join(root, "versions")
    
    version_root = os.path.join(versions_dir, f"{name}_{version}")
    os.makedirs(version_root, exist_ok=True)
    
    first, last = get_publish_frames(node)
    
    if asset_type == "usd":
        full_path = os.path.join(version_root, f"{name}_{version}.usd").replace("\\", "/")
        export = node.node("USDExport")
        export["file"].setValue(full_path)
        
        nuke.execute(export, first, last)
        
    elif asset_type == "images":
        full_path = os.path.join(version_root, "images", f"{name}_{version}.####.exr").replace("\\", "/")
        write = node.node("Write")
        
        write["file"].setValue(full_path)
        
        write["first"].setValue(first)
        write["last"].setValue(last)
        
        nuke.execute(write, first, last)
        
    metadata = os.path.join(version_root, "metadata.yaml")
        
    item_data = {
        "root": full_path,
        "version": version_string_to_int(version),
        "author": current,
        "type": asset_type,
    }

    with open(metadata, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            item_data,
            f,
            sort_keys=False,
            default_flow_style=False
        )    
    
    nuke.scriptSave()  
    nuke.scriptSaveAs(os.path.join(os.path.dirname(current), f"scene_{version_int_to_string(version_string_to_int(version) + 1)}.nk"))  
    
    node["next_version"].setValue(get_next_version(name))
    