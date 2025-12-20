import nuke

from utils import rgba

def create_studiotools_publish_node():
    grp = nuke.nodes.Group(name="StudioTools Publish")
    
    with grp:
        input = nuke.nodes.Input(name="Input")
        write = nuke.nodes.Write(name="Write")
        export = nuke.nodes.GeoExport(name="USDExport")
        
        write.setInput(0, input)
        export.setInput(0, input)
        
        output = nuke.nodes.Output(name="Output")
        output.setInput(0, input)
        
        for n in nuke.allNodes():
            n.setSelected(False)

    grp['knobChanged'].setValue("studiotools_publish_knob_changed()")

    grp["tile_color"].setValue(rgba(50, 50, 160))
    grp["note_font"].setValue("rounded")
    
    return grp

def studiotools_publish_knob_changed():
    pass