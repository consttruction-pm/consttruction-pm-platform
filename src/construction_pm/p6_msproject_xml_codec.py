from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence
from xml.etree import ElementTree as ET
from .backend_p0.models import BackendScope
from .p6_interchange_mapping import P6InterchangeResult, P6InterchangeRow
from .p6_mapping_registry import P6MappingFormat

class P6MsProjectXmlCodecError(ValueError):
    pass

NS="http://schemas.microsoft.com/project/2007"
EXT="https://constructionpm.example/p6-interchange"
COLLECTIONS={"Tasks","Resources","Assignments","Calendars","ExtendedAttributes","OutlineCodes","WBSMasks"}

@dataclass(frozen=True)
class P6MsProjectXmlCodec:
    format:P6MappingFormat=P6MappingFormat.MSPROJECT_XML

    def decode(self,payload:str|bytes,scope:BackendScope)->Sequence[P6InterchangeRow]:
        scope.validate()
        if isinstance(payload,bytes):
            payload=payload.decode("utf-8-sig")
        try: root=ET.fromstring(payload)
        except ET.ParseError as exc: raise P6MsProjectXmlCodecError("INVALID_XML") from exc
        if self._local(root.tag)!="Project":
            raise P6MsProjectXmlCodecError("INVALID_MSPROJECT_ROOT")
        rows=[]
        for collection in root:
            cname=self._local(collection.tag)
            if cname not in COLLECTIONS:
                raise P6MsProjectXmlCodecError(f"UNSUPPORTED_MSPROJECT_COLLECTION:{cname}")
            for obj in collection:
                values={}
                ext={"p6.msproject.xml.collection":cname,"p6.msproject.xml.object":self._local(obj.tag)}
                for child in obj:
                    if self._local(child.tag)=="Extensions" and child.tag.startswith("{"+EXT+"}"):
                        for field in child:
                            key=field.attrib.get("key")
                            if field.tag != "{"+EXT+"}Field" or not key: raise P6MsProjectXmlCodecError("INVALID_EXTENSION_FIELD")
                            ext[key]=field.text or ""
                        continue
                    key=self._local(child.tag)
                    if key in values: raise P6MsProjectXmlCodecError(f"DUPLICATE_FIELD:{cname}:{self._local(obj.tag)}:{key}")
                    values[key]=child.text or ""
                rows.append(P6InterchangeRow(scope=scope,format=self.format,values=values,extensions=ext))
        return tuple(rows)

    def encode(self,rows:Sequence[P6InterchangeResult],scope:BackendScope)->str:
        scope.validate()
        root=ET.Element("Project",{"xmlns":NS,"xmlns:constructionpm":EXT})
        groups={}
        for row in rows:
            collection=row.extensions.get("p6.msproject.xml.collection")
            obj=row.extensions.get("p6.msproject.xml.object")
            if not isinstance(collection,str) or not collection.strip(): raise P6MsProjectXmlCodecError("MISSING_MSPROJECT_COLLECTION")
            if not isinstance(obj,str) or not obj.strip(): raise P6MsProjectXmlCodecError("MISSING_MSPROJECT_OBJECT")
            if collection not in COLLECTIONS: raise P6MsProjectXmlCodecError(f"UNSUPPORTED_MSPROJECT_COLLECTION:{collection}")
            groups.setdefault(collection,[]).append((obj,row))
        for collection,items in groups.items():
            parent=ET.SubElement(root,collection)
            for obj,row in items:
                element=ET.SubElement(parent,obj)
                for field,value in row.values.items(): ET.SubElement(element,field).text=self._stringify(value)
                preserved=[(k,v) for k,v in row.extensions.items() if k not in {"p6.msproject.xml.collection","p6.msproject.xml.object"}]
                if preserved:
                    x=ET.SubElement(element,"{"+EXT+"}Extensions")
                    for key,value in sorted(preserved): ET.SubElement(x,"{"+EXT+"}Field",{"key":key}).text=self._stringify(value)
        return ET.tostring(root,encoding="unicode",short_empty_elements=True)+"\n"

    @staticmethod
    def _local(tag:str)->str:
        return tag.rsplit("}",1)[-1]

    @staticmethod
    def _stringify(value:Any)->str:
        if value is None:return ""
        if isinstance(value,bool):return "true" if value else "false"
        return str(value)

__all__=["P6MsProjectXmlCodec","P6MsProjectXmlCodecError"]
