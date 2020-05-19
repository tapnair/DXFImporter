# Created: 17.02.2019
# Copyright (c) 2019, Manfred Moitzi
# License: MIT License
from typing import TYPE_CHECKING, Optional, Tuple
import logging
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass
from ezdxf.lldxf.const import DXF12, SUBCLASS_MARKER, DXF2000, DXF2007, DXF2004, DXFInvalidLayerName
from ezdxf.lldxf.const import INVALID_NAME_CHARACTERS
from ezdxf.entities.dxfentity import base_class, SubclassProcessor, DXFEntity
from ezdxf.lldxf.validator import is_valid_layer_name
from ezdxf.tools import rgb2int, int2rgb, transparency2float, float2transparency
from ezdxf.lldxf.const import DXFValueError, DXFTableEntryError

from .factory import register_entity

logger = logging.getLogger('ezdxf')

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DXFNamespace

__all__ = ['Layer']

acdb_symbol_table_record = DefSubclass('AcDbSymbolTableRecord', {})

acdb_layer_table_record = DefSubclass('AcDbLayerTableRecord', {
    'name': DXFAttr(2),  # layer name
    'flags': DXFAttr(70, default=0),
    'color': DXFAttr(62, default=7),  # dxf color index
    'true_color': DXFAttr(420, dxfversion=DXF2004, optional=True),  # true color
    'linetype': DXFAttr(6, default='Continuous'),  # linetype name
    'plot': DXFAttr(290, default=1, dxfversion=DXF2000, optional=True),  # don't plot this layer if 0 else 1
    'lineweight': DXFAttr(370, default=-3, dxfversion=DXF2000),  # 1/100 mm, min 13 = 0.13mm, max 200 = 2.0mm

    # code 390 is required for AutoCAD
    # Pointer/handle to PlotStyleName
    # uses tag(390, ...) from the '0' layer1
    'plotstyle_handle': DXFAttr(390, dxfversion=DXF2000),  # handle to PlotStyleName object
    'material_handle': DXFAttr(347, dxfversion=DXF2007),  # handle to Material object
    'unknown1': DXFAttr(348, dxfversion=DXF2007, optional=True),  # handle to ???

})

AcAecLayerStandard = "AcAecLayerStandard"
AcCmTransparency = "AcCmTransparency"


