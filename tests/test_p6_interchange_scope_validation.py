import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_msproject_xml_codec import P6MsProjectXmlCodec
from construction_pm.p6_primavera_xml_codec import P6PrimaveraXmlCodec
from construction_pm.p6_xer_codec import P6XerCodec


def invalid_scope() -> BackendScope:
    return BackendScope(tenant_id="", project_id="p1", project_revision=4)


@pytest.mark.parametrize(
    "codec,payload",
    [
        (P6XerCodec(), "%T\tTASK\n%F\tid\n%R\t1\n%E\n"),
        (P6PrimaveraXmlCodec(), "<APIBusinessObjects/>"),
        (P6MsProjectXmlCodec(), "<Project/>"),
    ],
)
def test_interchange_decoders_validate_backend_scope(codec, payload):
    with pytest.raises(ValueError):
        codec.decode(payload, invalid_scope())
