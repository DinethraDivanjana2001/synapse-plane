from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from synapse_plane.domain.profile import UserProfile
from synapse_plane.persistence.repositories import UserProfileRepository

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{user_id}", response_model=UserProfile)
async def get_profile(user_id: str, db: AsyncSession = Depends(get_db)) -> UserProfile:
    profile = await UserProfileRepository(db).get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
