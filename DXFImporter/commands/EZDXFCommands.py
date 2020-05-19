
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
