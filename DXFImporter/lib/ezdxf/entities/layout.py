# Copyright (c) 2019, Manfred Moitzi
# License: MIT-License
# Created: 2019-02-18
from typing import TYPE_CHECKING
from ezdxf.lldxf.const import SUBCLASS_MARKER
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass, XType
from .dxfentity import base_class, SubclassProcessor
from .dxfobj import DXFObject
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace

__all__ = ['PlotSettings', 'DXFLayout']

acdb_plot_settings = DefSubclass('AcDbPlotSettings', {
    # acdb_plot_settings is also part of LAYOUT and LAYOUT has a 'name' attribute
    'page_setup_name': DXFAttr(1, default=''),
    'plot_configuration_file': DXFAttr(2, default='Adobe PDF'),
    'paper_size': DXFAttr(4, default='A4'),
    'plot_view_name': DXFAttr(6, default=''),
    'left_margin': DXFAttr(40, default=3.175),  # in mm
    'bottom_margin': DXFAttr(41, default=3.175),  # in mm
    'right_margin': DXFAttr(42, default=3.175),  # in mm
    'top_margin': DXFAttr(43, default=3.175),  # in mm
    'paper_width': DXFAttr(44, default=209.91),  # in mm
    'paper_height': DXFAttr(45, default=297.03),  # in mm
    'plot_origin_x_offset': DXFAttr(46, default=0.),  # in mm
    'plot_origin_y_offset': DXFAttr(47, default=0.),  # in mm
    'plot_window_x1': DXFAttr(48, default=0.),
    'plot_window_y1': DXFAttr(49, default=0.),
    'plot_window_x2': DXFAttr(140, default=0.),
    'plot_window_y2': DXFAttr(141, default=0.),
    'scale_numerator': DXFAttr(142, default=1.),  # Numerator of custom print scale: real world (paper) units
    'scale_denominator': DXFAttr(143, default=1.),  # Denominator of custom print scale: drawing units

    'plot_layout_flags': DXFAttr(70, default=688),
    # 1 = Plot Viewport Borders
    # 2 = Show Plot Styles
    # 4 = Plot Centered
    # 8 = Plot Hidden
    # 16 = Use Standard Scale
    # 32 = Plot Plot Styles
    # 64 = Scale Lineweights
    # 128 = Print Lineweights
    # 512 = Draw Viewports First
    # 1024 = Model Type
    # 2048 = Update Paper
    # 4096 = Zoom To Paper On Update
    # 8192 = Initializing
    # 16384 = Prev PlotInit

    'plot_paper_units': DXFAttr(72, default=0),
    # 0 = Plot in inches
    # 1 = Plot in millimeters
    # 2 = Plot in pixels

    'plot_rotation': DXFAttr(73, default=1),
    # 0 = No rotation
    # 1 = 90 degrees counterclockwise
    # 2 = Upside-down
    # 3 = 90 degrees clockwise

    'plot_type': DXFAttr(74, default=5),
    # 0 = Last screen display
    # 1 = Drawing extents
    # 2 = Drawing limits
    # 3 = View specified by code 6
    # 4 = Window specified by codes 48, 49, 140, and 141
    # 5 = Layout information
    'current_style_sheet': DXFAttr(7, default=''),
    'standard_scale_type': DXFAttr(75, default=16),
    # 0 = Scaled to Fit
    # 1 = 1/128"=1'
    # 2 = 1/64"=1'
    # 3 = 1/32"=1'
    # 4 = 1/16"=1'
    # 5 = 3/32"=1'
    # 6 = 1/8"=1'
    # 7 = 3/16"=1'
    # 8 = 1/4"=1'
    # 9 = 3/8"=1'
    # 10 = 1/2"=1'
    # 11 = 3/4"=1'
    # 12 = 1"=1'
    # 13 = 3"=1'
    # 14 = 6"=1'
    # 15 = 1'=1'
    # 16 = 1:1
    # 17 = 1:2
    # 18 = 1:4
    # 19 = 1:8
    # 20 = 1:10
    # 21 = 1:16
    # 22 = 1:20
    # 23 = 1:30
    # 24 = 1:40
    # 25 = 1:50
    # 26 = 1:100
    # 27 = 2:1
    # 28 = 4:1
    # 29 = 8:1
    # 30 = 10:1
    # 31 = 100:1
    # 32 = 1000:1

    'shade_plot_mode': DXFAttr(76, default=0),
    # 0 = As Displayed
    # 1 = Wireframe
    # 2 = Hidden
    # 3 = Rendered

    'shade_plot_resolution_level': DXFAttr(77, default=2),
    # 0 = Draft
    # 1 = Preview
    # 2 = Normal
    # 3 = Presentation
    # 4 = Maximum
    # 5 = Custom

    'shade_plot_custom_dpi': DXFAttr(78, default=300),
    # Valid range: 100 to 32767, Only applied when the shade_plot_resolution level is set to 5 (Custom)

    'unit_factor': DXFAttr(147, default=1.0),
    # 147: factor for unit conversion (mm -> inches)
    # 147: DXF Reference error 'A floating point scale factor that represents the standard scale value specified in code 75'

    'paper_image_origin_x': DXFAttr(148, default=0),
    'paper_image_origin_y': DXFAttr(149, default=0),
    'shade_plot_handle': DXFAttr(333, optional=True),  # optional
})


