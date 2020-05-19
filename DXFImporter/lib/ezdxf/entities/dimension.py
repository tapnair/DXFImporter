# Copyright (c) 2019-2020 Manfred Moitzi
# License: MIT License
# Created 2019-02-22
import math
from typing import TYPE_CHECKING, Optional, Union, Iterable

from ezdxf.math import Vector
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass, XType
from ezdxf.lldxf.const import DXF12, SUBCLASS_MARKER, DXF2010, DXF2000, DXF2007, DXF2004
from ezdxf.lldxf.const import DXFInternalEzdxfError, DXFValueError, DXFTableEntryError, DXFTypeError
from ezdxf.lldxf.types import get_xcode_for
from ezdxf.tools import take2
from ezdxf.render.arrows import ARROWS
from .dxfentity import base_class, SubclassProcessor
from .dxfgfx import DXFGraphic, acdb_entity
from .factory import register_entity
from .dimstyleoverride import DimStyleOverride
from ezdxf.explode import explode_entity
import logging

if TYPE_CHECKING:
    from ezdxf.eztypes import TagWriter, DimStyle, DXFNamespace, BlockLayout, OCS, UCS, BaseLayout, EntityQuery

logger = logging.getLogger('ezdxf')

__all__ = ['Dimension', 'OverrideMixin']

acdb_dimension = DefSubclass('AcDbDimension', {
    'version': DXFAttr(280, default=0, dxfversion=DXF2010),  # Version number: 0 = 2010
    'geometry': DXFAttr(2),  # Name of the block that contains the entities that make up the dimension picture
    'dimstyle': DXFAttr(3, default='Standard'),  # dimension style name
    # The dimension style is stored in doc.sections.tables.dimstyles,
    # shortcut Drawings.dimstyles property
    'defpoint': DXFAttr(10, xtype=XType.point3d, default=Vector(0, 0, 0)),
    # definition point for all dimension types in WCS
    'text_midpoint': DXFAttr(11, xtype=XType.point3d),  # midpoint of dimension text in OCS

    # Insertion point for clones of a  dimension—Baseline and Continue (in OCS)
    # located in AcDbDimension? Another error in the DXF reference?
    'insert': DXFAttr(12, xtype=XType.point3d, default=Vector(0, 0, 0), optional=True),

    'dimtype': DXFAttr(70, default=0),  # Dimension type:
    # Values 0–6 are integer values that represent the dimension type.
    # Values 32, 64, and 128 are bit values, which are added to the integer values
    # (value 32 is always set in R13 and later releases)
    # 0 = Rotated, horizontal, or vertical;
    # 1 = Aligned
    # 2 = Angular;
    # 3 = Diameter;
    # 4 = Radius
    # 5 = Angular 3 point;
    # 6 = Ordinate
    # 8 = Arc Dimension ??? -> ARC_DIMENSION
    # 32 = Indicates that the block reference (group code 2) is referenced by this dimension only
    # 64 = Ordinate type. This is a bit value (bit 7) used only with integer
    # value 6. If set, ordinate is X-type; if not set, ordinate is Y-type
    # 128 = This is a bit value (bit 8) added to the other group 70 values if
    # the dimension text has been positioned at a user-defined location
    # rather than at the default location

    'attachment_point': DXFAttr(71, default=5, dxfversion=DXF2000),  # Attachment point:
    # 1 = Top left; 2 = Top center; 3 = Top right
    # 4 = Middle left; 5 = Middle center; 6 = Middle right
    # 7 = Bottom left; 8 = Bottom center; 9 = Bottom right

    'line_spacing_style': DXFAttr(72, default=1, dxfversion=DXF2000, optional=True),
    # Dimension text line-spacing style
    # 1 (or missing) = At least (taller characters will override)
    # 2 = Exact (taller characters will not override)
    'line_spacing_factor': DXFAttr(41, dxfversion=DXF2000, optional=True),  # Dimension text-line spacing factor
    # Percentage of default (3-on-5) line spacing to be applied. Valid values
    # range from 0.25 to 4.00
    'actual_measurement': DXFAttr(42, dxfversion=DXF2000, optional=True),
    # Actual measurement (optional; read-only value)
    'unknown1': DXFAttr(73, dxfversion=DXF2000, optional=True),
    'flip_arrow_1': DXFAttr(74, dxfversion=DXF2000, optional=True),
    'flip_arrow_2': DXFAttr(75, dxfversion=DXF2000, optional=True),
    'text': DXFAttr(1, default='', optional=True),  # Dimension text explicitly entered by the user
    # default is the measurement.
    # If null or “<>”, the dimension measurement is drawn as the text,
    # if “ “ (one blank space), the text is suppressed.
    # Anything else is drawn as the text.
    'oblique_angle': DXFAttr(52, default=0, optional=True),
    # Linear dimension types with an oblique angle have an optional group
    # code 52. When added to the rotation angle of the linear dimension (group code 50), it gives the angle of the
    # extension lines (DXF reference error: false subclass AcDbAlignedDimension)
    'text_rotation': DXFAttr(53, default=0, optional=True),
    # The optional group code 53 is the rotation angle of the dimension
    # text away from its default orientation (the direction of the dimension line) (optional)
    'horizontal_direction': DXFAttr(51, default=0, optional=True),
    # All dimension types have an optional 51 group code, which
    # indicates the horizontal direction for the dimension entity. The dimension entity determines the orientation of
    # dimension text and lines for horizontal, vertical, and rotated linear dimensions. This group value is the negative
    # of the angle between the OCS X axis and the UCS X axis. It is always in the XY plane of the OCS
    'extrusion': DXFAttr(210, xtype=XType.point3d, default=Vector(0, 0, 1), optional=True),
})

