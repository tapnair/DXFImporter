"""
DXFImporter, a Fusion 360 add-in
================================
DXF Importer is a Fusion 360 add-in for the bulk import of DXF Files.

:copyright: (c) 2020 by Patrick Rainsberry.
:license: Apache 2.0, see LICENSE for more details.

DXFImporter leverages the ezdxf library.
Copyright (C) 2011-2020, Manfred Moitzi
License: MIT License


Notice:
-------

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
import adsk.core
import adsk.fusion

from enum import Enum

from ..apper import apper
from .. import config

DxfToFusionUnits = {
    1: "in",
    2: "ft",
    4: "mm",
    5: "cm",
    6: "m",
}

AllDxfUnits = {
    0: "Unitless",
    1: "Inches",
    2: "Feet",
    3: "Miles",
    4: "Millimeters",
    5: "Centimeters",
    6: "Meters",
    7: "Kilometers",
    8: "Microinches",
    9: "Mils",
    10: "Yards",
    11: "Angstroms",
    12: "Nanometers",
    13: "Microns",
    14: "Decimeters",
    15: "Decameters",
    16: "Hectometers",
    17: "Gigameters",
    18: "Astronomical units",
    19: "Light years",
    20: "Parsecs",
    21: "US Survey Feet",
    22: "US Survey Inch",
    23: "US Survey Yard",
    24: "US Survey Mile",
}


def create_sketch_text(sketch: adsk.fusion.Sketch, dxf_text_entity, font_selection, doc_units):
    ao = apper.AppObjects()
    dxf_height = dxf_text_entity.dxf.height
    height = ao.units_manager.convert(dxf_height, doc_units, ao.units_manager.internalUnits)
    (align, p1, p2) = dxf_text_entity.get_pos()
    x = p1[0]
    y = p1[1]
    # ao.ui.messageBox('Align: ' + align)

    dxf_point = adsk.core.Point3D.create(x, y, 0.0)

    # If sketch is created on model face, need to do some transform gymnastics
    point = sketch.modelToSketchSpace(dxf_point)
    point.z = 0.0

    # Read text from DXF entity
    text = dxf_text_entity.dxf.text

    # Get sketch texts
    sketch_texts = sketch.sketchTexts

    # Create sketch text input
    sketch_text_input = sketch_texts.createInput(text, height, point)

    # Set sketch text style
    # TODO - need to understand possible DXF values and map to fusion values.
    # sketch_text_input.textStyle = adsk.fusion.TextStyles.TextStyleBold

    # Set sketch text rotation
    sketch_text_input.angle = dxf_text_entity.dxf.rotation

    # Set sketch text rotation
    sketch_text_input.fontName = font_selection

    # Create sketch text
    sketch_texts.add(sketch_text_input)


@apper.lib_import(config.app_path)
def import_dxf_text(file_name, sketch, font_selection, face):
    import ezdxf
    from ezdxf.entities.text import Text
    doc = ezdxf.readfile(file_name)
    msp = doc.modelspace()

    dxf_units = doc.header.get('$INSUNITS', None)
    if dxf_units is None:
        app = adsk.core.Application.get()
        doc_units = app.activeProduct.unitsManager.defaultLengthUnits
        app.userInterface.messageBox(
            f'The file: {file_name} did not specify units.  '
            f'Default documents units ({doc_units}) are being assumed for text import.  '
            f'This will likely cause scaling errors with your text and will need to be corrected.'
        )

    else:
        doc_units = DxfToFusionUnits.get(dxf_units, None)

        if doc_units is None:
            app = adsk.core.Application.get()
            doc_units = app.activeProduct.unitsManager.defaultLengthUnits

            unsupported_units = AllDxfUnits.get(dxf_units, None)
            if unsupported_units is not None:
                app.userInterface.messageBox(
                    f'The file: {file_name} specifies unsupported units: ({unsupported_units}).  '
                    f'Default documents units ({doc_units}) are being assumed for text import.  '
                    f'This will likely cause scaling errors with your text and will need to be corrected.'
                )
            else:
                app.userInterface.messageBox(
                    f'The file: {file_name} specifies invalid units.  '
                    f'Default documents units ({doc_units}) are being assumed for text import.  '
                    f'This will likely cause scaling errors with your text and will need to be corrected.'
                )

    # entity query for all TEXT entities in model space
    dxf_text_entity: Text
    for dxf_text_entity in msp.query('TEXT'):
        # DEBUG
        # ao.ui.messageBox('Text: ' + dxf_text_entity.dxf.text)
        # ao.ui.messageBox('Style: ' + dxf_text_entity.dxf.style)
        # ao.ui.messageBox('Rotation: ' + str(dxf_text_entity.dxf.rotation))

        if isinstance(dxf_text_entity, Text):
            create_sketch_text(sketch, dxf_text_entity, font_selection, doc_units)
