"""Shared fixtures for HTTP-level scenario tests: real DB (in-memory
SQLite), FastAPI over httpx, DEMO_MODE forced True regardless of the real
.env — scenario tests must never make a live Gemini/Tavily/Google call."""

import pytest_asyncio
from apps.api.dependencies import get_db
from apps.api.main import app
from demo.seed import build_agent_catalogue, build_profile
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import synapse_plane.config as config_module
from synapse_plane.persistence.models import Base
from synapse_plane.persistence.repositories import AgentManifestRepository, UserProfileRepository


@pytest_asyncio.fixture
async def scenario_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        await UserProfileRepository(session).upsert(build_profile())
        agent_repo = AgentManifestRepository(session)
        for manifest in build_agent_catalogue():
            await agent_repo.upsert(manifest)
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    original_settings = config_module._settings
    config_module._settings = config_module.Settings(
        database_url="sqlite+aiosqlite:///:memory:", demo_mode=True
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    config_module._settings = original_settings
    await engine.dispose()
