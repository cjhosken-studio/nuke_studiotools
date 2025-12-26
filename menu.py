import nuke
from nodes.studiotools_asset import create_studiotools_asset_node
from nodes.studiotools_publish import create_studiotools_publish_node

nuke.menu("Nodes").addMenu(
    "StudioTools",
    icon="../../public/logo.png"
)

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

import nukescripts
nukescripts.update_plugin_menu("All plugins")