from pydantic import BaseModel, Field
from typing import Optional, List

class LeadAnalysis(BaseModel):
    name: Optional[str] = Field(None, description="Name of the contact or client.")
    company: Optional[str] = Field(None, description="Company or organization name.")
    email: Optional[str] = Field(None, description="Email address of the contact.")
    contactReason: Optional[str] = Field(None, description="Reason for the contact or call.")
    interest: Optional[str] = Field(None, description="Type of interest or topic discussed.")
    projectOrService: Optional[str] = Field(None, description="Specific project or service mentioned.")
    interestLevel: Optional[str] = Field(None, description="Level of interest, e.g., High, Medium, Low.")
    currentStatus: Optional[str] = Field(None, description="Current state of the interaction or lead.")
    nextAction: Optional[str] = Field(None, description="Next action or follow-up required.")
    shortSummary: Optional[str] = Field(None, description="Brief summary of the conversation.")

    def keys(self) -> List[str]:
        """Return the list of field names as strings."""
        return list(self.model_fields.keys())