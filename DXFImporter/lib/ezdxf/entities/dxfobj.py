# Copyright (c) 2019 Manfred Moitzi
# License: MIT License
# Created 2019-02-13
#
# DXFObject - non graphical entities stored in OBJECTS section
from typing import TYPE_CHECKING, Iterable, Dict, Tuple
import logging
import array
from ezdxf.lldxf.const import DXF2000, DXFStructureError, SUBCLASS_MARKER
from ezdxf.lldxf.tags import Tags
from ezdxf.lldxf.types import dxftag, DXFTag, DXFBinaryTag
from ezdxf.lldxf.attributes import DXFAttr, DXFAttributes, DefSubclass
from ezdxf.tools import take2
from .dxfentity import DXFEntity, base_class, SubclassProcessor
from .factory import register_entity

logger = logging.getLogger('ezdxf')
if TYPE_CHECKING:
    from ezdxf.eztypes import Auditor, Drawing, DXFNamespace, TagWriter

__all__ = ['DXFObject', 'Placeholder', 'XRecord', 'VBAProject', 'SortEntsTable', 'Field']


class DXFObject(DXFEntity):
    MIN_DXF_VERSION_FOR_EXPORT = DXF2000

    def audit(self, auditor: 'Auditor') -> None:
        """ Validity check. (internal API) """
        super().audit(auditor)
        self.check_owner(auditor)

    def check_owner(self, auditor: 'Auditor') -> None:
        # overridden in DICTIONARY
        auditor.check_owner_exist(self)


@register_entity
class Placeholder(DXFObject):
    DXFTYPE = 'ACDBPLACEHOLDER'


acdb_xrecord = DefSubclass('AcDbXrecord', {
    'cloning': DXFAttr(280, default=1),
    # 0 = not applicable
    # 1 = keep existing
    # 2 = use clone
    # 3 = <xref>$0$<name>
    # 4 = $0$<name>
    # 5 = Unmangle name
})


def totags(tags: Iterable) -> Iterable[DXFTag]:
    for tag in tags:
        if isinstance(tag, DXFTag):
            yield tag
        else:
            yield dxftag(tag[0], tag[1])


@register_entity
class XRecord(DXFObject):
    """ DXF XRECORD entity """
    DXFTYPE = 'XRECORD'
    DXFATTRIBS = DXFAttributes(base_class, acdb_xrecord)

    def __init__(self, doc: 'Drawing' = None):
        super().__init__(doc)
        self.tags = Tags()

    def _copy_data(self, entity: 'XRecord') -> None:
        entity.tags = Tags(entity.tags)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            try:
                tags = processor.subclasses[1]
            except IndexError:
                raise DXFStructureError('Missing subclass AcDbXrecord in XRecord (#{})'.format(dxf.handle))
            start_index = 1
            if len(tags) > 1:
                # first tag is group code 280, but not for DXF R13/R14
                # for testing doc may be None, but then doc also can not be R13/R14 - ezdxf does not create R13/R14
                if self.doc is None or self.doc.dxfversion >= DXF2000:
                    code, value = tags[1]
                    if code == 280:
                        dxf.cloning = value
                        start_index = 2
                    else:  # just log recoverable error
                        logger.info(
                            'XRecord (#{}): expected group code 280 as first tag in AcDbXrecord'.format(dxf.handle)
                        )
            self.tags = Tags(tags[start_index:])
        return dxf

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_xrecord.name)
        tagwriter.write_tag2(280, self.dxf.cloning)
        tagwriter.write_tags(Tags(totags(self.tags)))


acdb_vba_project = DefSubclass('AcDbVbaProject', {
    # 90: Number of bytes of binary chunk data (contained in the group code 310 records that follow)
    # 310: DXF: Binary object data (multiple entries containing VBA project data)
})


@register_entity
class VBAProject(DXFObject):
    """ DXF VBA_PROJECT entity """
    DXFTYPE = 'VBA_PROJECT'
    DXFATTRIBS = DXFAttributes(base_class, acdb_vba_project)

    def __init__(self, doc: 'Drawing' = None):
        super().__init__(doc)
        self.data = b''

    def _copy_data(self, entity: 'VBAProject') -> None:
        entity.tags = Tags(entity.tags)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            self.load_byte_data(processor.subclasses[1])
        return dxf

    def load_byte_data(self, tags: 'Tags') -> None:
        byte_array = array.array('B')
        for byte_data in (tag.value for tag in tags if tag.code == 310):
            byte_array.extend(byte_data)
        self.data = byte_array.tobytes()

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_vba_project.name)
        tagwriter.write_tag2(90, len(self.data))
        self.export_data(tagwriter)

    def export_data(self, tagwriter: 'TagWriter'):
        data = self.data
        while data:
            tagwriter.write_tag(DXFBinaryTag(310, data[:127]))
            data = data[127:]

    def clear(self) -> None:
        self.data = b''


acdb_sort_ents_table = DefSubclass('AcDbSortentsTable', {
    'block_record_handle': DXFAttr(330),
    # Soft-pointer ID/handle to owner (currently only the *MODEL_SPACE or *PAPER_SPACE blocks)
    # in ezdxf the block_record handle for a layout is also called layout_key
    # 331: Soft-pointer ID/handle to an entity (zero or more entries may exist)
    #   5: Sort handle (zero or more entries may exist)
})


