from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.orm import Session

from .. import auth, models
from ..auth import authenticate_user, create_access_token
from ..config import settings
from ..schemas import TokenWithApiKey

router = APIRouter()


@router.post("/login", response_model=TokenWithApiKey)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(auth.get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ensure the user has an API key; generate & save if not
    if not user.api_key:
        user.api_key = models.generate_api_key()
        db.commit()
        db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "api_key": user.api_key,
    }


@router.get("/me")
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return {
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "credits": current_user.credits if not current_user.is_admin else "Unlimited",
    }
