import asyncio

import litellm

from data import init_database
from gateway.app import create_app
from gateway.config import get_settings
app = create_app()

if __name__ == "__main__":
    import uvicorn
    litellm.config_path="./litellm_config.yml"
    uvicorn.run("main:app", host="0.0.0.0", port=get_settings().port, reload=False)