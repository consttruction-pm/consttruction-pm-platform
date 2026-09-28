from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_mapping_registry import P6MappingDefinition,P6MappingFormat,P6MappingStatus,PersistedP6Mapping
from construction_pm.p6_primavera_xml_codec import P6PrimaveraXmlCodec
def scope(): return BackendScope(tenant_id="t1",project_id="p1",project_revision=4)
def test_adapter_integration():
    s=scope()
    m=PersistedP6Mapping(scope=s,definition=P6MappingDefinition(mapping_id="activity.code",registry_version="p6-field-registry.v1",format=P6MappingFormat.PRIMAVERA_XML,subject_area="Activity",source_field="Id",canonical_field="activity.code",status=P6MappingStatus.SUPPORTED))
    adapter=P6InterchangeAdapter(mapper=P6InterchangeMapper((m,)),codec=P6PrimaveraXmlCodec())
    imported=adapter.import_document('<APIBusinessObjects><Activity><Id>A-10</Id><Name>Foundation</Name></Activity></APIBusinessObjects>',scope=s)
    assert imported[0].values=={"activity.code":"A-10"}
    assert imported[0].extensions["p6.interchange.t1.p1.Name"]=="Foundation"