@register_entity
class SortEntsTable(DXFObject):
    """ DXF VBA_PROJECT entity """
    # should work with AC1015/R2000 but causes problems with TrueView/AutoCAD LT 2019: "expected was-a-zombie-flag"
    # No problems with AC1018/R2004 and later
    #
    # If the header variable $SORTENTS Regen flag (bit-code value 16) is set, AutoCAD regenerates entities in ascending
    # handle order.
    #
    # When the DRAWORDER command is used, a SORTENTSTABLE object is attached to the *Model_Space or *Paper_Space block's
    # extension dictionary under the name ACAD_SORTENTS. The SORTENTSTABLE object related to this dictionary associates
    # a different handle with each entity, which redefines the order in which the entities are regenerated.
    #
    # $SORTENTS (280): Controls the object sorting methods (bitcode):
    # 0 = Disables SORTENTS
    # 1 = Sorts for object selection
    # 2 = Sorts for object snap
    # 4 = Sorts for redraws; obsolete
    # 8 = Sorts for MSLIDE command slide creation; obsolete
    # 16 = Sorts for REGEN commands
    # 32 = Sorts for plotting
    # 64 = Sorts for PostScript output; obsolete

    DXFTYPE = 'SORTENTSTABLE'
    DXFATTRIBS = DXFAttributes(base_class, acdb_sort_ents_table)

    def __init__(self, doc: 'Drawing' = None):
        super().__init__(doc)
        self.table = dict()  # type: Dict[str, str]

    def _copy_data(self, entity: 'SortEntsTable') -> None:
        entity.tags = dict(entity.table)

    def load_dxf_attribs(self, processor: SubclassProcessor = None) -> 'DXFNamespace':
        dxf = super().load_dxf_attribs(processor)
        if processor:
            tags = processor.load_dxfattribs_into_namespace(dxf, acdb_sort_ents_table)
            self.load_table(tags)
        return dxf

    def load_table(self, tags: 'Tags') -> None:
        for handle, sort_handle in take2(tags):
            if handle.code != 331:
                raise DXFStructureError('Invalid handle code {}, expected 331'.format(handle.code))
            if sort_handle.code != 5:
                raise DXFStructureError('Invalid sort handle code {}, expected 5'.format(handle.code))
            self.table[handle.value] = sort_handle.value

    def export_entity(self, tagwriter: 'TagWriter') -> None:
        # base class export is done by parent class
        super().export_entity(tagwriter)
        # AcDbEntity export is done by parent class
        tagwriter.write_tag2(SUBCLASS_MARKER, acdb_sort_ents_table.name)
        tagwriter.write_tag2(330, self.dxf.block_record_handle)
        self.export_table(tagwriter)

    def export_table(self, tagwriter: 'TagWriter'):
        for handle, sort_handle in self.table.items():
            tagwriter.write_tag2(331, handle)
            tagwriter.write_tag2(5, sort_handle)

    def __len__(self) -> int:
        return len(self.table)

    def __iter__(self) -> Iterable:
        """
        Yields all redraw associations as (object_handle, sort_handle) tuples.

        """
        return iter(self.table.items())

    def append(self, handle: str, sort_handle: str) -> None:
        """
        Append redraw association (handle, sort_handle).

        Args:
            handle: DXF entity handle (uppercase hex value without leading '0x')
            sort_handle: sort handle (uppercase hex value without leading '0x')

        """
        self.table[handle] = sort_handle

    def clear(self):
        """
        Remove all handles from redraw order table.

        """
        self.table = dict()

    def set_handles(self, handles: Iterable[Tuple[str, str]]) -> None:
        """
        Set all redraw associations from iterable `handles`, after removing all existing associations.

        Args:
            handles: iterable yielding (object_handle, sort_handle) tuples

        """
        # The sort_handle doesn't have to be unique, same or all handles can share the same sort_handle and sort_handles
        # can use existing handles too.
        #
        # The '0' handle can be used, but this sort_handle will be drawn as latest (on top of all other entities) and
        # not as first as expected. Invalid entity handles will be ignored by AutoCAD.
        self.table = dict(handles)

    def remove_invalid_handles(self) -> None:
        """
        Remove all handles which do not exists in the drawing database.

        """
        entitydb = self.doc.entitydb
        self.table = {handle: sort_handle for handle, sort_handle in self.table.items() if handle in entitydb}

    def remove_handle(self, handle: str) -> None:
        """
        Remove handle of DXF entity from redraw order table.

        Args:
            handle: DXF entity handle (uppercase hex value without leading '0x')

        """
        try:
            del self.table[handle]
        except KeyError:
            pass


acdb_field = DefSubclass('AcDbField', {
    'evaluator_id': DXFAttr(1),
    'field_code': DXFAttr(2),
    'field_code_overflow': DXFAttr(3),  # Overflow of field code string
    'n_child_fields': DXFAttr(90),  # Number of child fields
    # 360:  Child field ID (AcDbHardOwnershipId); repeats for number of children
    #  97:  Number of object IDs used in the field code
    # 331:  Object ID used in the field code (AcDbSoftPointerId); repeats for the number of object IDs used in the field code
    #  93:  Number of the data set in the field
    #   6:  Key string for the field data; a key-field pair is repeated for the number of data sets in the field
    #   7:  Key string for the evaluated cache; this key is hard-coded as ACFD_FIELD_VALUE
    #  90:  Data type of field value
    #  91:  Long value (if data type of field value is long)
    # 140:  Double value (if data type of field value is double)
    # 330:  ID value, AcDbSoftPointerId (if data type of field value is ID)
    #  92:  Binary data buffer size (if data type of field value is binary)
    # 310:  Binary data (if data type of field value is binary)
    # 301:  Format string
    #   9:  Overflow of Format string
    #  98:  Length of format string

})


# todo: implement FIELD
# register when done
class Field(DXFObject):
    """ DXF FIELD entity """
    DXFTYPE = 'FIELD'
    DXFATTRIBS = DXFAttributes(base_class, acdb_field)
