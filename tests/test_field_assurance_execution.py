from __future__ import annotations

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.field_assurance_execution import (
    FieldAssuranceExecution,
    FieldAssuranceExecutionAnswer,
    FieldAssuranceExecutionError,
    InMemoryFieldAssuranceRepository,
)
from construction_pm.field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)


def scope(revision: int = 7, tenant: str = "tenant-1", project: str = "project-1") -> BackendScope:
    return BackendScope(tenant, project, revision)


def template(version: int = 1, revision: int = 7) -> FieldAssuranceTemplate:
    return FieldAssuranceTemplate(
        template_id="TPL-1",
        scope=scope(revision),
        template_version=version,
        template_type=FieldAssuranceTemplateType.QUALITY,
        title_key="quality.concrete",
        items=(
            FieldAssuranceTemplateItem("I-1", 1, "criterion.pass", FieldAssuranceTemplateInputType.BOOLEAN, True),
            FieldAssuranceTemplateItem("I-2", 2, "criterion.note", FieldAssuranceTemplateInputType.TEXT, False),
        ),
    )


def execution(*, revision: int = 7, version: int = 1, answers=None, tenant="tenant-1", project="project-1"):
    return FieldAssuranceExecution(
        execution_id="EX-1",
        scope=scope(revision, tenant, project),
        template_id="TPL-1",
        template_version=version,
        answers=(
            (FieldAssuranceExecutionAnswer("I-1", True),)
            if answers is None
            else tuple(answers)
        ),
    )


def test_execute_references_exact_immutable_template_version() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template(version=1))
    repo.create_template(template(version=2))

    saved = repo.execute(execution(version=1))
    assert saved.template_version == 1
    assert repo.get_template(scope(), "TPL-1", 1) is not repo.get_template(scope(), "TPL-1", 2)


def test_required_answer_is_enforced() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template())
    with pytest.raises(FieldAssuranceExecutionError, match="MISSING_REQUIRED_EXECUTION_ANSWERS"):
        repo.execute(execution(answers=()))


def test_revision_mismatch_is_rejected() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template(revision=7))
    with pytest.raises(FieldAssuranceExecutionError, match="EXECUTION_SCOPE_MISMATCH"):
        repo.execute(execution(revision=8))


def test_tenant_and_project_are_isolated() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template())
    with pytest.raises(FieldAssuranceExecutionError, match="TEMPLATE_NOT_FOUND"):
        repo.execute(execution(tenant="tenant-2"))
    with pytest.raises(FieldAssuranceExecutionError, match="TEMPLATE_NOT_FOUND"):
        repo.execute(execution(project="project-2"))


def test_template_version_mismatch_is_rejected_even_when_template_exists() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template(version=1))
    with pytest.raises(FieldAssuranceExecutionError, match="TEMPLATE_NOT_FOUND"):
        repo.execute(execution(version=2))


def test_answers_are_type_checked() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template())
    bad = execution(answers=(FieldAssuranceExecutionAnswer("I-1", "yes"),))
    with pytest.raises(FieldAssuranceExecutionError, match="INVALID_BOOLEAN_ANSWER"):
        repo.execute(bad)


def test_duplicate_execution_and_duplicate_template_version_are_rejected() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template())
    with pytest.raises(FieldAssuranceExecutionError, match="TEMPLATE_VERSION_ALREADY_EXISTS"):
        repo.create_template(template())

    repo.execute(execution())
    with pytest.raises(FieldAssuranceExecutionError, match="EXECUTION_ALREADY_EXISTS"):
        repo.execute(execution())


def test_unknown_answer_item_is_rejected() -> None:
    repo = InMemoryFieldAssuranceRepository()
    repo.create_template(template())
    bad = execution(
        answers=(
            FieldAssuranceExecutionAnswer("I-1", True),
            FieldAssuranceExecutionAnswer("UNKNOWN", "x"),
        )
    )
    with pytest.raises(FieldAssuranceExecutionError, match="UNKNOWN_EXECUTION_ITEM"):
        repo.execute(bad)
