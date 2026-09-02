import asyncio
import httpx
import sys

async def run():
    async with httpx.AsyncClient() as client:
        # login
        resp = await client.post('http://beefnas:3866/api/auth/login', json={'username':'mcp-service-account','password':'vqt9VXP@znk_ytb2yge','provider':'local'})
        cookies = resp.cookies
        
        # get envs
        resp = await client.get('http://beefnas:3866/api/environments', cookies=cookies)
        envs = resp.json()
        env_id = envs[0].get('Id', envs[0].get('id'))
        print(f"Env ID: {env_id}")
        
        from dockhand_mcp.tools.containers import _compact_container
        
        resp = await client.get(f'http://beefnas:3866/api/containers?env={env_id}', cookies=cookies)
        containers = resp.json()
        
        compacted = [_compact_container(c) for c in containers]
        print(compacted[0])
        print("Total length for all:", len(str(compacted)))

if __name__ == '__main__':
    asyncio.run(run())
