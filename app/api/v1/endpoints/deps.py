from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional

# OAuth2 scheme setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# Type safety ke liye ek chota sa schema
class TokenData(BaseModel):
    user_id: Optional[str] = None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Verifies the JWT token and returns the current user's identification.
    """
    # Standard Unauthorized Exception
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. Token Decode karein
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM]
        )

        # 2. Extract User ID (Humnay 'sub' key use ki hai)
        user_id: str = payload.get("sub")

        if user_id is None:
            raise unauthorized_exception

        token_data = TokenData(user_id=user_id)

    except ExpiredSignatureError:
        # Agar token ka time khatam ho gaya ho
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        # Kisi bhi aur qism ka JWT error (manipulated token etc.)
        raise unauthorized_exception

    # 3. Return as a dictionary (for your current sync logic)
    return {"user_id": token_data.user_id}