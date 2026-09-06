from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from synapse_plane.domain.agent import AgentManifest
from synapse_plane.persistence.repositories import AgentManifestRepository

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentManifest])
async def list_agents(db: AsyncSession = Depends(get_db)) -> list[AgentManifest]:
    return await AgentManifestRepository(db).list_all()
