import os

import adsk.core
import adsk.fusion
import traceback

import apper
from apper import AppObjects


# Extract file names of all dxf files in a directory
def get_dxf_files(file_names):
    dxf_files = []

    for filename in file_names:

        if filename.endswith(".dxf"):
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


def move_sketch_to_origin(sketch: adsk.fusion.Sketch):
    vector = sketch.boundingBox.minPoint.asVector()
    vector.scaleBy(-1.0)
    new_transform = adsk.core.Matrix3D.create()
    new_transform.translation = vector
    all_curves = adsk.core.ObjectCollection.create()
    for entity in sketch.sketchCurves:
        all_curves.add(entity)

    sketch.move(all_curves, new_transform)


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
        extrude_feature = extrudes.add(ext_input)
        return True
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


class DXFImportCommand(apper.Fusion360CommandBase):

    def __init__(self, name: str, options: dict):
        super().__init__(name, options)
        self.file_names = []

    # Executed on user pressing OK button
    def on_execute(self, command, command_inputs, args, input_values):

        # Start a time line group
        start_index = apper.start_group()

        # Gets necessary application objects
        ao = AppObjects()

        # Define spacing and directions
        x_vector = adsk.core.Vector3D.create(1.0, 0.0, 0.0)
        x_magnitude = 0.0
        y_vector = adsk.core.Vector3D.create(0.0, 1.0, 0.0)
        y_magnitude = 0.0
        y_row_max = 0.0
        row_count = 0

        # Read in dxf Files
        dxf_files = get_dxf_files(self.file_names)

        # Iterate all dxf files and create components
        for dxf_file in dxf_files:

            # Create new component for this DXF file
            occurrence = apper.create_component(ao.root_comp, dxf_file['name'])

            # Import all layers of DXF to XY plane
            sketches = apper.import_dxf(dxf_file['full_path'], occurrence.component,
                                        occurrence.component.xYConstructionPlane)

            x_delta = 0
            y_delta = 0
            for sketch in sketches:
                if input_values['reset_option_input']:
                    move_sketch_to_origin(sketch)

                x_delta_check = get_bb_in_direction(sketch, x_vector)
                if x_delta_check > x_delta:
                    x_delta = x_delta_check
                y_delta_check = get_bb_in_direction(sketch, y_vector)
                if y_delta_check > y_delta:
                    y_delta = y_delta_check
                if input_values['extrude_option_input']:
                    extrude_largest_profile(sketch, occurrence.component, input_values['distance'])
                    # apper.extrude_all_profiles(
                    #     sketch, input_values['distance'], occurrence.component,
                    #     adsk.fusion.FeatureOperations.NewBodyFeatureOperation
                    # )

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

        # Close time line group
        apper.end_group(start_index)

    # Define the user interface for the command
    def on_create(self, command, command_inputs: adsk.core.CommandInputs):
        self.file_names = []

        # Gets necessary application objects
        ao = AppObjects()

        ao.ui.messageBox('Select the DXF Files you would like to place in the design')

        # Create file browser dialog box
        file_dialog = ao.ui.createFileDialog()
        file_dialog.filter = ".DXF files (*.dxf);;All files (*.*)"
        file_dialog.initialDirectory = os.path.expanduser("~/Desktop/")
        file_dialog.isMultiSelectEnabled = True
        file_dialog.title = 'Select dxf files to import'

        # Launch file browser
        dialog_results = file_dialog.showOpen()

        if dialog_results == adsk.core.DialogResults.DialogOK:
            self.file_names = file_dialog.filenames

        else:
            command.destroy()

        # Gets default units
        default_units = ao.units_manager.defaultLengthUnits
        spacing_default = adsk.core.ValueInput.createByReal(.5)
        distance_default = adsk.core.ValueInput.createByReal(.5)

        # Spacing between dxfs
        command_inputs.addValueInput('spacing', 'Spacing between parts: ', default_units, spacing_default)

        # Number of components per rows
        command_inputs.addIntegerSpinnerCommandInput('rows', 'Number per row: ', 1, 999, 1, 8)

        command_inputs.addBoolValueInput("reset_option_input", "Reset Sketch Origins?", True, "", False)

        command_inputs.addBoolValueInput("extrude_option_input", "Extrude Profiles?", True, "", False)

        # Thickness of profiles
        command_inputs.addValueInput('distance', 'Thickness: ', default_units, distance_default)
