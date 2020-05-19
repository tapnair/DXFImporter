# Copyright (c) 2018 Manfred Moitzi
# License: MIT License
from typing import TYPE_CHECKING, Iterable, cast
from ezdxf.lldxf.const import DXFValueError, DXFKeyError

if TYPE_CHECKING:
    from ezdxf.eztypes import DXFObject, Dictionary, Drawing, ObjectsSection


class ObjectCollection:
    def __init__(self, doc: 'Drawing', dict_name: str = 'ACAD_MATERIAL', object_type: str = 'MATERIAL'):
        self.doc = doc  # type: Drawing
        self.object_type = object_type  # type: str
        self.object_dict = doc.rootdict.get_required_dict(dict_name)  # type: Dictionary

    @property
    def objects(self) -> 'ObjectsSection':
        return self.doc.objects

    def __iter__(self) -> Iterable['DXFObject']:
        return self.object_dict.items()

    def __len__(self) -> int:
        return len(self.object_dict)

    def __contains__(self, name: str) -> bool:
        return name in self.object_dict

    def __getitem__(self, item):
        return self.get(item)

    def get(self, name: str) -> 'DXFObject':
        """
        Get object by name.

        Args:
            name: object name as string

        Raises:
            DXFKeyError: if name does not exist

        """
        return cast('DXFObject', self.object_dict.get(name))

    def new(self, name: str) -> 'DXFObject':
        """
        Create a new object of type `self.object_type` and store its handle in the object manager dictionary.

        Args:
            name: name of new object as string

        Returns:
            new object of type `self.object_type`

        Raises:
            DXFValueError: if object name already exist

        (internal API)

        """
        if name in self.object_dict:
            raise DXFValueError('{} entry {} already exists.'.format(self.object_type, name))
        return self._new(name, dxfattribs={'name': name})

    def _new(self, name: str, dxfattribs: dict) -> 'DXFObject':
        owner = self.object_dict.dxf.handle
        dxfattribs['owner'] = owner
        obj = self.objects.add_dxf_object_with_reactor(self.object_type, dxfattribs=dxfattribs)
        self.object_dict.add(name, obj)
        return cast('DXFObject', obj)

    def delete(self, name: str) -> None:
        try:
            obj = self.object_dict.get(name)
        except DXFKeyError:
            return
        else:
            self.object_dict.discard(name)
            self.objects.delete_entity(obj)

    def clear(self) -> None:
        """
        Delete all entries.

        """
        self.object_dict.clear()
