from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter()

@router.get("/me")
def get_me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token")
    return {"message": "Implement with Clerk SDK"}