acdb_dimension_dummy = DefSubclass('AcDbDimensionDummy', {
    'defpoint2': DXFAttr(13, xtype=XType.point3d, default=Vector(0, 0, 0)),
    # Definition point for linear and angular dimensions (in WCS)
    'defpoint3': DXFAttr(14, xtype=XType.point3d, default=Vector(0, 0, 0)),
    # Definition point for linear and angular dimensions (in WCS)
    # The defpoint2 (13,23,33) specifies the start point of the first extension line and
    # the defpoint3 (14,24,34) specifies the start point of the second extension line.
    # Defpoint (10,20,30) specifies the dimension line location. The text_midpoint (11,21,31)
    # specifies the midpoint of the dimension text.
    'angle': DXFAttr(50, default=0),  # Angle of rotated, horizontal, or vertical dimensions
    'defpoint4': DXFAttr(15, xtype=XType.point3d, default=Vector(0, 0, 0)),
    # Definition point for diameter, radius, and angular dimensions (in WCS)
    'leader_length': DXFAttr(40),  # Leader length for radius and diameter dimensions
    'defpoint5': DXFAttr(16, xtype=XType.point3d, default=Vector(0, 0, 0)),
    # Point defining dimension arc for angular dimensions (in OCS)
    # The defpoint2 (13,23,33) and defpoint3 (14,24,34) specify the endpoints of the line used to determine the first
    # extension line. Defpoint (10,20,30) and defpoint4 (15,25,35) specify the endpoints of the line used to determine
    # the second extension line. Defpoint5 (16,26,36) specifies the location of the dimension line arc.
    # The text_midpoint (11,21,31) specifies the midpoint of the dimension text.
})


