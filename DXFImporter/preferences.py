# You can set some default values here.

# Show "Pick DXF Files" message popup
# This must be a boolean, i.e. True or False
SHOW_POPUP = True

# The default spacing used for laying out the DXF files
# This is a string that must include units.
# The valid values for units are: ft, in, m, cm, mm
DEFAULT_PART_SPACING = '.5 in'

# The default number of parts per row when laying out the imported DXF files
# This must be positive integer
DEFAULT_PARTS_PER_ROW = 8

# Default value for reset sketch origins option
# This must be a boolean, i.e. True or False
RESET_ORIGINS = False

# Default value for the option to collapse aall DXF layers to a single sketch
# This must be a boolean, i.e. True or False
SINGLE_SKETCH = False

# Default value for whether to extrude the profiles in the imported DXF files
# This must be a boolean, i.e. True or False
EXTRUDE_PROFILES = True

# The default thickness used for creating extruded profiles of the input DXF files
# This is a string that must include units.
# The valid values for units are: ft, in, m, cm, mm
DEFAULT_THICKNESS = '.25 in'

# Default value for whether to apply a specific material.
# This must be a boolean, i.e. True or False
APPLY_MATERIAL = True

# The default material to use.
# NOTE: To apply a material you MUST first add the material to the active document.
# If it is not present in the active document, the first one in the list will be selected.
DEFAULT_MATERIAL = "Steel"

# Default value for whether to import text from the DXF
# This must be a boolean, i.e. True or False
IMPORT_TEXT = False

# The default font used for importing text.
# The available fonts are currently saved in DXFImporter/commands/resources/fonts.txt
# If these fonts do not match your system fonts, you may also need to edit this list.
DEFAULT_FONT = "Monotxt8"

# Default value for whether to attempt to close small gaps in the sketches from the imported DXF files
# NOTE: Can be time consuming.
# This must be a boolean, i.e. True or False
CLOSE_SKETCH_GAPS = False

# The default tolerance used for the close sketch option and command.
# This is a string that must include units.
# The valid values for units are: ft, in, m, cm, mm
DEFAULT_GAP_TOL = '.0001 in'



