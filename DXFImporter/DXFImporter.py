
import os
import sys
import adsk.core
import traceback

app_path = os.path.dirname(__file__)

sys.path.insert(0, app_path)
sys.path.insert(0, os.path.join(app_path, 'apper'))

try:
    import config
    import apper

    # Basic Fusion 360 Command Base samples
    from .commands.DXFImportCommand import DXFImportCommand

    my_addin = apper.FusionApp(config.app_name, config.company_name, False)

    # General command showing inputs and user interaction
    my_addin.add_command(
        'DXF Import',
        DXFImportCommand,
        {
            'cmd_description': 'Import multiple DXF Files',
            'cmd_id': 'dxf_import_cmd',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'DXF Import',
            'cmd_resources': 'command_icons',
            'command_visible': True,
            'command_promoted': True,
            # 'toolbar_tab_name': 'ToolsTab',
            # 'toolbar_tab_id': 'ToolsTab'

        }
    )

except:
    app = adsk.core.Application.get()
    ui = app.userInterface
    if ui:
        ui.messageBox('Initialization: {}'.format(traceback.format_exc()))

# Set to True to display various useful messages when debugging your app
debug = False


def run(context):
    my_addin.run_app()


def stop(context):
    my_addin.stop_app()
    sys.path.pop(0)
    sys.path.pop(0)
