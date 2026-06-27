from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows

class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(self, token_url: str, cookie_name: str = "access_token"):
        flows = OAuthFlows(password={"tokenUrl": token_url})
        super().__init__(flows=flows, auto_error=False)
        self.cookie_name = cookie_name

    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get(self.cookie_name)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        if token.startswith("Bearer "):
            return token[7:]
        return token
