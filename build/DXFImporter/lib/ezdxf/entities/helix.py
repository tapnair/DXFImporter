# Copyright (c) 2019-2020 Manfred Moitzi
# License: MIT License
# Created 2019-03-10
from typing import TYPE_CHECKING
from ezdxf.math import Vector
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass, XType
from ezdxf.lldxf.const import SUBCLASS_MARKER
from .spline import Spline, acdb_spline
from .dxfentity import base_class, SubclassProcessor
from .dxfgfx import acdb_entity
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace, UCS

__all__ = ['Helix']

acdb_helix = DefSubclass('AcDbHelix', {
    'major_release_number': DXFAttr(90, default=29),
    'maintenance_release_number': DXFAttr(91, default=63),
    'axis_base_point': DXFAttr(10, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'start_point': DXFAttr(11, xtype=XType.point3d, default=Vector(1, 0, 0)),
    'axis_vector': DXFAttr(12, xtype=XType.point3d, default=Vector(0, 0, 1)),
    'radius': DXFAttr(40, default=1),
    'turns': DXFAttr(41, default=1),
    'turn_height': DXFAttr(42, default=1),

    # Handedness: 0=left, 1=right
    'handedness': DXFAttr(290, default=1),

    # Constrain type: 0= Constrain turn height; 1= Constrain turns; 2= Constrain height
    'constrain': DXFAttr(280, default=1),

})


@register_entity
class Helix(Spline):
    """ DXF HELIX entity """
    DXFTYPE = 'HELIX'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_spline, acdb_helix)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_helix)
            if len(tags):
                processor.log_unprocessed_tags(tags, subclass=acdb_helix.name)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_helix.name)
        self.dxf.export_dxf_attribs(tagwriter, [
            'major_release_number', 'maintenance_release_number', 'axis_base_point', 'start_point', 'axis_vector',
            'radius', 'turns', 'turn_height', 'handedness', 'constrain'

        ])

    def transform_to_wcs(self, ucs: 'UCS') -> 'Helix':
        """ Transform HELIX entity from local :class:`~ezdxf.math.UCS` coordinates to :ref:`WCS` coordinates.

        .. versionadded:: 0.11

        """
        super().transform_to_wcs(ucs)
        self.dxf.axis_base_point = ucs.to_wcs(self.dxf.axis_base_point)
        self.dxf.axis_vector = ucs.direction_to_wcs(self.dxf.axis_vector)
        self.dxf.start_point = ucs.to_wcs(self.dxf.start_point)
        return self
