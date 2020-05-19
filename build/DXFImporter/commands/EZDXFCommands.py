
#  """
#  :copyright: (c) 2020 by Patrick Rainsberry
#  EZDXFCommands.py
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

import adsk.core
import adsk.fusion
import traceback

import apper
from apper import AppObjects
import ezdxf


def create_sketch_text(sketch: adsk.fusion.Sketch, dxf_text_entity, font_selection):
    ao = AppObjects()
    dxf_height = dxf_text_entity.dxf.height
    height = ao.units_manager.convert(dxf_height, ao.units_manager.defaultLengthUnits, ao.units_manager.internalUnits)
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


def import_dxf_text(file_name, sketch, font_selection, face):
    doc = ezdxf.readfile(file_name)
    msp = doc.modelspace()

    # entity query for all TEXT entities in modelspace
    for dxf_text_entity in msp.query('TEXT'):

        # DEBUG
        # ao.ui.messageBox('Text: ' + dxf_text_entity.dxf.text)
        # ao.ui.messageBox('Style: ' + dxf_text_entity.dxf.style)
        # ao.ui.messageBox('Rotation: ' + str(dxf_text_entity.dxf.rotation))

        create_sketch_text(sketch, dxf_text_entity, font_selection)
