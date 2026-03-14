"""Credential management service using OS keyring."""

import logging
from typing import Optional

import httpx
import keyring
from keyring.errors import KeyringError

logger = logging.getLogger(__name__)

SERVICE_NAME = "niamoto-deploy"

# Platform credential keys
PLATFORM_KEYS = {
    "cloudflare": ["cloudflare-api-token", "cloudflare-account-id"],
    "github": ["github-token"],
    "netlify": ["netlify-token"],
    "vercel": ["vercel-token"],
    "render": ["render-token"],
    "ssh": [],  # SSH credentials are handled differently (key file path, not stored in keyring)
}

# Platform validation endpoints
PLATFORM_VALIDATION = {
    "cloudflare": {
        "url": "https://api.cloudflare.com/client/v4/user/tokens/verify",
        "header": "Authorization",
        "header_prefix": "Bearer ",
        "success_field": "success",
    },
    "github": {
        "url": "https://api.github.com/user",
        "header": "Authorization",
        "header_prefix": "Bearer ",
        "success_status": 200,
    },
    "netlify": {
        "url": "https://api.netlify.com/api/v1/user",
        "header": "Authorization",
        "header_prefix": "Bearer ",
        "success_status": 200,
    },
    "vercel": {
        "url": "https://api.vercel.com/v2/user",
        "header": "Authorization",
        "header_prefix": "Bearer ",
        "success_status": 200,
    },
    "render": {
        "url": "https://api.render.com/v1/owners",
        "header": "Authorization",
        "header_prefix": "Bearer ",
        "success_status": 200,
    },
}


class CredentialService:
    """Manages deployment credentials via OS keyring."""

    @staticmethod
    def save(platform: str, key: str, value: str) -> bool:
        """Save a credential to the OS keyring."""
        credential_key = f"{platform}-{key}" if not key.startswith(platform) else key
        try:
            keyring.set_password(SERVICE_NAME, credential_key, value)
            logger.info("Saved credential %s for %s", credential_key, platform)
            return True
        except KeyringError as e:
            logger.error("Failed to save credential %s: %s", credential_key, e)
            return False

    @staticmethod
    def get(platform: str, key: str) -> Optional[str]:
        """Retrieve a credential from the OS keyring."""
        credential_key = f"{platform}-{key}" if not key.startswith(platform) else key
        try:
            return keyring.get_password(SERVICE_NAME, credential_key)
        except KeyringError as e:
            logger.error("Failed to get credential %s: %s", credential_key, e)
            return None

    @staticmethod
    def delete(platform: str, key: str) -> bool:
        """Delete a credential from the OS keyring."""
        credential_key = f"{platform}-{key}" if not key.startswith(platform) else key
        try:
            keyring.delete_password(SERVICE_NAME, credential_key)
            logger.info("Deleted credential %s", credential_key)
            return True
        except KeyringError as e:
            logger.error("Failed to delete credential %s: %s", credential_key, e)
            return False

    @staticmethod
    def has_credentials(platform: str) -> bool:
        """Check if a platform has all required credentials configured."""
        keys = PLATFORM_KEYS.get(platform, [])
        if not keys:
            return True  # SSH or unknown platforms
        return all(
            CredentialService.get(platform, k.replace(f"{platform}-", "")) is not None
            for k in keys
        )

    @staticmethod
    async def validate(platform: str) -> dict:
        """Validate credentials by making a test API call to the platform."""
        validation = PLATFORM_VALIDATION.get(platform)
        if not validation:
            return {"valid": False, "error": f"No validation available for {platform}"}

        # Get the token
        keys = PLATFORM_KEYS.get(platform, [])
        if not keys:
            return {"valid": False, "error": f"No credential keys for {platform}"}

        token_key = keys[0]  # First key is always the main token
        token = CredentialService.get(platform, token_key.replace(f"{platform}-", ""))
        if not token:
            return {"valid": False, "error": "No token configured"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    validation["header"]: f"{validation['header_prefix']}{token}"
                }
                # GitHub API requires User-Agent
                if platform == "github":
                    headers["User-Agent"] = "Niamoto-Deploy"

                response = await client.get(validation["url"], headers=headers)

                # Check response
                if "success_field" in validation:
                    data = response.json()
                    if data.get(validation["success_field"]):
                        return {"valid": True, "user": data.get("result", {}).get("id")}
                    return {"valid": False, "error": "Token verification failed"}
                elif response.status_code == validation.get("success_status", 200):
                    data = response.json()
                    # Extract user info for display
                    user_info = (
                        data.get("login")  # GitHub
                        or data.get("full_name")  # Netlify
                        or data.get("username")  # Vercel
                        or data.get("user", {}).get("name")  # Render
                        or "verified"
                    )
                    return {"valid": True, "user": user_info}
                else:
                    return {
                        "valid": False,
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    }
        except httpx.TimeoutException:
            return {"valid": False, "error": "Connection timeout"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    @staticmethod
    def get_all_for_platform(platform: str) -> dict:
        """Get all credentials for a platform (values masked)."""
        keys = PLATFORM_KEYS.get(platform, [])
        result = {}
        for key in keys:
            short_key = key.replace(f"{platform}-", "")
            value = CredentialService.get(platform, short_key)
            if value:
                # Mask the value for display
                result[short_key] = (
                    f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
                )
            else:
                result[short_key] = None
        return result
