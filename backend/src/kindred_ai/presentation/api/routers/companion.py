from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from kindred_ai.application.companion import get_companion_agent

router=APIRouter(prefix="/companion", tags=["Companion Agent"])
class Message(BaseModel): message:str
class FamilyMessage(BaseModel): contact_id:str; content:str; user_approved:bool=False
class CallRequest(BaseModel): contact_query:str
@router.post("/respond")
def respond(payload:Message): return {"reply":get_companion_agent().respond(payload.message)}
@router.get("/contacts")
def contacts(): return get_companion_agent().contacts()
@router.get("/phone-book")
def phone_book(): return get_companion_agent().phone_book()
@router.post("/call-requests", status_code=201)
def call(payload: CallRequest):
    try: return get_companion_agent().request_family_call(payload.contact_query)
    except ValueError as error: raise HTTPException(status_code=422,detail=str(error))
@router.post("/family-messages")
def send(payload:FamilyMessage):
    try: return get_companion_agent().send_approved_family_message(payload.contact_id,payload.content,payload.user_approved)
    except ValueError as error: raise HTTPException(status_code=422,detail=str(error))
