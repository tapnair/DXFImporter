
#  """
#  :copyright: (c) 2020 by Patrick Rainsberry
#  DXFImporter.py
#  =========================================================
#  A Component of DXFImporter, a Fusion 360 add-in
#
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
#  """
import sys

import adsk.core
import traceback

from.startup import setup_app, cleanup_app, get_app_path
setup_app(__file__)


try:
    import config
    import apper
    from .commands.DXFImportCommand import DXFImportCommand, CloseGapsCommand
    # TODO rethink when path is cleaned up

    my_addin = apper.FusionApp(config.app_name, config.company_name, False)
    my_addin.root_path = get_app_path(__file__)

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

    # General command showing inputs and user interaction
    my_addin.add_command(
        'Close Sketch Gaps',
        CloseGapsCommand,
        {
            'cmd_description': 'Close any gaps within tolerance in a Sketch',
            'cmd_id': 'dxf_gap_cmd',
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
    cleanup_app(__file__)
