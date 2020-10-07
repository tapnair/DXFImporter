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

import os
from math import floor

from . import EZDXFCommands
from ..apper import apper


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


class DXFImportCommand(apper.Fusion360CommandBase):

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)
        self.file_names = []
        self.material_list = []
        self.font_list = []

    # Executed on user pressing OK button
    def on_execute(self, command, command_inputs: adsk.core.CommandInputs, args, input_values):
        if len(self.file_names) == 0:
            return

        # explode = input_values['explode_input']
        # flatten = input_values['flatten_input']

        apply_material = input_values['apply_material_input']
        material = None
        drop_down_input = command_inputs.itemById('material_selection')
        if apply_material and (drop_down_input.listItems.count > 0):
            material_index = drop_down_input.selectedItem.index
            material = self.material_list[material_index]['material']

        # Start a time line group
        start_index = apper.start_group()

        # Gets necessary application objects
        ao = apper.AppObjects()
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

        # Read in dxf Files
        dxf_files = get_dxf_files(self.file_names)

        # Iterate all dxf files and create components
        for dxf_file in dxf_files:
            # if flatten or explode:
            #     clean_dxf(dxf_file, flatten, explode)

            # Create new component for this DXF file
            occurrence = apper.create_component(ao.root_comp, dxf_file['name'])

            # Import all layers of DXF to XY plane
            sketches = apper.import_dxf(
                dxf_file['full_path'],
                occurrence.component,
                occurrence.component.xYConstructionPlane,
                input_values['single_sketch']
            )

            x_delta = 0
            y_delta = 0
            face = False
            sketch_transform = None
            extrude_sketch_transform = None
            for sketch in sketches:

                if input_values['close_sketches']:
                    tolerance = input_values['tolerance_input']
                    close_sketch_gaps(sketch, tolerance)

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
                EZDXFCommands.import_dxf_text(dxf_file['full_path'], text_sketch, font_selection, face)

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

            if apply_material:
                occurrence.component.material = material

        ao.design.attributes.add("DXFer", "y_magnitude", str(y_magnitude))
        ao.design.attributes.add("DXFer", "x_magnitude", str(x_magnitude))
        ao.design.attributes.add("DXFer", "row_count", str(row_count))
        ao.design.attributes.add("DXFer", "y_row_max", str(y_row_max))

        # Close time line group
        apper.end_group(start_index)

    # Define the user interface for the command
    def on_create(self, command, command_inputs: adsk.core.CommandInputs):
        validate_workspace(command)
        self.file_names = []
        self.material_list = get_materials()

        # Gets necessary application objects
        ao = apper.AppObjects()

        ao.ui.messageBox('Select the DXF Files you would like to place in the design')

        # Create file browser dialog box
        file_dialog = ao.ui.createFileDialog()
        file_dialog.filter = ".DXF files (*.dxf);;All files (*.*)"
        # file_dialog.initialDirectory = os.path.expanduser("~/Desktop/")
        file_dialog.isMultiSelectEnabled = True
        file_dialog.title = 'Select dxf files to import'

        # Launch file browser
        dialog_results = file_dialog.showOpen()

        if dialog_results == adsk.core.DialogResults.DialogOK:
            self.file_names = file_dialog.filenames
        else:
            command.isAutoExecute = True
            return

        # Gets default units
        default_units = ao.units_manager.defaultLengthUnits
        spacing_default = adsk.core.ValueInput.createByReal(.5)
        distance_default = adsk.core.ValueInput.createByReal(.5)

        # Spacing between dxfs
        command_inputs.addValueInput('spacing', 'Spacing between parts: ', default_units, spacing_default)

        # Number of components per rows
        command_inputs.addIntegerSpinnerCommandInput('rows', 'Number per row: ', 1, 999, 1, 8)

        command_inputs.addBoolValueInput("reset_option_input", "Reset Sketch Origins?", True, "", False)

        command_inputs.addBoolValueInput('single_sketch', 'Combine to single sketch? ', True, "", False)

        command_inputs.addBoolValueInput("extrude_option_input", "Extrude Profiles?", True, "", False)

        # Thickness of profiles
        command_inputs.addValueInput('distance', 'Thickness: ', default_units, distance_default)

        # # Explode Blocks
        # command_inputs.addBoolValueInput("explode_input", "Explode blocks?", True, "", False)

        # Add Material
        command_inputs.addBoolValueInput("apply_material_input", "Apply Material?", True, "", False)
        drop_down_input = command_inputs.addDropDownCommandInput(
            "material_selection", "Material Name", adsk.core.DropDownStyles.TextListDropDownStyle
        )
        if len(self.material_list) > 0:
            for material_object in self.material_list:
                drop_down_input.listItems.add(material_object['name'], False)

            drop_down_input.listItems.item(0).isSelected = True
        else:
            drop_down_input.listItems.add("No materials in current design", True)

        # Handle Text
        font_file = os.path.join(os.path.dirname(__file__), 'resources', 'fonts.txt')
        self.font_list = open(font_file).read().splitlines()

        command_inputs.addBoolValueInput("import_text", "Import Text?", True, "", False)
        drop_down_fonts = command_inputs.addDropDownCommandInput(
            "font_selection", "Font: ", adsk.core.DropDownStyles.TextListDropDownStyle
        )
        for font_item in self.font_list:
            drop_down_fonts.listItems.add(font_item, False)

        drop_down_fonts.listItems.item(0).isSelected = True

        command_inputs.addBoolValueInput('close_sketches', 'Close Sketches? ', True, "", False)

        default_units = ao.units_manager.defaultLengthUnits
        tolerance_default = adsk.core.ValueInput.createByString(
            '.0001' + default_units
        )
        command_inputs.addValueInput('tolerance_input', 'Gap Tolerance: ', default_units, tolerance_default)


