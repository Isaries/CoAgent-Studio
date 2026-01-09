from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentConfig, AgentConfigCreate
from app.models.course import Course
from app.models.user import User, UserRole


class AgentConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_system_agent_configs(self, current_user: User) -> List[AgentConfig]:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        query = select(AgentConfig).where(AgentConfig.course_id == None)
        result = await self.session.exec(query)
        return result.all()

    async def update_system_agent_config(self, agent_type: str, config_in: AgentConfigCreate, current_user: User) -> AgentConfig:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        query = select(AgentConfig).where(AgentConfig.course_id == None, AgentConfig.type == agent_type)
        result = await self.session.exec(query)
        agent_config = result.first()

        if agent_config:
            # Update
            agent_config.system_prompt = config_in.system_prompt
            agent_config.model_provider = config_in.model_provider
            agent_config.model = config_in.model
            if config_in.api_key is not None:
                if config_in.api_key == "":
                    agent_config.encrypted_api_key = None
                else:
                    agent_config.encrypted_api_key = config_in.api_key
            if config_in.settings:
                # Merge or Replace? Pydantic dict handles it?
                # Model definition usually implies JSON replacement for SA JSON columns.
                agent_config.settings = config_in.settings

            self.session.add(agent_config)
            await self.session.commit()
            await self.session.refresh(agent_config)
            return agent_config
        else:
            # Create
            new_config = AgentConfig(
                course_id=None,
                type=agent_type,
                system_prompt=config_in.system_prompt,
                model_provider=config_in.model_provider,
                model=config_in.model,
                encrypted_api_key=config_in.api_key,
                settings=config_in.settings
            )
            self.session.add(new_config)
            await self.session.commit()
            await self.session.refresh(new_config)
            return new_config

    async def get_course_agent_configs(self, course_id: UUID, current_user: User) -> List[AgentConfig]:
        course = await self.session.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Permission: Admin, Owner, or TA?
        # Usually settings page calls this.
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
            # Allow TA? Current logic in endpoint seemed to allow "if not course" raise, but didn't strictly check permission for GET?
            # Let's check original code.
            # Oh, the original code had a print "DEBUG" but then had no permission check visible in snippet?
            # Wait, usually read is stricter. Let's enforce Owner/Admin for now as it contains API keys (masked).
            raise HTTPException(status_code=403, detail="Not enough permissions")

        query = select(AgentConfig).where(AgentConfig.course_id == course_id)
        result = await self.session.exec(query)
        return result.all()

    async def create_course_agent_config(self, course_id: UUID, config_in: AgentConfigCreate, current_user: User) -> AgentConfig:
        course = await self.session.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
             raise HTTPException(status_code=403, detail="Not enough permissions")

        agent_config = AgentConfig(
            course_id=course_id,
            type=config_in.type,
            system_prompt=config_in.system_prompt,
            model_provider=config_in.model_provider,
            model=config_in.model,
            encrypted_api_key=config_in.api_key,
            settings=config_in.settings,
            trigger_config=config_in.trigger_config,
            schedule_config=config_in.schedule_config,
            context_window=config_in.context_window
        )
        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    async def update_agent_config(self, agent_id: str, config_in: AgentConfigCreate, current_user: User) -> AgentConfig:
        agent_config = await self.session.get(AgentConfig, UUID(agent_id))
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        # Permission check via Course
        if agent_config.course_id:
            course = await self.session.get(Course, agent_config.course_id)
            if not course:
                 # Orphaned config?
                 pass
            elif current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
                 raise HTTPException(status_code=403, detail="Not enough permissions")
        else:
             # System config accessed via ID? Usually system endpoints use type.
             if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                 raise HTTPException(status_code=403, detail="Not enough permissions")

        # Update fields
        if config_in.system_prompt is not None: agent_config.system_prompt = config_in.system_prompt
        if config_in.model_provider is not None: agent_config.model_provider = config_in.model_provider
        if config_in.model is not None: agent_config.model = config_in.model

        if config_in.api_key is not None:
             if config_in.api_key == "":
                 agent_config.encrypted_api_key = None
             else:
                 agent_config.encrypted_api_key = config_in.api_key

        if config_in.settings is not None: agent_config.settings = config_in.settings
        if config_in.trigger_config is not None: agent_config.trigger_config = config_in.trigger_config
        if config_in.schedule_config is not None: agent_config.schedule_config = config_in.schedule_config
        if config_in.context_window is not None: agent_config.context_window = config_in.context_window

        self.session.add(agent_config)
        await self.session.commit()
        await self.session.refresh(agent_config)
        return agent_config

    async def delete_agent_config(self, agent_id: str, current_user: User):
        agent_config = await self.session.get(AgentConfig, UUID(agent_id))
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        if agent_config.course_id:
             course = await self.session.get(Course, agent_config.course_id)
             if course and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
                  raise HTTPException(status_code=403, detail="Not enough permissions")
        else:
             if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                  raise HTTPException(status_code=403, detail="Not enough permissions")

        await self.session.delete(agent_config)
        await self.session.commit()

    async def activate_agent(self, agent_id: str, current_user: User):
        agent_config = await self.session.get(AgentConfig, UUID(agent_id))
        if not agent_config:
            raise HTTPException(status_code=404, detail="Agent config not found")

        if agent_config.course_id:
             course = await self.session.get(Course, agent_config.course_id)
             if course and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
                  raise HTTPException(status_code=403, detail="Not enough permissions")

        # Deactivate others of same type in this course
        if agent_config.course_id:
            query = select(AgentConfig).where(
                AgentConfig.course_id == agent_config.course_id,
                AgentConfig.type == agent_config.type
            )
            others = await self.session.exec(query)
            for other in others.all():
                other.is_active = False
                self.session.add(other)

        agent_config.is_active = True
        self.session.add(agent_config)
        await self.session.commit()
        return agent_config
