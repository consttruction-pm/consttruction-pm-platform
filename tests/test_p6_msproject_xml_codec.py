import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_mapping_registry import P6MappingFormat
from construction_pm.p6_msproject_xml_codec import P6MsProjectXmlCodec,P6MsProjectXmlCodecError

def scope(): return BackendScope(tenant_id="t1",project_id="p1",project_revision=4)

def test_decode_tasks_and_resources():
    doc='<Project xmlns="http://schemas.microsoft.com/project/2007"><Tasks><Task><UID>1</UID><Name>Foundation</Name></Task></Tasks><Resources><Resource><UID>2</UID><Name>Crew</Name></Resource></Resources></Project>'
    rows=P6MsProjectXmlCodec().decode(doc,scope())
    assert [r.extensions["p6.msproject.xml.collection"] for r in rows]==["Tasks","Resources"]
    assert rows[0].values=={"UID":"1","Name":"Foundation"}
    assert rows[0].format is P6MappingFormat.MSPROJECT_XML

def test_rejects_root_and_duplicate_field():
    with pytest.raises(P6MsProjectXmlCodecError,match="INVALID_MSPROJECT_ROOT"): P6MsProjectXmlCodec().decode("<NotProject/>",scope())
    doc="<Project><Tasks><Task><UID>1</UID><UID>2</UID></Task></Tasks></Project>"
    with pytest.raises(P6MsProjectXmlCodecError,match="DUPLICATE_FIELD:Tasks:Task:UID"): P6MsProjectXmlCodec().decode(doc,scope())

def test_rejects_unsupported_collection():
    doc="<Project><CustomCollection><Item><UID>99</UID></Item></CustomCollection></Project>"
    with pytest.raises(P6MsProjectXmlCodecError,match="UNSUPPORTED_MSPROJECT_COLLECTION:CustomCollection"):
        P6MsProjectXmlCodec().decode(doc,scope())

def test_extension_round_trip():
    doc='<Project><Tasks><Task><UID>1</UID><constructionpm:Extensions xmlns:constructionpm="https://constructionpm.example/p6-interchange"><constructionpm:Field key="vendor.custom">keep</constructionpm:Field></constructionpm:Extensions></Task></Tasks></Project>'
    codec=P6MsProjectXmlCodec(); rows=codec.decode(doc,scope())
    from construction_pm.p6_interchange_mapping import P6InterchangeResult
    encoded=codec.encode((P6InterchangeResult(dict(rows[0].values),dict(rows[0].extensions)),),scope())
    decoded=codec.decode(encoded,scope())
    assert decoded[0].values==rows[0].values
    assert decoded[0].extensions["vendor.custom"]=="keep"
