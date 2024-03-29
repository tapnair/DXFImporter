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
import json
import logging
import sys
import traceback
from importlib import reload

import adsk.core
import adsk.fusion

import os
from math import floor

from ..apper import apper
from .. import config
from . import EZDXFCommands


def validate_workspace(command: adsk.core.Command):
    command.isExecutedWhenPreEmpted = False
    ao = apper.AppObjects()
    if ao.product.productType != 'DesignProductType':
        solid_workspace = ao.ui.workspaces.itemById('FusionSolidEnvironment')
        solid_workspace.activate()
        ao.ui.commandDefinitions.itemById(command.parentCommandDefinition.id).execute()


# Extract file names of all dxf files in a directory
def get_dxf_files(file_names):
    dxf_files = []

    for filename in file_names:

        if filename.endswith(".dxf") or filename.endswith(".DXF"):
            base_name = os.path.basename(filename)
            dxf_file = {
                'full_path': filename,
                'name': base_name[:-4],
                'base_name': base_name
            }
            dxf_files.append(dxf_file)
        else:
            continue

    return dxf_files


def get_delta_vector(fusion_object) -> adsk.core.Vector3D:
    max_point = fusion_object.boundingBox.maxPoint
    min_point = fusion_object.boundingBox.minPoint
    delta_vector = adsk.core.Vector3D.create(max_point.x - min_point.x,
                                             max_point.y - min_point.y,
                                             max_point.z - min_point.z)

    return delta_vector


def bounding_box_volume(fusion_object):
    max_point = fusion_object.boundingBox.maxPoint
    min_point = fusion_object.boundingBox.minPoint
    bb_volume = (max_point.x - min_point.x) * (max_point.y - min_point.y) * (max_point.z - min_point.z)
    return bb_volume


# Returns the magnitude of the bounding box in the specified direction
def get_bb_in_direction(fusion_object, direction_vector):
    delta_vector = get_delta_vector(fusion_object)

    # Get bounding box delta in specified direction
    delta = delta_vector.dotProduct(direction_vector)
    return delta


# Transforms an occurrence along a specified vector by a specified amount
def transform_along_vector(occurrence, direction_vector, magnitude):
    # Create a vector for the translation
    vector = direction_vector.copy()
    vector.scaleBy(magnitude)
    transform = transform_from_vector(occurrence, vector)
    # Transform Component
    occurrence.transform = transform


def move_to_origin(occurrence: adsk.fusion.Occurrence):
    vector = occurrence.boundingBox.minPoint.asVector()
    vector.scaleBy(-1.0)
    transform = transform_from_vector(occurrence, vector)
    # Transform Component
    occurrence.transform = transform


def move_sketch_by_transform(sketch, transform):
    all_sketch_entities = adsk.core.ObjectCollection.create()

    if sketch.sketchCurves.count > 0:
        for entity in sketch.sketchCurves:
            all_sketch_entities.add(entity)
    if sketch.sketchTexts.count > 0:
        for text_entity in sketch.sketchTexts:
            all_sketch_entities.add(text_entity)

    sketch.move(all_sketch_entities, transform)


def move_sketch_to_origin(sketch: adsk.fusion.Sketch):
    vector = sketch.boundingBox.minPoint.asVector()
    vector.scaleBy(-1.0)
    new_transform = adsk.core.Matrix3D.create()
    new_transform.translation = vector

    move_sketch_by_transform(sketch, new_transform)

    return new_transform


def transform_from_vector(occurrence, vector):
    # Create a transform to do move
    old_transform = adsk.core.Matrix3D.cast(occurrence.transform)
    new_transform = adsk.core.Matrix3D.create()
    new_transform.translation = vector
    old_transform.transformBy(new_transform)
    return old_transform


def create_extrude(profile: adsk.fusion.Profile, component: adsk.fusion.Component, distance, operation, success):
    extrudes = component.features.extrudeFeatures
    try:
        ext_input = extrudes.createInput(profile, operation)
        distance_input = adsk.core.ValueInput.createByReal(distance)
        ext_input.setDistanceExtent(False, distance_input)
        extrude_feature: adsk.fusion.ExtrudeFeature = extrudes.add(ext_input)
        face = extrude_feature.endFaces.item(0)
        return face

    except:
        return success


