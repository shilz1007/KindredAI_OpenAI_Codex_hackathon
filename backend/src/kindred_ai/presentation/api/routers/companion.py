from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from kindred_ai.application.companion import get_companion_agent
from kindred_ai.application.communication.service import get_communication_service

router=APIRouter(prefix="/companion", tags=["Companion Agent"])
class Message(BaseModel): message:str
class FamilyMessage(BaseModel): contact_id:str; content:str; user_approved:bool=False
class CallRequest(BaseModel): contact_query:str
class PhoneBookContact(BaseModel):
    display_name: str = Field(min_length=1, examples=["Name of the person"])
    relationship: str = Field(min_length=1, examples=["son"])
    phone_number: str = Field(min_length=7, examples=["+4790000000"])
    approved_for_calls: bool = True
@router.post("/respond")
def respond(payload:Message): return {"reply":get_companion_agent().respond(payload.message)}
@router.get("/contacts")
def contacts(): return get_companion_agent().contacts()
@router.get("/phone-book")
def phone_book(): return get_companion_agent().phone_book()
@router.post("/phone-book", status_code=201)
def add_phone_book_contact(payload: PhoneBookContact):
    try:
        return get_communication_service().add_phone_book_contact(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
@router.post("/call-requests", status_code=201)
def call(payload: CallRequest):
    try: return get_companion_agent().request_family_call(payload.contact_query)
    except ValueError as error: raise HTTPException(status_code=422,detail=str(error))
@router.post("/family-messages")
def send(payload:FamilyMessage):
    try: return get_companion_agent().send_approved_family_message(payload.contact_id,payload.content,payload.user_approved)
    except ValueError as error: raise HTTPException(status_code=422,detail=str(error))
