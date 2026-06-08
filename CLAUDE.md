# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

Single-file weather service (`main.py`) serving dual protocols:

**Shared Core**: `get_weather_data()` - calls OpenWeatherMap API, parses response, returns structured dict with temp/humidity/rain/wind/conditions.

**Two Interfaces**:
1. **MCP Tool** (`@mcp.tool()` decorator on `weather_tool()`) - exposes function to AI assistants via Model Context Protocol. Runs locally via stdio transport for Claude Desktop integration.
2. **REST API** (FastAPI `@app.get("/api/weather")`) - HTTP endpoint for chatbots/web apps. Deployed on Render, accessible via standard HTTP GET requests.

Both interfaces call same `get_weather_data()` core logic - no duplication.

## Development

**Run locally**:
```bash
python main.py
```
Server starts on `http://localhost:8080`. REST API available at `/api/weather?city=London`.

**Test MCP tool locally** (Claude Desktop):
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "weather": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\main.py"]
    }
  }
}
```

**Environment setup**:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

**Environment variables** (`.env` file):
- `OPENWEATHER_API` - required, get from openweathermap.org
- `BASE_URL` - optional, defaults to OpenWeatherMap current weather endpoint
- `PORT` - optional, defaults to 8080

## Deployment

**Render** (configured via `render.yaml`):
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- Must set `OPENWEATHER_API` env var in Render dashboard
- Free tier: spins down after inactivity

**Railway/Render use `PORT` env variable** - uvicorn binds to `os.getenv('PORT', 8080)`.

## API Contract

**Input**: City name OR lat/lon coordinates (not both).

**Output**: Consistent schema from both MCP and REST:
```python
{
    "temperature": float,        # Celsius
    "humidity": int,             # Percentage
    "rain_mm_per_hour": float,   # Measured rain (0 if none)
    "is_raining": bool,          # True if weather=rain/drizzle/thunderstorm
    "wind_speed": float,         # m/s
    "weather_condition": str,    # "Clear"/"Clouds"/"Rain"/etc
    "weather_description": str,  # "overcast clouds"
    "clouds_percent": int,       # 0-100
    "location": str,             # City name from API
    "country": str               # Country code
}
```

**Rain logic**: `rain_mm_per_hour` is measured precipitation from API (`rain.1h` or `rain.3h`/3). `is_raining` is boolean derived from weather condition type. OpenWeather only includes `rain` object when precipitation actively detected - absence means 0mm.

## Integration Patterns

**For chatbots** (LiteLLM/LangChain): Call REST endpoint via HTTP.

**For AI assistants** (Claude Desktop/Cursor): Use MCP tool via stdio transport.

**Do not** try to mount MCP SSE endpoint in FastAPI - FastMCP 3.4+ changed SSE API. Current approach: separate protocols via separate entry points (stdio for MCP, HTTP for REST).
