"""Public redacted status for the private PA01 policy handoff."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from .policy_evidence import PolicyEvidenceWriter, PolicyWriterStatus


def policy_writer_for(request: Request) -> PolicyEvidenceWriter:
    return request.app.state.policy_writer


PolicyWriterDep = Annotated[PolicyEvidenceWriter, Depends(policy_writer_for)]
router = APIRouter(prefix="/policy/v1", tags=["PA01 policy evidence"])


@router.get("/status")
def status(writer: PolicyWriterDep) -> PolicyWriterStatus:
    return writer.status()