def extrude_largest_profile(sketch: adsk.fusion.Sketch, component: adsk.fusion.Component, distance: float):
    if sketch.profiles.count == 0:
        return

    else:
        the_profile = sketch.profiles.item(0)
        operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        success = False

        success = create_extrude(the_profile, component, distance, operation, success)

        if sketch.profiles.count > 1:
            # the_profile = adsk.core.ObjectCollection.create()
            for i in range(1, sketch.profiles.count):
                if success:
                    operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
                success = create_extrude(sketch.profiles.item(i), component, distance, operation, success)


# extrude the first profile with the largest number of holes
def extrude_profile_with_most_loops(sketch: adsk.fusion.Sketch, component: adsk.fusion.Component, distance: float):
    if sketch.profiles.count == 0:
        return
    else:
        # start with the first profile
        the_profile = sketch.profiles.item(0)
        the_profile_loop_count = the_profile.profileLoops.count
        # find the profile with the most loops
        if sketch.profiles.count > 1:
            for i in range(1, sketch.profiles.count):
                next_profile = sketch.profiles.item(i)
                next_profile_loop_count = next_profile.profileLoops.count
                if next_profile_loop_count > the_profile_loop_count:
                    the_profile = next_profile
                    the_profile_loop_count = next_profile_loop_count
        operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        success = False
        face = create_extrude(the_profile, component, distance, operation, success)

        return face


# def clean_dxf(dxf_file, flatten, explode):
#     ao = apper.AppObjects()
#     file_name = dxf_file['full_path']
#
#     doc = ezdxf.readfile(file_name)
#
#     if explode:
#         blocks = doc.blocks
#         model_space = doc.modelspace()
#
#         for block in blocks:
#             entities = block.query('*')
#             for entity in entities:
#                 block.unlink_entity(entity)
#                 model_space.add_entity(entity)
#     if flatten:
#
#         if len(doc.layers) > 1:
#             for layer in doc.layers:
#                 doc.layers.remove(layer.dxf.name)
#             doc.layers.new("Merged Layers")
#             for entity in doc.entities:
#                 entity.dxf.layer = "Merged Layers"
#
#
#     ao.ui.messageBox("".join([layer.dxf.name for layer in doc.layers]))
#     head, tail = os.path.split(file_name)
#     new_file_name = os.path.join(head, 'clean_' + tail)
#
#     doc.saveas(new_file_name)


def get_materials():
    ao = apper.AppObjects()
    material_list = []
    for material in ao.design.materials:
        material_list.append(
            {
                "material": material,
                "name": material.name,
                "id": material.id,
            }
        )

    return material_list


