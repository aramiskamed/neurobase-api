from fastapi import APIRouter

router = APIRouter()

# Placeholder endpoints — implement as needed
@router.get("/provas")
def list_provas():
    return {"message": "Provas endpoint - implement with Supabase query"}

@router.get("/lectures")
def list_lectures():
    return {"message": "Lectures endpoint - implement with Supabase query"}