class OverrideMixin:
    def get_dim_style(self) -> 'DimStyle':
        """ Returns the associated :class:`DimStyle` entity. """
        if self.doc is None:
            raise DXFInternalEzdxfError('Dimension.drawing attribute not initialized.')

        dim_style_name = self.dxf.dimstyle
        # raises ValueError if not exists, but all used dim styles should exists!
        return self.doc.dimstyles.get(dim_style_name)

    def dim_style_attributes(self) -> 'DXFAttributes':
        """ Returns all valid DXF attributes (internal API). """
        return self.get_dim_style().DXFATTRIBS

    def dim_style_attr_names_to_handles(self, data: dict, dxfversion: str) -> dict:
        """
        `ezdxf` uses internally only resource names for arrows, line types and text styles, but
        DXF 2000 and later requires handles for these resources, this method translates resource names
        into related handles. (e.g. 'dimtxsty': 'FancyStyle' -> 'dimtxsty_handle', <handle of FancyStyle>)

        Args:
            data: dictionary of overridden DimStyle attributes as names (ezdxf)
            dxfversion: target DXF version

        Returns: dictionary with resource names replaced by handles

        Raises:
            DXFTableEntry: text style or line type does not exist
            DXFKeyError: referenced block does not exist

        (internal API)

        """
        data = dict(data)  # shallow copy dict
        blocks = self.doc.blocks

        def set_arrow_handle(attrib_name, block_name):
            attrib_name += '_handle'
            if block_name in ARROWS:  # create all arrows on demand
                block_name = ARROWS.create_block(blocks, block_name)
            if block_name == '_CLOSEDFILLED':  # special arrow
                handle = '0'  # set special #0 handle for closed filled arrow
            else:
                block = blocks[block_name]
                handle = block.block_record_handle
            data[attrib_name] = handle

        def set_linetype_handle(attrib_name, linetype_name):
            try:
                ltype = self.doc.linetypes.get(linetype_name)
            except DXFTableEntryError:
                logger.info('Required line type "{}" does not exist.'.format(linetype_name))
            else:
                data[attrib_name + '_handle'] = ltype.dxf.handle

        if dxfversion > DXF12:
            # transform block names into block record handles
            for attrib_name in ('dimblk', 'dimblk1', 'dimblk2', 'dimldrblk'):
                try:
                    block_name = data.pop(attrib_name)
                except KeyError:
                    pass
                else:
                    set_arrow_handle(attrib_name, block_name)

            # replace 'dimtxsty' attribute by 'dimtxsty_handle'
            try:
                dimtxsty = data.pop('dimtxsty')
            except KeyError:
                pass
            else:
                txtstyle = self.doc.styles.get(dimtxsty)
                data['dimtxsty_handle'] = txtstyle.dxf.handle

        if dxfversion >= DXF2007:
            # transform linetype names into LTYPE entry handles
            for attrib_name in ('dimltype', 'dimltex1', 'dimltex2'):
                try:
                    linetype_name = data.pop(attrib_name)
                except KeyError:
                    pass
                else:
                    set_linetype_handle(attrib_name, linetype_name)
        return data

    def set_acad_dstyle(self, data: dict) -> None:
        """ Set XDATA section ACAD:DSTYLE, to override DIMSTYLE attributes for this DIMENSION entity.

        Args:
            data: ``dict`` with DIMSTYLE attribute names as keys.

        (internal API)
        """
        if self.doc is None:
            raise DXFInternalEzdxfError('Dimension.doc attribute not initialized.')

        # ezdxf uses internally only resource names for arrows, line types and text styles, but
        # DXF 2000 and later requires handles for these resources
        actual_dxfversion = self.doc.dxfversion
        data = self.dim_style_attr_names_to_handles(data, actual_dxfversion)
        tags = []
        dim_style_attributes = self.dim_style_attributes()
        for key, value in data.items():
            if key not in dim_style_attributes:  # ignore unknown attributes, but log
                logging.debug('Ignore unknown DIMSTYLE attribute: "{}"'.format(key))
                continue
            dxf_attr = dim_style_attributes.get(key)
            if dxf_attr and dxf_attr.code > 0:  # skip internal and virtual tags
                if dxf_attr.dxfversion > actual_dxfversion:
                    logging.debug(
                        'Unsupported DIMSTYLE attribute "{}" for DXF version {}'.format(key, self.doc.acad_release))
                    continue
                code = dxf_attr.code
                tags.append((1070, code))
                if code == 5:  # DimStyle 'dimblk' has group code 5 but is not a handle
                    tags.append((1000, value))
                else:
                    tags.append((get_xcode_for(code), value))

        if len(tags):
            self.set_xdata_list('ACAD', 'DSTYLE', tags)

    def dim_style_attr_handles_to_names(self, data: dict) -> dict:
        """
        `ezdxf` uses internally only resource names for arrows, line types and text styles, but
        DXF 2000 and later requires handles for these resources, this method translates resource handles
        into related names. (e.g. 'dimtxsty_handle', <handle of FancyStyle> -> 'dimtxsty': 'FancyStyle')

        Args:
            data: dictionary of overridden DimStyle attributes as handles (DXF2000)

        Returns: dictionary with resource as handles replaced by names

        Raises:
            DXFTableEntry: text style or line type does not exist
            DXFKeyError: referenced block does not exist

        (internal API)
        """
        data = dict(data)  # shallow copy dict
        db = self.doc.entitydb

        def set_arrow_name(attrib_name: str, handle: str):
            if handle == '0':  # special handle for default arrow CLOSEDFILLED
                data[attrib_name] = ''  # special name for default arrow CLOSEDFILLED
                return
            try:
                block_record = db[handle]
            except KeyError:
                logger.info(
                    'Required arrow block #{} does not exist, ignoring {} override.'.format(handle, attrib_name.upper())
                )
                return
            name = block_record.dxf.name
            if name.startswith('_'):  # translate block name into ACAD standard name _OPEN30 -> OPEN30
                acad_arrow_name = name[1:]
                if ARROWS.is_acad_arrow(acad_arrow_name):
                    name = acad_arrow_name
            data[attrib_name] = name

        def set_ltype_name(attrib_name: str, handle: str):
            try:
                ltype = db[handle]
            except KeyError:
                logger.info(
                    'Required line type #{} does not exist, ignoring {} override.'.format(handle, attrib_name.upper())
                )
            else:
                data[attrib_name] = ltype.dxf.name

        # transform block record handles into block names
        for attrib_name in ('dimblk', 'dimblk1', 'dimblk2', 'dimldrblk'):
            try:
                blkrec_handle = data.pop(attrib_name + '_handle')
            except KeyError:
                pass
            else:
                set_arrow_name(attrib_name, blkrec_handle)

        # replace 'dimtxsty_handle' attribute by 'dimtxsty_handle'
        try:
            dimtxsty_handle = data.pop('dimtxsty_handle')
        except KeyError:
            pass
        else:
            try:
                txtstyle = db[dimtxsty_handle]
            except KeyError:
                logger.info(
                    'Required text style #{} does not exist, ignoring DIMTXSTY override.'.format(dimtxsty_handle)
                )
            else:
                data['dimtxsty'] = txtstyle.dxf.name

        # transform linetype handles into LTYPE entry names
        for attrib_name in ('dimltype', 'dimltex1', 'dimltex2'):
            try:
                handle = data.pop(attrib_name + '_handle')
            except KeyError:
                pass
            else:
                set_ltype_name(attrib_name, handle)
        return data

    def get_acad_dstyle(self, dim_style: 'DimStyle') -> dict:
        """ Get XDATA section ACAD:DSTYLE, to override DIMSTYLE attributes for this DIMENSION entity.
        Returns a ``dict`` with DIMSTYLE attribute names as keys.

        (internal API)
        """
        try:
            data = self.get_xdata_list('ACAD', 'DSTYLE')
        except DXFValueError:
            return {}
        attribs = {}
        codes = dim_style.CODE_TO_DXF_ATTRIB
        for code_tag, value_tag in take2(data):
            group_code = code_tag.value
            value = value_tag.value
            if group_code in codes:
                attribs[codes[group_code]] = value
        return self.dim_style_attr_handles_to_names(attribs)


