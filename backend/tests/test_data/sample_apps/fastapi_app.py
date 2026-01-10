from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user

# Dependency to check for specific role
def require_role(role: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{role} role required"
            )
        return current_user
    return role_checker

# Dependency to check for any of specified roles
def require_any_role(*roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if not any(role in current_user.roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(roles)}"
            )
        return current_user
    return role_checker

@app.get("/api/expenses")
async def get_expenses(current_user: User = Depends(get_current_user)) -> List[Expense]:
    """Get all expenses - requires authentication"""
    return await expense_service.get_all()

@app.post("/api/expenses", status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(require_role("MANAGER"))
) -> Expense:
    """Create expense - requires MANAGER role"""
    return await expense_service.create(expense)

@app.put("/api/expenses/{expense_id}/approve")
async def approve_expense(
    expense_id: int,
    current_user: User = Depends(require_any_role("MANAGER", "DIRECTOR"))
) -> Expense:
    """Approve expense - MANAGER for < $5000, DIRECTOR for higher"""
    expense = await expense_service.get_by_id(expense_id)

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.amount > 5000 and "DIRECTOR" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Director role required for amounts over $5,000"
        )

    expense.approved = True
    return await expense_service.update(expense)

@app.delete("/api/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(require_role("ADMIN"))
):
    """Delete expense - requires ADMIN role"""
    await expense_service.delete(expense_id)

@app.get("/api/reports/financial")
async def financial_report(current_user: User = Depends(get_current_user)):
    """Generate financial report - Finance department only"""
    if current_user.department != "Finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Finance department access required"
        )

    return await report_service.generate_financial_report()
