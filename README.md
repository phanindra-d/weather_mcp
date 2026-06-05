# Weather MCP Server

Production-ready MCP server for weather data using OpenWeatherMap API.

## Features
- City name or lat/lon input
- Returns temperature, humidity, rain status, wind speed, conditions
- MCP protocol compatible (works with Claude Desktop, LiteLLM, any MCP client)
- SSE transport for remote deployment

## Local Usage
```bash
python main.py
```

## Remote Deployment

### Render (Free Tier)
1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. Create new Web Service
4. Connect your GitHub repo
5. Set environment variable: `OPENWEATHER_API=your_api_key`
6. Deploy (uses render.yaml config)

Your MCP server will be at: `https://weather-mcp-xxxx.onrender.com`

## Integration with LiteLLM

```python
from litellm import completion

response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's weather in London?"}],
    tools=[{
        "type": "mcp",
        "server_url": "https://your-server.onrender.com"
    }]
)
```

## Integration with Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "weather-remote": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/client", "https://your-server.onrender.com"]
    }
  }
}
```

## Environment Variables
- `OPENWEATHER_API`: Your OpenWeatherMap API key
- `BASE_URL`: OpenWeather API endpoint (default: https://api.openweathermap.org/data/2.5/weather)
