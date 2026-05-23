"""utils/id_generator.py"""
from __future__ import annotations
import uuid


def make_job_id() -> str:
    """e.g. 'job_3f2a1b9c'"""
    return f"job_{uuid.uuid4().hex[:8]}"
