import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_mapping_registry import P6MappingFormat
from construction_pm.p6_primavera_xml_codec import P6PrimaveraXmlCodec, P6PrimaveraXmlCodecError
def scope(): return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)
def test_decode_flat_xml():
    doc='<APIBusinessObjects xmlns="http://xmlns.oracle.com/Primavera/P6/API/BusinessObjects"><Activity><ObjectId>100</ObjectId><Id>A-10</Id><Name>Foundation</Name></Activity></APIBusinessObjects>'
    rows=P6PrimaveraXmlCodec().decode(doc,scope())
    assert rows[0].format is P6MappingFormat.PRIMAVERA_XML
    assert rows[0].values == {"ObjectId":"100","Id":"A-10","Name":"Foundation"}
    assert rows[0].extensions["p6.primavera.xml.object"]=="Activity"
def test_rejects_wrong_root_and_duplicate_field():
    with pytest.raises(P6PrimaveraXmlCodecError,match="INVALID_P6_XML_ROOT"): P6PrimaveraXmlCodec().decode("<NotP6/>",scope())
    doc='<APIBusinessObjects><Activity><Id>A</Id><Id>B</Id></Activity></APIBusinessObjects>'
    with pytest.raises(P6PrimaveraXmlCodecError,match="DUPLICATE_FIELD:Activity:Id"): P6PrimaveraXmlCodec().decode(doc,scope())
def test_rejects_root_level_extension():
    doc='<APIBusinessObjects xmlns:constructionpm="https://constructionpm.example/p6-interchange"><constructionpm:Extensions><constructionpm:Field key="dropped">value</constructionpm:Field></constructionpm:Extensions></APIBusinessObjects>'
    with pytest.raises(P6PrimaveraXmlCodecError,match="ROOT_LEVEL_EXTENSION_NOT_ALLOWED"): P6PrimaveraXmlCodec().decode(doc,scope())
def test_extension_round_trip():
    doc='<APIBusinessObjects><Activity><Id>A-10</Id><constructionpm:Extensions xmlns:constructionpm="https://constructionpm.example/p6-interchange"><constructionpm:Field key="vendor.custom">preserved</constructionpm:Field></constructionpm:Extensions></Activity></APIBusinessObjects>'
    codec=P6PrimaveraXmlCodec(); rows=codec.decode(doc,scope())
    from construction_pm.p6_interchange_mapping import P6InterchangeResult
    encoded=codec.encode((P6InterchangeResult(dict(rows[0].values),dict(rows[0].extensions)),),scope())
    decoded=codec.decode(encoded,scope())
    assert decoded[0].values==rows[0].values and decoded[0].extensions["vendor.custom"]=="preserved"
def test_encode_requires_object():
    from construction_pm.p6_interchange_mapping import P6InterchangeResult
    with pytest.raises(P6PrimaveraXmlCodecError,match="MISSING_P6_XML_OBJECT"):
        P6PrimaveraXmlCodec().encode((P6InterchangeResult({"Id":"A"},{}),),scope())
