
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

import os
import sys
from importlib import reload

import adsk.core
import traceback


def remove_from_path(name):
    if name in sys.path:
        sys.path.remove(name)
        remove_from_path(name)


app_path = os.path.dirname(__file__)

remove_from_path(app_path)
remove_from_path(os.path.join(app_path, 'apper'))
remove_from_path(os.path.join(app_path, 'lib'))

if sys.modules.get('apper', False):
    del sys.modules['apper']

sys.path.insert(0, app_path)
sys.path.insert(0, os.path.join(app_path, 'apper'))
sys.path.insert(0, os.path.join(app_path, 'lib'))

try:
    import config
    import apper

    # Basic Fusion 360 Command Base samples
    from .commands.DXFImportCommand import DXFImportCommand, CloseGapsCommand

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
    sys.path.pop(0)
    sys.path.pop(0)
    sys.path.pop(0)
