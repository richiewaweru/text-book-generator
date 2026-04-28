from pydantic import BaseModel


class GenerationAcceptedResponse(BaseModel):
    generation_id: str
    status: str
    events_url: str
    document_url: str
    report_url: str