def process_dxf_files(dxf_files, input_values, material, logger: logging.Logger):
    ao = apper.AppObjects()
    # Start a time line group
    start_index = apper.start_group()

    y_magnitude_attribute = ao.design.attributes.itemByName("DXFer", "y_magnitude")
    x_magnitude_attribute = ao.design.attributes.itemByName("DXFer", "x_magnitude")
    row_count_attribute = ao.design.attributes.itemByName("DXFer", "row_count")
    y_row_max_attribute = ao.design.attributes.itemByName("DXFer", "y_row_max")

    if y_magnitude_attribute is None:
        y_magnitude = 0.0
    else:
        y_magnitude = float(y_magnitude_attribute.value)

    if x_magnitude_attribute is None:
        x_magnitude = 0.0
    else:
        x_magnitude = float(x_magnitude_attribute.value)

    if row_count_attribute is None:
        row_count = 0
    else:
        row_count = int(row_count_attribute.value)

    if y_row_max_attribute is None:
        y_row_max = 0.0
    else:
        y_row_max = float(y_row_max_attribute.value)

    # Define spacing and directions
    x_vector = adsk.core.Vector3D.create(1.0, 0.0, 0.0)
    y_vector = adsk.core.Vector3D.create(0.0, 1.0, 0.0)

    # Iterate all dxf files and create components
    for dxf_file in dxf_files:
        # Create new component for this DXF file
        occurrence = apper.create_component(ao.root_comp, dxf_file['name'])
        sketches = apper.import_dxf(
            dxf_file['full_path'],
            occurrence.component,
            occurrence.component.xYConstructionPlane,
            input_values['single_sketch']
        )
        logger.info(f"Imported DXF File: {dxf_file['name']}")
        x_delta = 0
        y_delta = 0
        face = False
        sketch_transform = None
        extrude_sketch_transform = None
        for sketch in sketches:

            if input_values['close_sketches']:
                tolerance = input_values['tolerance_input']
                close_sketch_gaps(sketch, tolerance, logger)

            if input_values['reset_option_input']:
                sketch_transform = move_sketch_to_origin(sketch)

            x_delta_check = get_bb_in_direction(sketch, x_vector)
            if x_delta_check > x_delta:
                x_delta = x_delta_check
            y_delta_check = get_bb_in_direction(sketch, y_vector)
            if y_delta_check > y_delta:
                y_delta = y_delta_check

            if input_values['extrude_option_input']:
                # extrude_largest_profile(sketch, occurrence.component, input_values['distance'])
                this_face = extrude_profile_with_most_loops(sketch, occurrence.component, input_values['distance'])
                if this_face:
                    face = this_face
                    extrude_sketch_transform = sketch_transform
                if input_values['keep_sketches_shown']:
                    sketch.isLightBulbOn = True

        if input_values['import_text']:
            # Alternative to create sketch on extrude cap face, having transform issues.
            if face:
                text_sketch = occurrence.component.sketches.add(face)
            else:
                xy_plane = occurrence.component.xYConstructionPlane
                text_sketch = occurrence.component.sketches.add(xy_plane)

            text_sketch.name = 'TEXT'

            # Import text with EZDXF Library
            font_selection = input_values['font_selection']
            EZDXFCommands.import_dxf_text(dxf_file['full_path'], text_sketch, font_selection, logger)

            if text_sketch.sketchTexts.count == 0:
                text_sketch.deleteMe()
            elif input_values['reset_option_input']:
                if extrude_sketch_transform is not None:
                    move_sketch_by_transform(text_sketch, extrude_sketch_transform)
                elif sketch_transform is not None:
                    move_sketch_by_transform(text_sketch, sketch_transform)

            # EZDXFCommands.import_dxf_text(dxf_file['full_path'], occurrence.component, font_selection)

        if not input_values['reset_option_input']:
            move_to_origin(occurrence)
        # Move component in specified direction
        transform_along_vector(occurrence, x_vector, x_magnitude)
        transform_along_vector(occurrence, y_vector, y_magnitude)

        # Update document and capture position of new component
        adsk.doEvents()
        if ao.design.snapshots.hasPendingSnapshot:
            ao.design.snapshots.add()

        # Increment magnitude by desired component size and spacing
        x_magnitude += input_values['spacing']
        x_magnitude += x_delta
        row_count += 1

        if y_delta > y_row_max:
            y_row_max = y_delta

        # Move to next row
        if row_count >= input_values['rows']:
            y_magnitude += input_values['spacing']
            y_magnitude += y_row_max
            y_row_max = 0.0
            x_magnitude = 0.0
            row_count = 0

        if material is not None:
            occurrence.component.material = material

    ao.design.attributes.add("DXFer", "y_magnitude", str(y_magnitude))
    ao.design.attributes.add("DXFer", "x_magnitude", str(x_magnitude))
    ao.design.attributes.add("DXFer", "row_count", str(row_count))
    ao.design.attributes.add("DXFer", "y_row_max", str(y_row_max))

    # Close time line group
    apper.end_group(start_index)


