"""Architect Agent — plans software projects and coordinates development."""

from agents.base import BaseAgent


class ArchitectAgent(BaseAgent):
    """Plans project structure, creates work items, assigns tasks, and reviews work."""

    async def plan_project(self, workspace_id: str, developer_agent_id: str, developer_name: str):
        """Create a full project plan: Epic → Features → Stories → Tasks, then kick off discussion."""

        # 1. Create Epic
        epic = await self.create_work_item(
            workspace_id, "epic", "User Authentication System",
            description="Implement a complete user authentication system with login, registration, password reset, and session management."
        )

        # 2. Create Features under Epic
        feat_login = await self.create_work_item(
            workspace_id, "feature", "Login & Registration",
            description="User login and registration flows with email verification.",
            parent_id=epic["id"]
        )
        feat_sessions = await self.create_work_item(
            workspace_id, "feature", "Session Management",
            description="JWT-based session management with refresh tokens.",
            parent_id=epic["id"]
        )

        # 3. Create Stories under Features
        story_login_ui = await self.create_work_item(
            workspace_id, "story", "Login Page UI",
            description="As a user, I want a clean login page so I can access my account.",
            parent_id=feat_login["id"]
        )
        story_register = await self.create_work_item(
            workspace_id, "story", "Registration Flow",
            description="As a new user, I want to register with email and password.",
            parent_id=feat_login["id"]
        )
        story_jwt = await self.create_work_item(
            workspace_id, "story", "JWT Token Service",
            description="As a developer, I need a JWT service for issuing and validating tokens.",
            parent_id=feat_sessions["id"]
        )

        # 4. Create Tasks under Stories — assign to developer
        task_form = await self.create_work_item(
            workspace_id, "task", "Build login form component",
            description="Create React login form with email/password fields, validation, and error display.",
            parent_id=story_login_ui["id"],
            assigned_agent_id=developer_agent_id
        )
        task_api = await self.create_work_item(
            workspace_id, "task", "Implement login API endpoint",
            description="POST /api/auth/login — validate credentials, return JWT. Use bcrypt for password comparison.",
            parent_id=story_login_ui["id"],
            assigned_agent_id=developer_agent_id
        )
        task_register_api = await self.create_work_item(
            workspace_id, "task", "Implement registration endpoint",
            description="POST /api/auth/register — validate input, hash password with bcrypt, store user, send verification email.",
            parent_id=story_register["id"],
            assigned_agent_id=developer_agent_id
        )
        task_jwt = await self.create_work_item(
            workspace_id, "task", "Create JWT utility module",
            description="Create jwt_utils.py with sign_token(), verify_token(), refresh_token() functions. Use RS256 algorithm.",
            parent_id=story_jwt["id"],
            assigned_agent_id=developer_agent_id
        )

        # 5. Create a planning thread and post initial message
        thread = await self.create_thread(
            workspace_id,
            "Auth System — Architecture & Planning",
            description="Main discussion thread for the authentication system design.",
            work_item_id=epic["id"]
        )

        await self.post_message(
            thread["id"],
            f"Hi @{developer_name}, I've set up the project plan for our Authentication System. "
            f"Here's the breakdown:\n\n"
            f"📋 Epic: User Authentication System\n"
            f"  ├── Feature: Login & Registration\n"
            f"  │   ├── Story: Login Page UI\n"
            f"  │   │   ├── Task: Build login form component (assigned to you)\n"
            f"  │   │   └── Task: Implement login API endpoint (assigned to you)\n"
            f"  │   └── Story: Registration Flow\n"
            f"  │       └── Task: Implement registration endpoint (assigned to you)\n"
            f"  └── Feature: Session Management\n"
            f"      └── Story: JWT Token Service\n"
            f"          └── Task: Create JWT utility module (assigned to you)\n\n"
            f"Please start with the JWT utility module since the login API depends on it. "
            f"Let me know if you have any questions about the architecture!"
        )

        return {
            "epic": epic,
            "features": [feat_login, feat_sessions],
            "stories": [story_login_ui, story_register, story_jwt],
            "tasks": [task_form, task_api, task_register_api, task_jwt],
            "thread": thread,
        }

    async def review_and_respond(self, thread_id: str, developer_name: str, tasks: list[dict], workspace_id: str):
        """Review developer's progress and provide feedback."""

        # Check what developer posted
        messages = await self.list_messages(thread_id)

        await self.post_message(
            thread_id,
            f"@{developer_name} Great progress! I've reviewed your updates. "
            f"A few notes:\n\n"
            f"1. For the JWT module, make sure to use RS256 with rotating keys — "
            f"we'll need key rotation for production.\n"
            f"2. The login form should include a 'Remember me' checkbox that extends "
            f"the token TTL to 30 days.\n"
            f"3. For registration, add rate limiting (max 5 attempts per IP per hour).\n\n"
            f"Once the JWT module is done, please move on to the login API endpoint. "
            f"Tag me when you need a code review!"
        )

        # Create a code review thread
        review_thread = await self.create_thread(
            workspace_id,
            "Code Review — JWT Utility Module",
            description="Review thread for the JWT utility implementation."
        )

        await self.post_message(
            review_thread["id"],
            f"@{developer_name} I'm opening this thread for code review discussion. "
            f"Please post your implementation approach here before writing code so "
            f"we can align on the design. Key decisions:\n"
            f"- RSA key pair storage (env vars vs. file system?)\n"
            f"- Token expiry defaults (access: 15min, refresh: 7d?)\n"
            f"- Should we support token revocation via a blocklist?"
        )

        return review_thread
