"""
Alternative SSE server using Uvicorn directly for Railway deployment
"""
import os
import uvicorn
from main import mcp

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))

    # Run FastMCP with SSE transport via Uvicorn
    uvicorn.run(
        "main:mcp.app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
