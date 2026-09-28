from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_mapping_registry import P6MappingDefinition,P6MappingFormat,P6MappingStatus,PersistedP6Mapping
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_xlsx_codec import P6XlsxCodec
def test_xlsx_adapter_integration():
 s=BackendScope(tenant_id="t1",project_id="p1",project_revision=4)
 m=PersistedP6Mapping(scope=s,definition=P6MappingDefinition(mapping_id="activity.code",registry_version="p6-field-registry.v1",format=P6MappingFormat.XLSX,subject_area="Activity",source_field="Id",canonical_field="activity.code",status=P6MappingStatus.SUPPORTED))
 a=P6InterchangeAdapter(mapper=P6InterchangeMapper((m,)),codec=P6XlsxCodec())
 imported=a.import_document(P6XlsxCodec().encode((__import__("construction_pm.p6_interchange_mapping",fromlist=["P6InterchangeResult"]).P6InterchangeResult({"Id":"A-10"},{"p6.xlsx.sheet":"Activities"}),),s),scope=s)
 assert imported[0].values=={"activity.code":"A-10"}
