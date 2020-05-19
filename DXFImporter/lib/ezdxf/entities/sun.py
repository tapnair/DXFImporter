# Copyright (c) 2019, Manfred Moitzi
# License: MIT-License
# Created: 2019-03-11
from typing import TYPE_CHECKING
from ezdxf.lldxf.const import SUBCLASS_MARKER, DXF2007
from ezdxf.lldxf.attributes import DXFAttributes, DefSubclass, DXFAttr
from .dxfentity import base_class, SubclassProcessor
from .dxfobj import DXFObject
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace

__all__ = ['Sun']

acdb_sun = DefSubclass('AcDbSun', {
    'version': DXFAttr(90, default=1),
    'status': DXFAttr(290, default=1),
    'color': DXFAttr(63, default=7),
    'true_color': DXFAttr(421, default=16777215),
    'intensity': DXFAttr(40, default=1),
    'shadows': DXFAttr(291, default=1),
    'julian_day': DXFAttr(91, default=2456922),
    'time': DXFAttr(92, default=43200),  # Time (in seconds past midnight)
    'daylight_savings_time': DXFAttr(292, default=0),
    'shadow_type': DXFAttr(70, default=0),  # Shadow type 0 = Ray traced shadows; 1 = Shadow maps
    'shadow_map_size': DXFAttr(71, default=256),
    'shadow_softness': DXFAttr(280, default=1),
})


@register_entity
class Sun(DXFObject):
    """ DXF SUN entity """
    DXFTYPE = 'SUN'
    DXFATTRIBS = DXFAttributes(base_class, acdb_sun)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2007

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            processor.load_dxfattribs_into_namespace(dxf, acdb_sun)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_sun.name)
        self.dxf.export_dxf_attribs(tagwriter, [
            'version', 'status', 'color', 'true_color', 'intensity', 'shadows', 'julian_day', 'time',
            'daylight_savings_time', 'shadow_type', 'shadow_map_size', 'shadow_softness'
        ])


# todo: implement SUNSTUDY?
acdb_sunstudy = DefSubclass('AcDbSun', {
    'version': DXFAttr(90),
    'name': DXFAttr(1),
    'description': DXFAttr(2),
    'output_type': DXFAttr(70),
    'sheet_set_name': DXFAttr(3),  # Included only if Output type is Sheet Set.
    'use_subset': DXFAttr(290),  # Included only if Output type is Sheet Set.
    'sheet_subset_name': DXFAttr(4),  # Included only if Output type is Sheet Set.
    'dates_from_calender': DXFAttr(291),
    'date_input_array_size': DXFAttr(91),  # represents the number of dates picked
    # 90 Julian day; represents the date. One entry for each date picked.
    # 90 Seconds past midnight; represents the time of day. One entry for each date picked.
    'range_of_dates': DXFAttr(292),
    # 93 Start time. If range of dates flag is true.
    # 94 End time. If range of dates flag is true.
    # 95 Interval in seconds. If range of dates flag is true.
    'hours_count': DXFAttr(73),
    # 290 Hour. One entry for every hour as specified by the number of hours entry above.
    'page_setup_wizard_id': DXFAttr(340),  # Page setup wizard hard pointer ID
    'view_id': DXFAttr(341),  # View hard pointer ID
    'visual_style_id': DXFAttr(342),  # Visual Style ID
    'shade_plot_type': DXFAttr(74),
    'viewports_per_page': DXFAttr(75),
    'nrows': DXFAttr(76),  # Number of rows for viewport distribution
    'ncols': DXFAttr(77),  # Number of columns for viewport distribution
    'spacing': DXFAttr(40),
    'lock_viewports': DXFAttr(293),
    'label_viewports': DXFAttr(294),
    'text_style_id': DXFAttr(343),
})
