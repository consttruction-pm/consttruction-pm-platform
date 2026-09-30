import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_xer_codec import P6XerCodec, P6XerCodecError


def test_xer_rejects_records_after_end_marker():
    document = "%T\tTASK\n%F\tid\n%R\t1\n%E\n%T\tDROPPED\n%F\tid\n%R\t2\n"
    with pytest.raises(P6XerCodecError, match="TRAILING_RECORD_AFTER_END:4"):
        P6XerCodec().decode(
            document,
            BackendScope(tenant_id="t1", project_id="p1", project_revision=4),
        )
