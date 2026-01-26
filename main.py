"""Main entry point for the Konko AI Agent API server."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing agent modules
load_dotenv()

# Now import agent modules (they may need env vars)
from agent_api import create_app  # noqa: E402

# Load config path from environment or use default
config_path = os.getenv("AGENT_CONFIG_PATH", "configs/basic_agent.yaml")

# Create app with configuration
app = create_app(config_path=config_path)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