@register_entity
class PlotSettings(DXFObject):
    DXFTYPE = 'PLOTSETTINGS'
    DXFATTRIBS = DXFAttributes(base_class, acdb_plot_settings)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor is None:
            return dxf

        processor.load_dxfattribs_into_namespace(dxf, acdb_plot_settings)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_plot_settings.name)

        self.dxf.export_dxf_attribs(tagwriter, [
            'page_setup_name', 'plot_configuration_file', 'paper_size', 'plot_view_name', 'left_margin',
            'bottom_margin', 'right_margin', 'top_margin', 'paper_width', 'paper_height', 'plot_origin_x_offset',
            'plot_origin_y_offset', 'plot_window_x1', 'plot_window_y1', 'plot_window_x2', 'plot_window_y2',
            'scale_numerator', 'scale_denominator', 'plot_layout_flags', 'plot_paper_units', 'plot_rotation',
            'plot_type', 'current_style_sheet', 'standard_scale_type', 'shade_plot_mode', 'shade_plot_resolution_level',
            'shade_plot_custom_dpi', 'unit_factor', 'paper_image_origin_x', 'paper_image_origin_y',
        ])


acdb_layout = DefSubclass('AcDbLayout', {
    'name': DXFAttr(1, default='Layoutname'),  # layout name
    'layout_flags': DXFAttr(70, default=1),
    # Flag (bit-coded) to control the following:
    # 1 = Indicates the PSLTSCALE value for this layout when this layout is current
    # 2 = Indicates the LIMCHECK value for this layout when this layout is current
    'taborder': DXFAttr(71, default=1),
    # Tab order. This number is an ordinal indicating this layout's ordering in the tab control that is attached to the
    # AutoCAD drawing frame window. Note that the “Model” tab always appears as the first tab regardless of its tab order
    'limmin': DXFAttr(10, xtype=XType.point2d, default=(-3.175, -3.175)),  # minimum limits
    'limmax': DXFAttr(11, xtype=XType.point2d, default=(293.857, 206.735)),  # maximum limits
    'insert_base': DXFAttr(12, xtype=XType.point3d, default=(0, 0, 0)),  # Insertion base point for this layout
    'extmin': DXFAttr(14, xtype=XType.point3d, default=(29.068, 20.356, 0)),  # Minimum extents for this layout
    'extmax': DXFAttr(15, xtype=XType.point3d, default=(261.614, 183.204, 0)),  # Maximum extents for this layout
    'elevation': DXFAttr(146, default=0.),
    'ucs_origin': DXFAttr(13, xtype=XType.point3d, default=(0, 0, 0)),
    'ucs_xaxis': DXFAttr(16, xtype=XType.point3d, default=(1, 0, 0)),
    'ucs_yaxis': DXFAttr(17, xtype=XType.point3d, default=(0, 1, 0)),
    'ucs_type': DXFAttr(76, default=1),
    # Orthographic type of UCS 0 = UCS is not orthographic;
    # 1 = Top; 2 = Bottom; 3 = Front; 4 = Back; 5 = Left; 6 = Right
    'block_record_handle': DXFAttr(330),
    'viewport_handle': DXFAttr(331),
    # ID/handle to the viewport that was last active in this
    # layout when the layout was current
    'ucs_handle': DXFAttr(345),
    # ID/handle of AcDbUCSTableRecord if UCS is a named
    # UCS. If not present, then UCS is unnamed
    'base_ucs_handle': DXFAttr(346),
    # ID/handle of AcDbUCSTableRecord of base UCS if UCS is
    # orthographic (76 code is non-zero). If not present and
    # 76 code is non-zero, then base UCS is taken to be WORLD
})


@register_entity
class DXFLayout(PlotSettings):
    DXFTYPE = 'LAYOUT'
    DXFATTRIBS = DXFAttributes(base_class, acdb_plot_settings, acdb_layout)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor is None:
            return dxf

        processor.load_dxfattribs_into_namespace(dxf, acdb_layout)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        # set correct Model Type flag
        self.set_flag_state(1024, self.dxf.name == 'Model', 'plot_layout_flags')
        # base class export is done by parent class
        super().export_entity(tagwriter)
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_layout.name)
        self.dxf.export_dxf_attribs(tagwriter, [
            'name', 'layout_flags', 'taborder', 'limmin', 'limmax', 'insert_base', 'extmin', 'extmax', 'elevation',
            'ucs_origin', 'ucs_xaxis', 'ucs_yaxis', 'ucs_type', 'block_record_handle', 'viewport_handle', 'ucs_handle',
            'base_ucs_handle',
        ])
