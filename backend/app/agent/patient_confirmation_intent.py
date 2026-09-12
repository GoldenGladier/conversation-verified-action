from typing import Literal

from pydantic import BaseModel


class PatientProposalResponse(BaseModel):
    decision: Literal["confirm", "reject", "modify", "unrelated"]
