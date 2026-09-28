from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_mapping_registry import P6MappingDefinition,P6MappingFormat,P6MappingStatus,PersistedP6Mapping
from construction_pm.p6_msproject_xml_codec import P6MsProjectXmlCodec

def test_msproject_adapter_integration():
    s=BackendScope(tenant_id="t1",project_id="p1",project_revision=4)
    m=PersistedP6Mapping(scope=s,definition=P6MappingDefinition(mapping_id="activity.code",registry_version="p6-field-registry.v1",format=P6MappingFormat.MSPROJECT_XML,subject_area="Activity",source_field="UID",canonical_field="activity.code",status=P6MappingStatus.SUPPORTED))
    a=P6InterchangeAdapter(mapper=P6InterchangeMapper((m,)),codec=P6MsProjectXmlCodec())
    imported=a.import_document("<Project><Tasks><Task><UID>1</UID><Name>Foundation</Name></Task></Tasks></Project>",scope=s)
    assert imported[0].values=={"activity.code":"1"}
    assert imported[0].extensions["p6.interchange.t1.p1.Name"]=="Foundation"
