# Copyright (c) 2019-2020 Manfred Moitzi
# License: MIT License
# Created 2019-02-15
from typing import TYPE_CHECKING
from ezdxf.math import Vector
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass, XType
from ezdxf.lldxf.const import SUBCLASS_MARKER, DXF2000
from .dxfentity import base_class, SubclassProcessor
from .dxfgfx import DXFGraphic, acdb_entity
from .factory import register_entity

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace, UCS

__all__ = ['Ray', 'XLine']

acdb_xline = DefSubclass('AcDbXline', {
    'start': DXFAttr(10, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'unit_vector': DXFAttr(11, xtype=XType.point3d, default=Vector(1, 0, 0)),
})


@register_entity
class XLine(DXFGraphic):
    """ DXF XLINE entity """
    DXFTYPE = 'XLINE'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_xline)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000
    XLINE_SUBCLASS = 'AcDbXline'

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_xline, 2)
            if len(tags):
                processor.log_unprocessed_tags(tags, subclass=self.XLINE_SUBCLASS)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, self.XLINE_SUBCLASS)
        # for all DXF versions
        self.dxf.export_dxf_attribs(tagwriter, ['start', 'unit_vector'])

    def transform_to_wcs(self, ucs: 'UCS') -> 'XLine':
        """ Transform XLINE/RAY entity from local :class:`~ezdxf.math.UCS` coordinates to
        :ref:`WCS` coordinates.

        .. versionadded:: 0.11

        """
        self.dxf.start = ucs.to_wcs(self.dxf.start)
        self.dxf.unit_vector = ucs.direction_to_wcs(self.dxf.unit_vector)
        return self


@register_entity
class Ray(XLine):
    """ DXF Ray entity """
    DXFTYPE = 'RAY'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_xline)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000
    XLINE_SUBCLASS = 'AcDbRay'
