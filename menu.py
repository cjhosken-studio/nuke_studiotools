import nuke
from nodes.studiotools_asset import create_studiotools_asset_node

nuke.menu("Nodes").addCommand(
    "StudioTools/StudioTools Asset",
    "create_studiotools_asset_node()",
    icon="Read.png"
)

nuke.menu("Nodes").addCommand(
    "StudioTools/StudioTools Publish",
    "create_studiotools_publish_node()",
    icon="Write.png"
)

nuke.menu("Nodes").addCommand(
    "StudioTools/StudioTools Publish 3D",
    "create_studiotools_publish_3D_node()",
    icon="Write.png"
)
