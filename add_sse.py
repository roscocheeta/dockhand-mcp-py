import sys

def modify_client():
    with open('dockhand_mcp/client.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_methods = '''
    async def post_sse(
        self, path: str, json: Any = None, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """POST returning Server-Sent Events. Parses the events and returns combined output."""
        return await self._request_sse("POST", path, json_body=json, params=params)

    async def put_sse(
        self, path: str, json: Any = None, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """PUT returning Server-Sent Events. Parses the events and returns combined output."""
        return await self._request_sse("PUT", path, json_body=json, params=params)

    async def _request_sse(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make a request expecting an SSE stream and parse the data lines."""
        await self._auth.ensure_authenticated(self._client)

        clean_params = {k: v for k, v in params.items() if v is not None} if params else None
        
        headers = {"Accept": "text/event-stream"}
        kwargs = {"headers": headers}
        if json_body is not None:
            kwargs["json"] = json_body
        if clean_params:
            kwargs["params"] = clean_params

        current_version = self._auth.session_version
        
        # Dockhand deploy streams can take a long time, use a longer timeout (5 mins)
        client = self._client.copy_with(timeout=httpx.Timeout(300.0, connect=10.0))
        resp = await client.request(method, path, **kwargs)

        if resp.status_code == 401:
            await self._auth.invalidate_and_retry(self._client, current_version)
            resp = await client.request(method, path, **kwargs)

        if resp.status_code >= 400:
            detail = resp.text[:1000] if resp.text else resp.reason_phrase
            raise DockhandAPIError(resp.status_code, detail, method, path)

        return self._parse_sse_response(resp)

    @staticmethod
    def _parse_sse_response(resp: httpx.Response) -> dict[str, Any]:
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()

        import json as json_lib
        
        text = resp.text
        lines = text.split('\\n')
        combined_output = []
        last_success = True
        
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith('data: '):
                payload = trimmed[6:]
                try:
                    data = json_lib.loads(payload)
                    if isinstance(data, dict):
                        if 'output' in data:
                            combined_output.append(str(data['output']))
                        if 'error' in data:
                            combined_output.append(str(data['error']))
                        if 'success' in data:
                            last_success = bool(data['success'])
                except json_lib.JSONDecodeError:
                    combined_output.append(payload)

        if not combined_output:
            return {"success": True, "output": text}
            
        return {
            "success": last_success,
            "output": "\\n".join(combined_output)
        }
'''

    # Insert it right before Health check shorthand
    parts = content.split('def health_check')
    if len(parts) == 2:
        new_content = parts[0] + new_methods.strip() + '\n\n    async def health_check' + parts[1]
        with open('dockhand_mcp/client.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated client.py with SSE support")
    else:
        print("Failed to find insertion point")

if __name__ == '__main__':
    modify_client()
