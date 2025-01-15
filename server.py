"""
WebSockets test mule.

An echo server that we can use to test WebSockets and APISIX. Uses the
`websockets` library. Does not use Django or FastAPI explicitly.

This expects to sit behind APISIX in a route that uses openid-connect and is
configured to talk to Keycloak. We can slurp the logged in user info out of the
X-Userinfo header that it sends during the handshake.

"""

import asyncio
import base64
import json

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK


async def handler(websocket):
    print(f"Client connected: {websocket.id}")
    request = websocket.request
    print(f"Request: {request}")

    userinfo = json.loads(base64.b64decode(request.headers.get("X-Userinfo")))

    print(f"Userinfo: {userinfo}")
    await websocket.send(f"=> Hello, {userinfo['preferred_username']}")

    while True:
        try:
            message = await websocket.recv()
            print(f"{websocket.id} sent: {message}")
            await websocket.send(f"Echo: {message}")
        except ConnectionClosedOK:
            print(f"Client disconnected: {websocket.id}")
            break


async def main():
    async with serve(handler, "", 7766):
        print("Server up")
        await asyncio.get_running_loop().create_future() 


if __name__ == "__main__":
    print("Starting server")
    asyncio.run(main())