def close_sketch_gaps(sketch: adsk.fusion.Sketch, tolerance):
    ao = apper.AppObjects()

    # factor = int(floor(1/tolerance))
    factor = int(floor(1 / .01))
    bounding_box = sketch.boundingBox
    min_x = bounding_box.minPoint.x
    min_y = bounding_box.minPoint.y
    max_x = bounding_box.maxPoint.x
    max_y = bounding_box.maxPoint.y
    x_range = int(floor(factor * (max_x - min_x)))
    y_range = int(floor(factor * (max_y - min_y)))
    trans_x = round(0 - min_x, 6)
    trans_y = round(0 - min_y, 6)

    # str_comp = str(x_range) + ', ' + str(y_range)
    # ao.ui.messageBox(str_comp)
    #
    # str_comp = str(trans_x) + ', ' + str(trans_y)
    # ao.ui.messageBox(str_comp)

    grid = [[0 for i in range(x_range + 2)] for j in range(y_range + 2)]
    str_list = []

    sketch_point: adsk.fusion.SketchPoint
    for sketch_point in sketch.sketchPoints:
        if bounding_box.contains(sketch_point.worldGeometry):
            x_pos = int(floor(factor * (trans_x + sketch_point.worldGeometry.x)))
            y_pos = int(floor(factor * (trans_y + sketch_point.worldGeometry.y)))
            # x_pos = int(factor * round((trans_x + sketch_point.geometry.x), n_places))
            # y_pos = int(factor * round((trans_y + sketch_point.geometry.y), n_places))

            # str_comp = str(x_pos) + ', ' + str(y_pos)
            # str_geo = str(sketch_point.worldGeometry.x) + ', ' + str(sketch_point.worldGeometry.y)
            # ao.ui.messageBox(str_comp + ' : ' + str_geo)

            point_check = grid[y_pos][x_pos]
            add_point = False

            if isinstance(point_check, adsk.fusion.SketchPoint):
                if sketch_point.worldGeometry.distanceTo(point_check.worldGeometry) <= tolerance:
                    # sketch_point.merge(point_check)
                    sketch.geometricConstraints.addCoincident(sketch_point, point_check)
                else:
                    add_point = True
            else:
                add_point = True

            if add_point:
                grid[y_pos][x_pos] = sketch_point
                grid[y_pos + 1][x_pos] = sketch_point
                grid[y_pos - 1][x_pos] = sketch_point
                grid[y_pos][x_pos + 1] = sketch_point
                grid[y_pos + 1][x_pos + 1] = sketch_point
                grid[y_pos - 1][x_pos + 1] = sketch_point
                grid[y_pos][x_pos - 1] = sketch_point
                grid[y_pos + 1][x_pos - 1] = sketch_point
                grid[y_pos - 1][x_pos - 1] = sketch_point

            str_list.append(str(x_pos) + ', ' + str(y_pos))

        # ao.ui.messageBox(str(str_list))


class CloseGapsCommand(apper.Fusion360CommandBase):

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)

    # Executed on user pressing OK button
    def on_execute(self, command, command_inputs: adsk.core.CommandInputs, args, input_values):
        sketch = input_values['sketch_selection'][0]
        tolerance = input_values['tolerance_input']
        close_sketch_gaps(sketch, tolerance)

    def on_create(self, command, command_inputs):
        validate_workspace(command)
        ao = apper.AppObjects()

        sketch_selection = command_inputs.addSelectionInput('sketch_selection', 'Sketch: ',
                                                            'Pick a sketch to close gaps')
        sketch_selection.addSelectionFilter('Sketches')
        sketch_selection.setSelectionLimits(1, 1)

        default_units = ao.units_manager.defaultLengthUnits
        tolerance_default = adsk.core.ValueInput.createByString(
            '.0001' + default_units
        )
        command_inputs.addValueInput('tolerance_input', 'Gap Tolerance: ', default_units, tolerance_default)
