# Created: 2019-02-18
# Copyright (c) 2019, Manfred Moitzi
# License: MIT License
from typing import TYPE_CHECKING, Iterable, Optional, Union
from .base import BaseLayout

if TYPE_CHECKING:
    from ezdxf.eztypes import DXFGraphic, AttDef


class BlockLayout(BaseLayout):
    """
    BlockLayout has the same factory-functions as Layout, but is managed
    in the :class:`BlocksSection` class. It represents a DXF Block.

    """

    def __contains__(self, entity: Union['DXFGraphic', str]) -> bool:
        """ Returns ``True`` if block contains `entity`.

        Args:
             entity: :class:`DXFGraphic` object or handle as hex string

        """
        if isinstance(entity, str):
            entity = self.entitydb[entity]
        return entity in self.entity_space

    @property
    def block(self):
        """ the associated :class:`~ezdxf.entities.Block` entity. """
        return self.block_record.block

    @property
    def endblk(self):
        """ the associated :class:`~ezdxf.entities.EndBlk` entity. """
        return self.block_record.endblk

    @property
    def name(self) -> str:
        """ Get block and block_record name """
        return self.block_record.dxf.name

    @name.setter
    def name(self, new_name) -> None:
        """ Set block and block_record name """
        self.block_record.rename(new_name)

    @property
    def dxf(self):
        """ DXF name space of associated :class:`~ezdxf.entities.BlockRecord` table entry. """
        return self.block_record.dxf

    @property
    def can_explode(self) -> bool:
        """ Set property to ``True`` to allow exploding block references of this block. """
        return bool(self.block_record.dxf.explode)

    @can_explode.setter
    def can_explode(self, value: bool):
        self.block_record.dxf.explode = int(value)

    @property
    def scale_uniformly(self) -> bool:
        """ Set property to ``True`` to allow block references of this block only scale uniformly. """
        return bool(self.block_record.dxf.scale)

    @scale_uniformly.setter
    def scale_uniformly(self, value: bool):
        self.block_record.dxf.scale = int(value)

    def attdefs(self) -> Iterable['AttDef']:
        """ Returns iterable of all :class:`~ezdxf.entities.attrib.Attdef` entities. """
        return (entity for entity in self if entity.dxftype() == 'ATTDEF')

    def has_attdef(self, tag: str) -> bool:
        """ Returns ``True`` if an :class:`~ezdxf.entities.attrib.Attdef` for `tag` exist. """
        return self.get_attdef(tag) is not None

    def get_attdef(self, tag: str) -> Optional['DXFGraphic']:
        """ Returns attached :class:`~ezdxf.entities.attrib.Attdef` entity by `tag` name. """
        for attdef in self.attdefs():
            if tag == attdef.dxf.tag:
                return attdef

    def get_attdef_text(self, tag: str, default: str = None) -> str:
        """
        Returns text content for :class:`~ezdxf.entities.attrib.Attdef` `tag` as string or returns `default` if no
        :class:`Attdef` for `tag` exist.

        Args:
            tag: name of tag
            default: default value if `tag` not exist

        """
        attdef = self.get_attdef(tag)
        if attdef is None:
            return default
        return attdef.dxf.text

    def get_const_attdefs(self) -> Iterable['AttDef']:
        """ Returns iterable for all constant ATTDEF entities. (internal API) """
        return (attdef for attdef in self.attdefs() if attdef.is_const)