def save_settings(inputs: adsk.core.CommandInputs, fusion_app: apper.FusionApp):
    new_prefs = {
        "SHOW_POPUP": inputs.itemById('show_popup').value,
        "DEFAULT_PART_SPACING": inputs.itemById('spacing').expression,
        "DEFAULT_PARTS_PER_ROW": inputs.itemById('rows').value,
        "RESET_ORIGINS": inputs.itemById('reset_option_input').value,
        "SINGLE_SKETCH": inputs.itemById('single_sketch').value,
        "EXTRUDE_PROFILES": inputs.itemById('extrude_option_input').value,
        "DEFAULT_THICKNESS": inputs.itemById('distance').expression,
        "APPLY_MATERIAL": inputs.itemById('apply_material_input').value,
        "DEFAULT_MATERIAL": inputs.itemById('material_selection').selectedItem.name,
        "IMPORT_TEXT": inputs.itemById('import_text').value,
        "DEFAULT_FONT": inputs.itemById('font_selection').selectedItem.name,
        "CLOSE_SKETCH_GAPS": inputs.itemById('close_sketches').value,
        "DEFAULT_GAP_TOL": inputs.itemById('tolerance_input').expression,
        "KEEP_SKETCHES_SHOWN": inputs.itemById('keep_sketches_shown').value
    }
    fusion_app.save_preferences("DEFAULT", new_prefs, False)


def close_sketch_gaps(sketch: adsk.fusion.Sketch, tolerance, logger: logging.Logger):
    ao = apper.AppObjects()

    # factor = int(floor(1/tolerance))

    bounding_box = sketch.boundingBox
    min_x = bounding_box.minPoint.x
    min_y = bounding_box.minPoint.y
    max_x = bounding_box.maxPoint.x
    max_y = bounding_box.maxPoint.y

    factor = int(floor(2000 / ((max_x - min_x) + (max_y - min_y))))

    x_range = int(floor(factor * (max_x - min_x)))
    y_range = int(floor(factor * (max_y - min_y)))
    trans_x = round(0 - min_x, 6)
    trans_y = round(0 - min_y, 6)

    # Debug
    # str_comp = str(x_range) + ', ' + str(y_range)
    # ao.ui.messageBox(str_comp)
    #
    # str_comp = str(trans_x) + ', ' + str(trans_y)
    # ao.ui.messageBox(str_comp)

    grid = [[[] for i in range(x_range + 2)] for j in range(y_range + 2)]
    str_list = []
    constrained_points: int = 0
    sketch_point: adsk.fusion.SketchPoint
    for sketch_point in sketch.sketchPoints:
        if sketch_point.geometry.z == 0:
            if bounding_box.contains(sketch_point.worldGeometry):
                x_pos: int = int(floor(factor * (trans_x + sketch_point.worldGeometry.x)))
                y_pos: int = int(floor(factor * (trans_y + sketch_point.worldGeometry.y)))
                point_check_list = grid[y_pos][x_pos]
                point_merged = False
                for point_check in point_check_list:
                    if isinstance(point_check, adsk.fusion.SketchPoint):
                        if sketch_point.worldGeometry.distanceTo(point_check.worldGeometry) <= tolerance:
                            try:
                                sketch.geometricConstraints.addCoincident(sketch_point, point_check)
                                constrained_points += 1
                                point_merged = True

                            except:
                                logger.error(f"Constrain Points Error: {traceback.format_exc(2)}")

                if not point_merged:
                    grid[y_pos][x_pos].append(sketch_point)
                    grid[y_pos + 1][x_pos].append(sketch_point)
                    grid[y_pos - 1][x_pos].append(sketch_point)
                    grid[y_pos][x_pos + 1].append(sketch_point)
                    grid[y_pos + 1][x_pos + 1].append(sketch_point)
                    grid[y_pos - 1][x_pos + 1].append(sketch_point)
                    grid[y_pos][x_pos - 1].append(sketch_point)
                    grid[y_pos + 1][x_pos - 1].append(sketch_point)
                    grid[y_pos - 1][x_pos - 1].append(sketch_point)

                str_list.append(str(x_pos) + ', ' + str(y_pos))

        # ao.ui.messageBox(str(str_list))
    # if merged_points > 0:
    #     ao.ui.messageBox(f"Number of merged points: {merged_points}")
    if constrained_points > 0:
        logger.info(f"There were {constrained_points} gaps closed in {sketch.parentComponent.name} - {sketch.name}")


