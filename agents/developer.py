"""Developer Agent — implements tasks, reports progress, and collaborates."""

from agents.base import BaseAgent


class DeveloperAgent(BaseAgent):
    """Picks up assigned tasks, updates statuses, posts progress, and asks questions."""

    async def acknowledge_plan(self, thread_id: str, architect_name: str):
        """Respond to the architect's project plan."""
        await self.post_message(
            thread_id,
            f"Thanks @{architect_name}! I've reviewed the project plan and it looks solid. "
            f"I'll start with the JWT utility module as suggested. "
            f"Quick question before I begin — should we support multiple signing algorithms "
            f"(RS256 + ES256) or just RS256 for now? Also, should the token payload include "
            f"user roles/permissions or just the user ID?\n\n"
            f"I'll begin setting up the module structure while waiting for your response."
        )

    async def start_task(self, workspace_id: str, task: dict, thread_id: str, architect_name: str):
        """Mark a task as in_progress and post an update."""
        await self.update_work_item(workspace_id, task["id"], status="in_progress")

        await self.post_message(
            thread_id,
            f"@{architect_name} Starting work on: **{task['title']}**\n"
            f"Moving it to 'in_progress'. I'll post updates here as I make progress."
        )

    async def post_progress(self, thread_id: str, architect_name: str, task_title: str):
        """Post a progress update with technical details."""
        await self.post_message(
            thread_id,
            f"@{architect_name} Progress update on **{task_title}**:\n\n"
            f"✅ Created `jwt_utils.py` with the following structure:\n"
            f"  - `generate_key_pair()` — generates RSA 2048-bit key pair\n"
            f"  - `sign_token(payload, ttl=900)` — signs JWT with RS256\n"
            f"  - `verify_token(token)` — validates signature + expiry\n"
            f"  - `refresh_token(token, ttl=604800)` — issues new token from valid refresh\n\n"
            f"🔧 Design decisions made:\n"
            f"  - Using RS256 as agreed, keys loaded from env vars\n"
            f"  - Access token TTL: 15 min, Refresh token TTL: 7 days\n"
            f"  - Added `jti` claim for future token revocation support\n\n"
            f"Ready for review. Should I open a PR or post the code here?"
        )

    async def complete_task(self, workspace_id: str, task: dict, thread_id: str, architect_name: str):
        """Mark a task as done and notify."""
        await self.update_work_item(workspace_id, task["id"], status="done")

        await self.post_message(
            thread_id,
            f"@{architect_name} ✅ Completed: **{task['title']}**\n"
            f"Moved to 'done'. All unit tests passing. Ready for the next task."
        )

    async def respond_to_review(self, review_thread_id: str, architect_name: str):
        """Respond to the code review discussion."""
        await self.post_message(
            review_thread_id,
            f"@{architect_name} Here's my proposed approach for the JWT module:\n\n"
            f"**RSA Key Storage**: I'll use environment variables (`JWT_PRIVATE_KEY`, "
            f"`JWT_PUBLIC_KEY`) in PEM format. For local dev, we auto-generate a pair "
            f"if not set.\n\n"
            f"**Token Expiry Defaults**:\n"
            f"  - Access: 15 min (configurable via `JWT_ACCESS_TTL`)\n"
            f"  - Refresh: 7 days (configurable via `JWT_REFRESH_TTL`)\n\n"
            f"**Token Revocation**: I'll add a `jti` (JWT ID) claim to every token. "
            f"For v1, we'll use an in-memory set for revoked JTIs. We can swap to "
            f"Redis later.\n\n"
            f"**Token Payload**:\n"
            f"```json\n"
            f'{{"sub": "user_id", "jti": "unique-id", "roles": ["user"], '
            f'"iat": 1234567890, "exp": 1234568790}}\n'
            f"```\n\n"
            f"Does this align with your vision? I can start coding once approved."
        )

    async def ask_question(self, thread_id: str, architect_name: str):
        """Ask a technical question about the implementation."""
        await self.post_message(
            thread_id,
            f"@{architect_name} Quick question about the login API:\n\n"
            f"For the `POST /api/auth/login` endpoint, should we:\n"
            f"1. Return both access + refresh tokens in the response body, OR\n"
            f"2. Set the refresh token as an HttpOnly cookie?\n\n"
            f"Option 2 is more secure against XSS but complicates CORS. "
            f"What's our deployment setup — same-origin or separate frontend/API domains?"
        )
