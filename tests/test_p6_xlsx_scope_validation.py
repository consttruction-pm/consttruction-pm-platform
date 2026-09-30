import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_xlsx_codec import P6XlsxCodec


def test_xlsx_decoder_validates_backend_scope():
    with pytest.raises(ValueError):
        P6XlsxCodec().decode(b"not-a-workbook", BackendScope(tenant_id="", project_id="p1", project_revision=4))