def get_tooltips():
    file_name = os.path.join(config.app_path, 'commands', 'resources', 'tooltips.json')
    tooltips_dict = {}
    if os.path.exists(file_name):
        with open(file_name) as f:
            try:
                tooltips_dict = json.load(f)
            except:
                pass

    return tooltips_dict


def set_tool_tips(command_inputs: adsk.core.CommandInputs, tool_tips_dict):
    command_input: adsk.core.CommandInput
    for i in range(command_inputs.count):
        command_input = command_inputs.item(i)
        tip_text = tool_tips_dict.get(command_input.id, False)
        if tip_text:
            command_input.tooltipDescription = tip_text
            # ao = apper.AppObjects()
            # ao.ui.messageBox(f"{command_input.id}  -  {command_input.tooltipDescription}")


class DXFImportCommand(apper.Fusion360CommandBase):
    def __init__(self, name: str, options: dict):
        super().__init__(name, options)
        self.file_names = []
        self.material_list = []
        self.font_list = []
        self.tooltips = get_tooltips()

        if not bool(self.fusion_app.preferences):
            file_name = os.path.join(config.app_path, "default_preferences.json")
            default_preferences = self.fusion_app.read_json_file(file_name)
            self.fusion_app.initialize_preferences(default_preferences)

        self.fusion_app.enable_logging()

    def on_execute(self, command, command_inputs: adsk.core.CommandInputs, args, input_values):
        if len(self.file_names) == 0:
            return

        if input_values["save_settings"]:
            save_settings(command_inputs, self.fusion_app)

        apply_material = input_values['apply_material_input']
        material = None
        drop_down_input = command_inputs.itemById('material_selection')
        if apply_material and (drop_down_input.listItems.count > 0):
            material_index = drop_down_input.selectedItem.index
            material = self.material_list[material_index]['material']

        dxf_files = get_dxf_files(self.file_names)
        process_dxf_files(dxf_files, input_values, material, self.fusion_app.logger)

    def on_create(self, command, command_inputs: adsk.core.CommandInputs):
        validate_workspace(command)
        command.helpFile = os.path.join(config.app_path, "HelpFile.html")
        self.file_names = []
        self.material_list = get_materials()
        ao = apper.AppObjects()

        # Gets default values from preferences
        preferences = self.fusion_app.get_group_preferences("DEFAULT")
        default_units = ao.units_manager.defaultLengthUnits
        default_font = str(preferences["DEFAULT_FONT"])
        default_spacing = adsk.core.ValueInput.createByString(preferences["DEFAULT_PART_SPACING"])
        default_thickness = adsk.core.ValueInput.createByString(preferences["DEFAULT_THICKNESS"])
        default_gap_tol = adsk.core.ValueInput.createByString(preferences["DEFAULT_GAP_TOL"])
        default_parts_per_row = int(preferences["DEFAULT_PARTS_PER_ROW"])
        default_material = str(preferences["DEFAULT_MATERIAL"])
        default_keep_sketches_shown = preferences.get("KEEP_SKETCHES_SHOWN", False)

        if preferences.get("SHOW_POPUP", True):
            ao.ui.messageBox('Select the DXF Files you would like to place in the design')

        # Create file browser dialog box
        file_dialog = ao.ui.createFileDialog()
        file_dialog.filter = ".DXF files (*.dxf);;All files (*.*)"
        file_dialog.isMultiSelectEnabled = True
        file_dialog.title = 'Select dxf files to import'
        dialog_results = file_dialog.showOpen()
        if dialog_results == adsk.core.DialogResults.DialogOK:
            self.file_names = file_dialog.filenames
        else:
            command.isAutoExecute = True
            return

        # Spacing between DXF's
        command_inputs.addValueInput('spacing', 'Spacing between parts: ', default_units, default_spacing)

        # Number of components per rows
        command_inputs.addIntegerSpinnerCommandInput('rows', 'Number per row: ', 1, 999, 1, default_parts_per_row)

        # Resets DXF origin to minimum of the profiles bounding box
        command_inputs.addBoolValueInput(
            "reset_option_input", "Reset Sketch Origins?", True, "", preferences["RESET_ORIGINS"]
        )

        # Combines all layers of a DXF into a single sketch
        command_inputs.addBoolValueInput(
            'single_sketch', 'Combine to single sketch? ', True, "", preferences["SINGLE_SKETCH"]
        )

        # Extrude profiles
        command_inputs.addBoolValueInput(
            "extrude_option_input", "Extrude Profiles?", True, "", preferences["EXTRUDE_PROFILES"]
        )
        command_inputs.addValueInput('distance', 'Thickness: ', default_units, default_thickness)
        command_inputs.addBoolValueInput(
            "keep_sketches_shown", "Keep Sketches Shown", True, "", default_keep_sketches_shown
        )

        # Add Material
        material_check_box = command_inputs.addBoolValueInput(
            "apply_material_input", "Apply Material?", True, "", preferences["APPLY_MATERIAL"]
        )
        drop_down_input = command_inputs.addDropDownCommandInput(
            "material_selection", "Material Name", adsk.core.DropDownStyles.TextListDropDownStyle
        )
        if len(self.material_list) > 0:
            default_material_index = 0
            for i, material_object in enumerate(self.material_list):
                drop_down_input.listItems.add(material_object['name'], False)
                if material_object['name'] == default_material:
                    default_material_index = i

            drop_down_input.listItems.item(default_material_index).isSelected = True
        else:
            drop_down_input.listItems.add("No materials in current design", True)
            material_check_box.value = False
            material_check_box.isEnabled = False

        # Handle Text
        font_file = os.path.join(os.path.dirname(__file__), 'resources', 'fonts.txt')
        self.font_list = open(font_file).read().splitlines()

        command_inputs.addBoolValueInput("import_text", "Import Text?", True, "", preferences["IMPORT_TEXT"])
        drop_down_fonts = command_inputs.addDropDownCommandInput(
            "font_selection", "Font: ", adsk.core.DropDownStyles.TextListDropDownStyle
        )
        preselect = 0
        for i, font_item in enumerate(self.font_list):
            drop_down_fonts.listItems.add(font_item, False)
            if default_font in font_item:
                preselect = i
        drop_down_fonts.listItems.item(preselect).isSelected = True

        # Close Sketches
        command_inputs.addBoolValueInput(
            'close_sketches', 'Close Sketches? ', True, "", preferences["CLOSE_SKETCH_GAPS"]
        )
        command_inputs.addValueInput('tolerance_input', 'Gap Tolerance: ', default_units, default_gap_tol)

        # Save settings
        command_inputs.addBoolValueInput('save_settings', 'Save Settings? ', True, "", False)
        # Save settings
        command_inputs.addBoolValueInput('show_popup', 'Show Popup? ', True, "", preferences["SHOW_POPUP"])

        set_tool_tips(command_inputs, self.tooltips)