@register_entity
class Layer(DXFEntity):
    """ DXF LAYER entity """
    DXFTYPE = 'LAYER'
    DXFATTRIBS = DXFAttributes(base_class, acdb_symbol_table_record, acdb_layer_table_record)
    DEFAULT_ATTRIBS = {'name': '0'}
    FROZEN = 0b00000001
    THAW = 0b11111110
    LOCK = 0b00000100
    UNLOCK = 0b11111011

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor is None:
            return dxf

        tags = processor.load_dxfattribs_into_namespace(dxf, acdb_layer_table_record)
        if len(tags) and not processor.r12:
            processor.log_unprocessed_tags(tags, subclass=acdb_layer_table_record.name)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        if tagwriter.dxfversion > DXF12:
            tagwriter.write_tag2(SUBCLASS_MARKER, acdb_symbol_table_record.name)
            tagwriter.write_tag2(SUBCLASS_MARKER, acdb_layer_table_record.name)

        self.dxf.export_dxf_attribs(tagwriter, [
            'name', 'flags', 'color', 'true_color', 'linetype', 'plot', 'lineweight', 'plotstyle_handle',
            'material_handle', 'unknown1',
        ])

    def post_new_hook(self) -> None:
        if not is_valid_layer_name(self.dxf.name):
            raise DXFInvalidLayerName("Invalid layer name '{}'".format(self.dxf.name))

    def set_required_attributes(self):
        if not self.dxf.hasattr('material'):
            self.dxf.material_handle = self.doc.materials['Global'].dxf.handle
        if not self.dxf.hasattr('plotstyle_handle'):
            self.dxf.plotstyle_handle = self.doc.plotstyles['Normal'].dxf.handle

    def is_frozen(self) -> bool:
        """ Returns ``True`` if layer is frozen. """
        return self.dxf.flags & Layer.FROZEN > 0

    def freeze(self) -> None:
        """ Freeze layer. """
        self.dxf.flags = self.dxf.flags | Layer.FROZEN

    def thaw(self) -> None:
        """ Thaw layer."""
        self.dxf.flags = self.dxf.flags & Layer.THAW

    def is_locked(self) -> bool:
        """ Returns ``True`` if layer is locked. """
        return self.dxf.flags & Layer.LOCK > 0

    def lock(self) -> None:
        """ Lock layer, entities on this layer are not editable - just important in CAD applications. """
        self.dxf.flags = self.dxf.flags | Layer.LOCK

    def unlock(self) -> None:
        """ Unlock layer, entities on this layer are editable - just important in CAD applications. """
        self.dxf.flags = self.dxf.flags & Layer.UNLOCK

    def is_off(self) -> bool:
        """ Returns ``True`` if layer is off. """
        return self.dxf.color < 0

    def is_on(self) -> bool:
        """ Returns ``True`` if layer is on. """
        return not self.is_off()

    def on(self) -> None:
        """ Switch layer `on` (visible)."""
        self.dxf.color = abs(self.dxf.color)

    def off(self) -> None:
        """ Switch layer `off` (invisible). """
        self.dxf.color = -abs(self.dxf.color)

    def get_color(self) -> int:
        """ Get layer color, safe method for getting the layer color, because dxf.color is negative
        for layer status `off`.
        """
        return abs(self.dxf.color)

    def set_color(self, color: int) -> None:
        """ Set layer color, safe method for setting the layer color, because dxf.color is negative
        for layer status `off`.
        """
        color = abs(color) if self.is_on() else -abs(color)
        self.dxf.color = color

    @property
    def rgb(self) -> Optional[Tuple[int, int, int]]:
        """ Returns RGB true color as (r, g, b)-tuple or None if attribute dxf.true_color is not set. """
        if self.dxf.hasattr('true_color'):
            return int2rgb(self.dxf.get('true_color'))
        else:
            return None

    @rgb.setter
    def rgb(self, rgb: Tuple[int, int, int]) -> None:
        """ Set RGB true color as (r, g, b)-tuple e.g. (12, 34, 56). """
        self.dxf.set('true_color', rgb2int(rgb))

    @property
    def color(self) -> int:
        """ Get layer color, safe method for getting the layer color, because dxf.color is negative
        for layer status `off`.
        """
        return self.get_color()

    @color.setter
    def color(self, value: int) -> None:
        """ Set layer color, safe method for setting the layer color, because dxf.color is negative
        for layer status `off`.
        """
        self.set_color(value)

    @property
    def description(self) -> str:
        try:
            xdata = self.get_xdata(AcAecLayerStandard)
        except DXFValueError:
            return ""
        else:
            if len(xdata) > 1:
                # this is the usual case in BricsCAD
                return xdata[1].value
            else:
                return ""

    @description.setter
    def description(self, value: str) -> None:
        # create AppID table entry if not present
        if self.doc and AcAecLayerStandard not in self.doc.appids:
            self.doc.appids.new(AcAecLayerStandard)
        self.discard_xdata(AcAecLayerStandard)
        self.set_xdata(AcAecLayerStandard, [(1000, ''), (1000, value)])

    @property
    def transparency(self) -> float:
        try:
            xdata = self.get_xdata(AcCmTransparency)
        except DXFValueError:
            return 0
        else:
            return transparency2float(xdata[0].value)

    @transparency.setter
    def transparency(self, value: float) -> None:
        # create AppID table entry if not present
        if self.doc and AcCmTransparency not in self.doc.appids:
            self.doc.appids.new(AcCmTransparency)
        if 0 <= value <= 1:
            self.discard_xdata(AcCmTransparency)
            self.set_xdata(AcCmTransparency, [(1071, float2transparency(value))])
        else:
            raise ValueError('Value out of range (0 .. 1).')

    def rename(self, name: str) -> None:
        """
        Rename layer and all known (documented) references to this layer.

        .. warning::

            Renaming layers may damage the DXF file in some circumstances!

        Args:
             name: new layer name

        Raises:
            ValueError: `name` contains invalid characters: <>/\\":;?*|=`
            ValueError: layer `name` already exist
            ValueError: renaming of layers ``'0'`` and ``'DEFPOINTS'`` not possible

        """
        if not is_valid_layer_name(name):
            raise ValueError('Name contains invalid characters: {}.'.format(INVALID_NAME_CHARACTERS))
        layers = self.doc.layers
        if self.dxf.name.lower() in ('0', 'defpoints'):
            raise ValueError('Can not rename layer "{}".'.format(self.dxf.name))
        if layers.has_entry(name):
            raise ValueError('Layer "{}" already exist.'.format(name))
        old = self.dxf.name
        self.dxf.name = name
        layers.replace(old, self)
        self._rename_layer_references(old, name)

    def _rename_layer_references(self, old_name: str, new_name: str) -> None:
        key = self.doc.layers.key
        old_key = key(old_name)
        for e in self.doc.entitydb.values():
            if e.dxf.hasattr('layer') and key(e.dxf.layer) == old_key:
                e.dxf.layer = new_name
            entity_type = e.dxftype()
            if entity_type == 'VIEWPORT':
                e.rename_frozen_layer(old_name, new_name)
            elif entity_type == 'LAYER_FILTER':
                # todo: if LAYER_FILTER implemented, add support for renaming layers
                logger.debug('renaming layer "{}" - document contains LAYER_FILTER'.format(old_name))
            elif entity_type == 'LAYER_INDEX':
                # todo: if LAYER_INDEX implemented, add support for renaming layers
                logger.debug('renaming layer "{}" - document contains LAYER_INDEX'.format(old_name))
