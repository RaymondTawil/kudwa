from fastapi import APIRouter, Depends, Header
from sqlite3 import Connection
from app.domain.models import NLQRequest, NLQResponse
from app.services.nlq import nlq as nlq_service
from app.config import settings
from app.db.db_con import db_conn

router = APIRouter(prefix="/api/v1", tags=["nlq"])

@router.post("/nlq", response_model=NLQResponse)
def nlq(
    req: NLQRequest,
    con: Connection = Depends(db_conn),
    x_model: str | None = Header(default=None, convert_underscores=False),
):
    out = nlq_service(
        con=con,
        query=req.query,
        conversation_id=req.conversation_id,
        openai_api_key=settings.openai_api_key,
        default_model_name=settings.model_name,
        model_variants_str=settings.model_variants, 
        prefer_model=x_model,                          
    )
    return NLQResponse(**out)