class CloseGapsCommand(apper.Fusion360CommandBase):

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)
        if not bool(self.fusion_app.preferences):
            file_name = os.path.join(config.app_path, "default_preferences.json")
            default_preferences = self.fusion_app.read_json_file(file_name)
            self.fusion_app.initialize_preferences(default_preferences)

        self.fusion_app.enable_logging()

    def on_execute(self, command, command_inputs: adsk.core.CommandInputs, args, input_values):
        sketch = input_values['sketch_selection'][0]
        tolerance = input_values['tolerance_input']
        close_sketch_gaps(sketch, tolerance, self.fusion_app.logger)

    def on_create(self, command, command_inputs):
        ao = apper.AppObjects()
        validate_workspace(command)

        preferences = self.fusion_app.get_group_preferences("DEFAULT")
        default_units = ao.units_manager.defaultLengthUnits
        default_gap_tol = adsk.core.ValueInput.createByString(preferences["DEFAULT_GAP_TOL"])

        sketch_selection = command_inputs.addSelectionInput('sketch_selection', 'Sketch: ',
                                                            'Pick a sketch to close gaps')
        sketch_selection.addSelectionFilter('Sketches')
        sketch_selection.setSelectionLimits(1, 1)

        command_inputs.addValueInput('tolerance_input', 'Gap Tolerance: ', default_units, default_gap_tol)
