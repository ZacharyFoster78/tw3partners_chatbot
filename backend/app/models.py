from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict]

class FeedbackRequest(BaseModel):
    conversation: List[dict]
    rating: bool # True for good, False for bad