@register_entity
class Dimension(DXFGraphic, OverrideMixin):
    """ DXF DIMENSION entity """
    DXFTYPE = 'DIMENSION'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_dimension, acdb_dimension_dummy)
    LINEAR = 0
    ALIGNED = 1
    ANGULAR = 2
    DIAMETER = 3
    RADIUS = 4
    ANGULAR_3P = 5
    ORDINATE = 6
    ARC = 8
    ORDINATE_TYPE = 64
    USER_LOCATION_OVERRIDE = 128

    # WARNING for destroy() method:
    # Do not destroy associated anonymous block, if DIMENSION is used in a block, the anonymous block may
    # be used by several block references.

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_dimension)
            if len(tags) and not processor.r12:
                processor.log_unprocessed_tags(tags, subclass=acdb_dimension.name)
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_dimension_dummy, index=3)
            # ignore possible 5. subclass AcDbRotatedDimension, has no content
            if len(tags) and not processor.r12:
                processor.log_unprocessed_tags(tags, subclass=acdb_dimension_dummy.name)

        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        if tagwriter.dxfversion == DXF12:
            self.dxf.export_dxf_attribs(tagwriter, [
                'geometry', 'dimstyle', 'defpoint', 'text_midpoint', 'insert', 'dimtype', 'text', 'defpoint2',
                'defpoint3', 'defpoint4', 'defpoint5', 'leader_length', 'angle', 'horizontal_direction',
                'oblique_angle', 'text_rotation'
            ])
            return

        # else DXF2000+
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_dimension.name)
        dim_type = self.dimtype
        self.dxf.export_dxf_attribs(tagwriter, [
            'version', 'geometry', 'dimstyle', 'defpoint', 'text_midpoint', 'insert', 'dimtype', 'attachment_point',
            'line_spacing_style', 'line_spacing_factor', 'actual_measurement', 'unknown1', 'flip_arrow_1',
            'flip_arrow_2', 'text', 'oblique_angle', 'text_rotation', 'horizontal_direction', 'extrusion',
        ])

        if dim_type == 0:  # linear
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbAlignedDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint2', 'defpoint3', 'angle'])
            # empty but required subclass
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbRotatedDimension')
        elif dim_type == 1:  # aligned
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbAlignedDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint2', 'defpoint3', 'angle'])
        elif dim_type == 2:  # angular & angular3p
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDb2LineAngularDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint2', 'defpoint3', 'defpoint4', 'defpoint5'])
        elif dim_type == 3:  # diameter
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbDiametricDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint4', 'leader_length'])
        elif dim_type == 4:  # radius
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbRadialDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint4', 'leader_length'])
        elif dim_type == 5:  # angular & angular3p
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDb3PointAngularDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint2', 'defpoint3', 'defpoint4', 'defpoint5'])
        elif dim_type == 6:  # ordinate
            tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbOrdinateDimension')
            self.dxf.export_dxf_attribs(tagwriter, ['defpoint2', 'defpoint3'])

    @property
    def dimtype(self) -> int:
        """ :attr:`dxf.dimtype` without binary flags (32, 62, 128). """
        # ARC_DIMENSION = 8
        return self.dxf.dimtype & 15

    def get_geometry_block(self) -> Optional['BlockLayout']:
        """
        Returns :class:`~ezdxf.layouts.BlockLayout` of associated anonymous dimension block, which contains the
        entities that make up the dimension picture. Returns ``None`` if block name is not set or the BLOCK itself
        does not exist

        .. versionadded:: 0.10

        """
        block_name = self.get_dxf_attrib('geometry', None)
        return self.doc.blocks.get(block_name)

    def get_measurement(self) -> Union[float, Vector]:
        """ Returns the actual dimension measurement in :ref:`WCS` units, no scaling applied for linear dimensions.
        Returns angle in degrees for angular dimension from 2 lines and angular dimension from 3 points.
        Returns vector from origin to feature location for ordinate dimensions.

        .. versionadded:: 0.10.2

        .. versionchanged:: 0.11

            Added support for angular and ordinate dimensions.

        """

        def angle_between(v1: Vector, v2: Vector) -> float:
            angle = v2.angle_deg - v1.angle_deg
            return angle + 360 if angle < 0 else angle

        if self.dimtype in (0, 1):  # linear, aligned
            return linear_measurement(
                self.dxf.defpoint2,
                self.dxf.defpoint3,
                math.radians(self.dxf.get('angle', 0)),
                self.ocs(),
            )
        elif self.dimtype in (3, 4):  # diameter, radius
            p1 = Vector(self.dxf.defpoint)
            p2 = Vector(self.dxf.defpoint4)
            return (p2 - p1).magnitude
        elif self.dimtype == 2:  # angular from 2 lines
            p1 = Vector(self.dxf.defpoint2)  # 1. point of 1. extension line
            p2 = Vector(self.dxf.defpoint3)  # 2. point of 1. extension line
            p3 = Vector(self.dxf.defpoint4)  # 1. point of 2. extension line
            p4 = Vector(self.dxf.defpoint)  # 2. point of 2. extension line
            dir1 = p2 - p1  # direction of 1. extension line
            dir2 = p4 - p3  # direction of 2. extension line
            return angle_between(dir1, dir2)
        elif self.dimtype == 5:  # angular from 2 lines
            p1 = Vector(self.dxf.defpoint4)  # center
            p2 = Vector(self.dxf.defpoint2)  # 1. extension line
            p3 = Vector(self.dxf.defpoint3)  # 2. extension line
            dir1 = p2 - p1  # direction of 1. extension line
            dir2 = p3 - p1  # direction of 2. extension line
            return angle_between(dir1, dir2)
        elif self.dimtype == 6:  # ordinate
            origin = Vector(self.dxf.defpoint)
            feature_location = Vector(self.dxf.defpoint2)
            return feature_location - origin
        else:
            logger.debug("get_measurement() - unknown DIMENSION type {}.".format(self.dimtype))
            return 0

    def override(self) -> 'DimStyleOverride':
        """ Returns the :class:`~ezdxf.entities.DimStyleOverride` object.

        .. versionadded:: 0.12

        """
        return DimStyleOverride(self)

    def render(self) -> None:
        """ Render graphical representation as anonymous block.

        .. versionadded:: 0.12

        """
        # todo: delete existing anonymous block?
        self.override().render()

    def transform_to_wcs(self, ucs: 'UCS') -> 'Dimension':
        """ Transform DIMENSION entity from local :class:`~ezdxf.math.UCS` coordinates to :ref:`WCS` coordinates.

        Does not transform the graphical representation in the anonymous block!

        .. versionadded:: 0.12

        """
        # Transform existing OCS points and angles
        dxf = self.dxf
        vector_names = [
            name for name in ['text_midpoint', 'defpoint5', 'insert'] if dxf.hasattr(name)
        ]
        angle_names = [
            name for name in ['text_rotation', 'horizontal_direction', 'angle'] if dxf.hasattr(name)
        ]
        self._ucs_and_ocs_transformation(ucs, vector_names=vector_names, angle_names=angle_names)

        # Transform existing WCS points
        for name in ['defpoint', 'defpoint2', 'defpoint3', 'defpoint4']:
            if dxf.hasattr(name):
                dxf.set(name, ucs.to_wcs(dxf.get(name)))
        return self

    def virtual_entities(self) -> Iterable['DXFGraphic']:
        """
        Yields 'virtual' parts of DIMENSION as basic DXF entities like LINE, ARC or TEXT.

        This entities are located at the original positions, but are not stored in the entity database, have no handle
        and are not assigned to any layout.

        .. versionadded:: 0.12

        """
        block = self.get_geometry_block()
        if block is not None:
            for entity in block:
                try:
                    yield entity.copy()
                except DXFTypeError:
                    pass

    def explode(self, target_layout: 'BaseLayout' = None) -> 'EntityQuery':
        """
        Explode parts of DIMENSION as basic DXF entities like LINE, ARC or TEXT into target layout,
        if target layout is ``None``, the target layout is the layout of the DIMENSION.

        Returns an :class:`~ezdxf.query.EntityQuery` container with all DXF parts.

        Args:
            target_layout: target layout for DXF parts, ``None`` for same layout as source entity.

        .. versionadded:: 0.12

        """
        return explode_entity(self, target_layout)


