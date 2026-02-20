from typing import Any, List
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentConfig, AgentConfigCreate, AgentConfigVersion
from app.models.agent_key import AgentKey
from app.models.project import Project, UserProjectLink
from app.models.user import User, UserRole


class AgentConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_system_agent_configs(self, current_user: User) -> List[AgentConfig]:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        query: Any = select(AgentConfig).where(AgentConfig.project_id == None)
        result = await self.session.exec(query)
        return result.all()

    async def update_system_agent_config(
        self, agent_type: str, config_in: AgentConfigCreate, current_user: User
    ) -> AgentConfig:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        query: Any = select(AgentConfig).where(
            AgentConfig.project_id == None, AgentConfig.type == agent_type
        )
        result = await self.session.exec(query)
        agent_config = result.first()

        if agent_config:
            # Update
            # Update
            self._apply_config_updates(agent_config, config_in)

            self.session.add(agent_config)
            await self.session.commit()
            await self.session.refresh(agent_config)
            return agent_config
        else:
            # Create
            new_config = AgentConfig(
                project_id=None,
                type=agent_type,
                system_prompt=config_in.system_prompt,
                model_provider=config_in.model_provider,
                model=config_in.model,
                encrypted_api_key=config_in.api_key,
                settings=config_in.settings,
            )
            self.session.add(new_config)
            await self.session.commit()
            await self.session.refresh(new_config)
            return new_config

    async def get_project_agent_configs(
        self, project_id: UUID, current_user: User
    ) -> List[AgentConfig]:
        project = await self.session.get(Project, project_id)  # type: ignore[func-returns-value]
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Permission Check
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await self.session.get(UserProjectLink, (current_user.id, project_id))
            if not link:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        query = select(AgentConfig).where(AgentConfig.project_id == project_id)
        result = await self.session.exec(query)
        return result.all()

    async def create_and_initialize_config(
        self, project_id: UUID, config_in: AgentConfigCreate, current_user: User
    ) -> AgentConfig:
        project = await self.session.get(Project, project_id)  # type: ignore[func-returns-value]
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await self.session.get(UserProjectLink, (current_user.id, project_id))
            if not link or link.role not in ["admin", "owner"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        # 1. Existing Configs Check (Name Duplicate & Auto-Activate)
        query = select(AgentConfig).where(
            AgentConfig.project_id == project_id, AgentConfig.type == config_in.type
        )
        existing_configs = (await self.session.exec(query)).all()

        if any(c.name == config_in.name for c in existing_configs):
            raise HTTPException(
                status_code=400, detail="A brain with this name already exists for this agent type."
            )

        # Auto-activate if it's the first one of this type
        is_first = len(existing_configs) == 0

        agent_config = AgentConfig(
            project_id=project_id,
            type=config_in.type,
            system_prompt=config_in.system_prompt,
            model_provider=config_in.model_provider,
            model=config_in.model,
            encrypted_api_key=config_in.api_key,
            settings=config_in.settings,
            trigger_config=config_in.trigger_config,
            schedule_config=config_in.schedule_config,
            context_window=config_in.context_window,
            is_active=is_first,  # Set active state during creation
        )
        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    async def update_agent_config(
        self, agent_id: str, config_in: AgentConfigCreate, current_user: User
    ) -> AgentConfig:
        agent_config = await self.session.get(AgentConfig, UUID(agent_id))  # type: ignore[func-returns-value]
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        await self._check_update_permissions(agent_config, current_user)
        self._apply_config_updates(agent_config, config_in)

        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    async def upsert_project_agent_config_by_type(
        self, project_id: UUID, agent_type: str, config_in: AgentConfigCreate, current_user: User
    ) -> AgentConfig:
        project = await self.session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.role != UserRole.ADMIN:
            link = await self.session.get(UserProjectLink, (current_user.id, project_id))
            if not link or link.role not in ["admin", "owner", "editor"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        query: Any = select(AgentConfig).where(
            AgentConfig.project_id == project_id, AgentConfig.type == agent_type
        )
        result = await self.session.exec(query)
        agent_config = result.first()

        if agent_config:
            # Update
            self._apply_config_updates(agent_config, config_in)
            self.session.add(agent_config)
            await self.session.commit()
            await self.session.refresh(agent_config)
            return agent_config
        else:
            # Create
            new_config = AgentConfig(
                project_id=project_id,
                type=agent_type,
                system_prompt=config_in.system_prompt,
                model_provider=config_in.model_provider,
                encrypted_api_key=config_in.api_key,
                settings=config_in.settings,
            )
            self.session.add(new_config)
            await self.session.commit()
            await self.session.refresh(new_config)
            return new_config

    async def _check_update_permissions(
        self, agent_config: AgentConfig, current_user: User
    ) -> None:
        if agent_config.project_id:
            project = await self.session.get(Project, agent_config.project_id)  # type: ignore[func-returns-value]
            if not project:
                return  # Orphaned config, allow admin? Or fail? Logic was pass.

            if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
                if not link or link.role not in ["admin", "owner"]:
                    raise HTTPException(status_code=403, detail="Not enough permissions")
        else:
            # Global Agent (System or My Agent)
            # System agents (no created_by or created_by is admin?) - Actually system agents created_by might be None or Admin.
            # My Agent: created_by == current_user.id
            is_owner = agent_config.created_by == current_user.id
            if not is_owner and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

    def _apply_config_updates(
        self, agent_config: AgentConfig, config_in: AgentConfigCreate
    ) -> None:
        if config_in.system_prompt is not None:
            agent_config.system_prompt = config_in.system_prompt
        if config_in.model_provider is not None:
            agent_config.model_provider = config_in.model_provider
        if config_in.model is not None:
            agent_config.model = config_in.model

        if config_in.api_key is not None:
            if config_in.api_key == "":
                agent_config.encrypted_api_key = None
            else:
                agent_config.encrypted_api_key = config_in.api_key

        if config_in.settings is not None:
            agent_config.settings = config_in.settings
        if config_in.trigger_config is not None:
            agent_config.trigger_config = config_in.trigger_config
        if config_in.schedule_config is not None:
            agent_config.schedule_config = config_in.schedule_config
        if config_in.context_window is not None:
            agent_config.context_window = config_in.context_window

    async def delete_agent_config(self, agent_id: str, current_user: User) -> None:
        agent_config = await self.session.get(AgentConfig, UUID(agent_id))  # type: ignore[func-returns-value]
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        if agent_config.project_id:
            project = await self.session.get(Project, agent_config.project_id)
            if project and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
                if not link or link.role not in ["admin", "owner"]:
                    raise HTTPException(status_code=403, detail="Not enough permissions")
        else:
            # Global Agent (System or My Agent)
            is_owner = agent_config.created_by == current_user.id
            if not is_owner and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        await self.session.delete(agent_config)
        await self.session.commit()

    async def activate_agent(self, agent_id: str, current_user: User) -> AgentConfig:
        agent_config = await self.session.get(AgentConfig, UUID(agent_id))  # type: ignore[func-returns-value]
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        if agent_config.project_id:
            project = await self.session.get(Project, agent_config.project_id)
            if project and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
                if not link or link.role not in ["admin", "owner"]:
                    raise HTTPException(status_code=403, detail="Not enough permissions")

        # Deactivate others of same type in this project
        if agent_config.project_id:
            query = select(AgentConfig).where(
                AgentConfig.project_id == agent_config.project_id,
                AgentConfig.type == agent_config.type,
            )
            others = await self.session.exec(query)
            for other in others.all():
                other.is_active = False
                self.session.add(other)

        agent_config.is_active = True
        self.session.add(agent_config)
        await self.session.commit()
        return agent_config

    async def get_project_agent_config(self, agent_id: UUID, current_user: User) -> AgentConfig:
        agent_config = await self.session.get(AgentConfig, agent_id)  # type: ignore[func-returns-value]
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        if agent_config.project_id:
            project = await self.session.get(Project, agent_config.project_id)
            if project and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
                if not link:
                    raise HTTPException(status_code=403, detail="Not enough permissions")
        else:
            if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        return agent_config

    async def get_agent_keys(self, agent_config_id: UUID) -> List[AgentKey]:
        query: Any = select(AgentKey).where(AgentKey.agent_config_id == agent_config_id)
        result = await self.session.exec(query)
        return result.all()

    async def update_agent_keys(
        self, agent_config_id: UUID, keys_data: dict, current_user: User
    ) -> AgentConfig:
        # Verify permissions and existence
        agent_config = await self.get_project_agent_config(agent_config_id, current_user)

        # keys_data = {"room_key": "val", "global_key": "val", "backup_key": "val"}

        # 1. Fetch existing keys
        existing_keys = await self.get_agent_keys(agent_config_id)
        existing_map = {k.key_type: k for k in existing_keys}

        for k_type, k_val in keys_data.items():
            if not k_val:
                # If explicitly sent empty, delete/clear.
                if k_type in existing_map:
                    await self.session.delete(existing_map[k_type])
                continue

            if k_type in existing_map:
                existing_map[k_type].encrypted_api_key = k_val
                self.session.add(existing_map[k_type])
            else:
                new_key = AgentKey(
                    agent_config_id=agent_config_id, key_type=k_type, encrypted_api_key=k_val
                )
                self.session.add(new_key)

        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    # =====================================================
    # Versioning Methods
    # =====================================================

    async def create_version(
        self, config_id: UUID, version_label: str, current_user: User
    ) -> AgentConfigVersion:
        agent_config = await self.get_project_agent_config(config_id, current_user)
        
        # Require editing privileges
        if agent_config.project_id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
            if not link or link.role not in ["admin", "owner", "editor"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        version = AgentConfigVersion(
            config_id=config_id,
            version_label=version_label,
            system_prompt=agent_config.system_prompt,
            model_provider=agent_config.model_provider,
            model=agent_config.model,
            settings=agent_config.settings,
            created_by=current_user.id
        )
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def list_versions(self, config_id: UUID, current_user: User) -> List[AgentConfigVersion]:
        await self.get_project_agent_config(config_id, current_user)
        query = select(AgentConfigVersion).where(AgentConfigVersion.config_id == config_id).order_by(AgentConfigVersion.created_at.desc())
        result = await self.session.exec(query)
        return result.all()

    async def restore_version(
        self, config_id: UUID, version_id: UUID, current_user: User
    ) -> AgentConfig:
        agent_config = await self.get_project_agent_config(config_id, current_user)

        # Require editing privileges
        if agent_config.project_id and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
            if not link or link.role not in ["admin", "owner", "editor"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        version = await self.session.get(AgentConfigVersion, version_id)
        if not version or version.config_id != config_id:
            raise HTTPException(status_code=404, detail="Version not found")

        agent_config.system_prompt = version.system_prompt
        agent_config.model_provider = version.model_provider
        agent_config.model = version.model
        if version.settings:
            agent_config.settings = version.settings
            
        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    # =====================================================
    # My Agent (Global Agent) Methods
    # =====================================================

    async def get_global_agents(self, current_user: User) -> List[AgentConfig]:
        """
        Get all global agent templates owned by the current user.
        """
        query: Any = select(AgentConfig).where(
            AgentConfig.is_template == True,
            AgentConfig.created_by == current_user.id
        )
        result = await self.session.exec(query)
        return result.all()

    async def create_global_agent(
        self, config_in: AgentConfigCreate, current_user: User
    ) -> AgentConfig:
        """
        Create a new global agent template (My Agent).
        """
        agent_config = AgentConfig(
            project_id=None,  # Global agent has no project
            type=config_in.type,
            name=config_in.name or "My Agent",
            system_prompt=config_in.system_prompt,
            model_provider=config_in.model_provider,
            model=config_in.model,
            encrypted_api_key=config_in.api_key,
            settings=config_in.settings,
            trigger_config=config_in.trigger_config,
            schedule_config=config_in.schedule_config,
            context_window=config_in.context_window,
            is_template=True,  # Mark as template
            created_by=current_user.id,
        )
        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    async def clone_global_agent_to_project(
        self, agent_id: UUID, project_id: UUID, current_user: User
    ) -> AgentConfig:
        """
        Clone a global agent template to a specific project.
        Creates an instance linked to the parent template.
        """
        # 1. Get parent template
        parent_config = await self.session.get(AgentConfig, agent_id)
        if not parent_config:
            raise HTTPException(status_code=404, detail="Global agent not found")

        if not parent_config.is_template:
            raise HTTPException(status_code=400, detail="Source agent is not a template")

        # 2. Check user owns the template
        if parent_config.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        # 3. Check project exists and user has access
        project = await self.session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            link = await self.session.get(UserProjectLink, (current_user.id, project_id))
            if not link or link.role not in ["admin", "owner"]:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        # 4. Clone the config
        cloned_config = AgentConfig(
            project_id=project_id,
            type=parent_config.type,
            name=parent_config.name,
            system_prompt=parent_config.system_prompt,
            model_provider=parent_config.model_provider,
            model=parent_config.model,
            encrypted_api_key=parent_config.encrypted_api_key,
            settings=parent_config.settings.copy() if parent_config.settings else {},
            trigger_config=parent_config.trigger_config,
            schedule_config=parent_config.schedule_config,
            context_window=parent_config.context_window,
            is_template=False,  # Instance, not template
            parent_config_id=parent_config.id,  # Link to parent
            created_by=current_user.id,
        )
        self.session.add(cloned_config)
        await self.session.commit()
        await self.session.refresh(cloned_config)
        return cloned_config

    async def sync_from_parent(
        self, config_id: UUID, current_user: User
    ) -> AgentConfig:
        """
        Sync an agent instance with its parent template (My Agent).
        Overwrites system_prompt, model_provider, model, and settings.
        """
        agent_config = await self.session.get(AgentConfig, config_id)
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        if not agent_config.parent_config_id:
            raise HTTPException(status_code=400, detail="Agent has no parent template to sync from")

        # Permission check
        if agent_config.project_id:
            project = await self.session.get(Project, agent_config.project_id)
            if project and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                link = await self.session.get(UserProjectLink, (current_user.id, agent_config.project_id))
                if not link or link.role not in ["admin", "owner"]:
                    raise HTTPException(status_code=403, detail="Not enough permissions")

        # Get parent
        parent_config = await self.session.get(AgentConfig, agent_config.parent_config_id)
        if not parent_config:
            raise HTTPException(status_code=404, detail="Parent template not found")

        # Apply parent values
        agent_config.system_prompt = parent_config.system_prompt
        agent_config.model_provider = parent_config.model_provider
        agent_config.model = parent_config.model
        agent_config.settings = parent_config.settings.copy() if parent_config.settings else {}
        agent_config.trigger_config = parent_config.trigger_config
        agent_config.schedule_config = parent_config.schedule_config
        agent_config.context_window = parent_config.context_window

        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    # =====================================================
    # External Agent Methods
    # =====================================================

    async def list_external_agents(self, current_user: User) -> List[AgentConfig]:
        """List all external agents visible to the current user."""
        query = select(AgentConfig).where(AgentConfig.is_external == True)
        
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            query = query.where(AgentConfig.created_by == current_user.id)
            
        result = await self.session.exec(query)
        return list(result.all())

    async def create_external_agent(
        self, 
        name: str,
        type_name: str,
        external_config: dict,
        system_prompt: str,
        current_user: User
    ) -> AgentConfig:
        """Create a new external agent configuration."""
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
            
        from app.models.agent_config import AgentCategory
        
        new_config = AgentConfig(
            type=type_name,
            name=name,
            system_prompt=system_prompt,
            model_provider="external",
            category=AgentCategory.EXTERNAL,
            is_external=True,
            is_active=True,
            external_config=external_config,
            capabilities=["a2a_messaging"],
            created_by=current_user.id,
        )
        
        self.session.add(new_config)
        await self.session.commit()
        await self.session.refresh(new_config)
        return new_config

    async def test_external_connection(self, config: AgentConfig) -> dict:
        """Test connection for an existing agent config."""
        from app.core.a2a.external_adapter import ExternalAgentAdapter
        
        if not config.is_external:
             raise HTTPException(status_code=400, detail="Not an external agent")
             
        adapter = ExternalAgentAdapter(config)
        return await adapter.test_connection()

    async def test_external_connection_params(self, external_config: dict) -> dict:
        """Test connection using raw parameters (before creation)."""
        # Create a temporary/dummy config for the adapter
        dummy_config = AgentConfig(
            type="external_test",
            name="test",
            model_provider="external",
            is_external=True,
            external_config=external_config
        )
        
        from app.core.a2a.external_adapter import ExternalAgentAdapter
        # We might need to ensure the adapter doesn't need other fields that are missing
        # ExternalAgentAdapter checks is_external and external_config.
        
        try:
            adapter = ExternalAgentAdapter(dummy_config)
            return await adapter.test_connection()
        except Exception as e:
            return {"success": False, "error": str(e)}
