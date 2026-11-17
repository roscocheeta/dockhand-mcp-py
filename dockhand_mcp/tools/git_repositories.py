"""
Git Repository management tools.
"""

from mcp.server.fastmcp import FastMCP, Context
from dockhand_mcp.utils import (
    encode_path,
    redact_sensitive_dict,
    redact_url_credentials,
    validate_repo_url,
)

async def list_git_repositories(ctx: Context = None) -> list:
    """List Git repositories."""
    client = ctx.request_context.lifespan_context["dockhand"]
    repos = await client.get("/api/git/repositories")
    if isinstance(repos, list):
        return [
            {
                "Id": r.get("id") or r.get("Id"),
                "Name": r.get("name") or r.get("Name"),
                "Url": redact_url_credentials(r.get("url") or r.get("Url"))
                if isinstance(r.get("url") or r.get("Url"), str)
                else (r.get("url") or r.get("Url")),
                "Branch": r.get("branch") or r.get("Branch"),
            }
            for r in repos
        ]
    return repos

async def create_git_repository(name: str, url: str, branch: str, ctx: Context = None, credential_id: int | None = None) -> dict:
    """Create a new Git repository reference.

    Note: SSH repository URLs (e.g. 'ssh://...' or 'git@...') must be paired with an
    SSH key credential rather than a username/password credential.
    """
    url = validate_repo_url(url)
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {"name": name, "url": url, "branch": branch}
    if credential_id is not None:
        body["credentialId"] = credential_id
    data = await client.post("/api/git/repositories", json=body)
    return redact_sensitive_dict(data)

async def update_git_repository(repository_id: int, ctx: Context = None, name: str | None = None, url: str | None = None, branch: str | None = None, credential_id: int | None = None) -> dict:
    """Update an existing Git repository reference.

    Note: SSH repository URLs (e.g. 'ssh://...' or 'git@...') must be paired with an
    SSH key credential rather than a username/password credential.
    """
    client = ctx.request_context.lifespan_context["dockhand"]
    body = {}
    if name is not None: body["name"] = name
    if url is not None: body["url"] = validate_repo_url(url)
    if branch is not None: body["branch"] = branch
    if credential_id is not None: body["credentialId"] = credential_id
    data = await client.put(f"/api/git/repositories/{encode_path(str(repository_id))}", json=body)
    return redact_sensitive_dict(data)

async def delete_git_repository(repository_id: int, ctx: Context = None) -> dict:
    """Delete a Git repository reference."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.delete(f"/api/git/repositories/{encode_path(str(repository_id))}")

async def sync_git_repository(repository_id: int, ctx: Context = None) -> dict:
    """Sync a Git repository."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/git/repositories/{encode_path(str(repository_id))}/sync")

async def test_git_repository(repository_id: int, ctx: Context = None) -> dict:
    """Test connectivity for a Git repository."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/git/repositories/{encode_path(str(repository_id))}/test")

async def trigger_git_webhook(repository_id: int, ctx: Context = None) -> dict:
    """Trigger a webhook for a Git repository."""
    client = ctx.request_context.lifespan_context["dockhand"]
    return await client.post(f"/api/git/repositories/{encode_path(str(repository_id))}/webhook")

def register_git_repository_tools(mcp: FastMCP) -> None:
    mcp.add_tool(list_git_repositories)
    mcp.add_tool(create_git_repository)
    mcp.add_tool(update_git_repository)
    mcp.add_tool(delete_git_repository)
    mcp.add_tool(sync_git_repository)
    mcp.add_tool(test_git_repository)
    mcp.add_tool(trigger_git_webhook)
