from typing import Any
import httpx


headers = {
    "Authorization": "apikey",
    "Content-Type": "application/json"
}

def getResponseData(response:httpx.Response):
    success = response.status_code == 200
    return success, response if not success else response.json()

async def postHttpRequest(url: str, postData: Any):
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.post(
            url,
            json=postData,
            headers=headers
        )

        return getResponseData(response)


async def getHttpRequest(url: str, headers: dict = None):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response: httpx.Response = await client.get(
            url,
            headers=headers
        )
        return getResponseData(response)
            
async def patchHttpRequest(url: str, postData: Any):
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.patch(
            url,
            json=postData,
            headers=headers
        )

        return getResponseData(response)
    
async def deleteHttpRequest(url: str):
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.delete(
            url,
            headers=headers
        )

        return getResponseData(response)