acdb_arc_dimension = DefSubclass('AcDbArcDimension', {
    'ext_line1_point': DXFAttr(13, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'ext_line2_point': DXFAttr(14, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'arc_center': DXFAttr(15, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'start_angle': DXFAttr(40),  # radians?
    'end_angle': DXFAttr(41),  # radians?
    'is_partial': DXFAttr(70),
    'has_leader': DXFAttr(71),
    'leader_point1': DXFAttr(16, xtype=XType.point3d, default=Vector(0, 0, 0)),
    'leader_point2': DXFAttr(17, xtype=XType.point3d, default=Vector(0, 0, 0)),
})


@register_entity
class ArcDimension(Dimension):
    """ DXF ARC_DIMENSION entity """
    DXFTYPE = 'ARC_DIMENSION'
    DXFATTRIBS = DXFAttributes(base_class, acdb_entity, acdb_dimension, acdb_arc_dimension)
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        # skip Dimension loader
        dxf = super(Dimension, self).load_dxf_attribs(processor)
        if processor:
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_dimension)
            if len(tags) and not processor.r12:
                processor.log_unprocessed_tags(tags, subclass=acdb_dimension.name)
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_arc_dimension, index=3)
            if len(tags) and not processor.r12:
                processor.log_unprocessed_tags(tags, subclass=acdb_arc_dimension.name)
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        """ Export entity specific data as DXF tags. """
        super().export_entity(tagwriter)
        tagwriter.write_tag2(SUBCLASS_MARKER, 'AcDbArcDimension')
        self.dxf.export_dxf_attribs(tagwriter, [
            'ext_line1_point', 'ext_line2_point', 'arc_center', 'start_angle', 'end_angle',
            'is_partial', 'has_leader', 'leader_point1', 'leader_point2',
        ])

    def transform_to_wcs(self, ucs: 'UCS') -> 'Dimension':
        super().transform_to_wcs(ucs)
        self._ucs_and_ocs_transformation(ucs, vector_names=[], angle_names=['start_angle', 'end_angle'])
        dxf = self.dxf
        for name in ['leader_point1', 'leader_point2']:
            if dxf.hasattr(name):
                dxf.set(name, ucs.to_wcs(dxf.get(name)))
        return self


# todo: DIMASSOC
acdb_dim_assoc = DefSubclass('AcDbDimAssoc', {
    'dimension': DXFAttr(330),  # handle of dimension object
    'point_flag': DXFAttr(90),  # Associativity flag (bit-coded)
    # 1 = First point reference
    # 2 = Second point reference
    # 4 = Third point reference
    # 8 = Fourth point reference
    'trans_space': DXFAttr(70),  # Trans-space flag (true/false)
    'rotated_dim_type': DXFAttr(71),  # Rotated Dimension type (parallel, perpendicular)
    # Autodesk gone crazy: subclass AcDbOsnapPointRef with group code 1!!!!!
    #  }), DefSubclass('AcDbOsnapPointRef', {
    'osnap_type': DXFAttr(72),  # Object Osnap type
    # 0 = None
    # 1 = Endpoint
    # 2 = Midpoint
    # 3 = Center
    # 4 = Node
    # 5 = Quadrant
    # 6 = Intersection
    # 7 = Insertion
    # 8 = Perpendicular
    # 9 = Tangent
    # 10 = Nearest
    # 11 = Apparent intersection
    # 12 = Parallel
    # 13 = Start point
    'object_id': DXFAttr(331),  # ID of main object (geometry)
    'object_subtype': DXFAttr(73),  # Subtype of main object (edge, face)
    'object_gs_marker': DXFAttr(91),  # GsMarker of main object (index)
    'object_xref_id': DXFAttr(301),  # Handle (string) of Xref object
    'near_param': DXFAttr(40),  # Geometry parameter for Near Osnap
    'osnap_point': DXFAttr(10, xtype=XType.point3d),  # Osnap point in WCS
    'intersect_id': DXFAttr(332),  # ID of intersection object (geometry)
    'intersect_subtype': DXFAttr(74),  # Subtype of intersection object (edge/face)
    'intersect_gs_marker': DXFAttr(92),  # GsMarker of intersection object (index)
    'intersect_xref_id': DXFAttr(302),  # Handle (string) of intersection Xref object
    'has_last_point_ref': DXFAttr(75),  # hasLastPointRef flag (true/false)
})


def linear_measurement(p1: Vector, p2: Vector, angle: float = 0, ocs: 'OCS' = None) -> float:
    """ Returns distance from `p1` to `p2` projected onto ray defined by `angle`, `angle` in radians in the xy-plane.
    """
    if ocs is not None and ocs.uz != (0, 0, 1):
        p1 = ocs.to_wcs(p1)
        p2 = ocs.to_wcs(p2)
        # angle in OCS xy-plane
        ocs_direction = Vector.from_angle(angle)
        measurement_direction = ocs.to_wcs(ocs_direction)
    else:
        # angle in WCS xy-plane
        measurement_direction = Vector.from_angle(angle)

    t1 = measurement_direction.project(p1)
    t2 = measurement_direction.project(p2)
    return (t2 - t1).magnitude
