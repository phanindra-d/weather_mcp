from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from typing import Optional
import dotenv, os, requests

dotenv.load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API')
BASE_URL = os.getenv('BASE_URL', 'https://api.openweathermap.org/data/2.5/weather')

# Authentication (optional - disabled if MCP_API_TOKEN not set)
auth = None
mcp_token = os.getenv('MCP_API_TOKEN')

if mcp_token:
    auth = StaticTokenVerifier(
        tokens={
            mcp_token: {
                "client_id": "weather-client",
                "scopes": ["weather:read"]
            }
        }
    )
    print(f"✓ MCP authentication enabled")
else:
    print("⚠ MCP authentication disabled (MCP_API_TOKEN not set)")

# MCP Server
mcp = FastMCP(name='weather_mcp', auth=auth)

def get_weather_data(city=None, latitude=None, longitude=None):
    """Fetch weather from OpenWeatherMap API"""
    if city:
        params = {'q': city}
    elif latitude is not None and longitude is not None:
        params = {'lat': latitude, 'lon': longitude}
    else:
        raise ValueError('Provide either city OR latitude and longitude')

    params.update({'appid': API_KEY, 'units': 'metric'})

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    # Calculate rain
    rain_mm = 0
    if "rain" in data and "1h" in data["rain"]:
        rain_mm = data["rain"]["1h"]
    elif "rain" in data and "3h" in data["rain"]:
        rain_mm = data["rain"]["3h"] / 3

    weather_main = data['weather'][0]['main'].lower()
    is_raining = weather_main in ['rain', 'drizzle', 'thunderstorm']

    return {
        "temperature": data['main']['temp'],
        "humidity": data['main']['humidity'],
        "rain_mm_per_hour": rain_mm,
        "is_raining": is_raining,
        "wind_speed": data['wind']['speed'],
        "weather_condition": data['weather'][0]['main'],
        "weather_description": data['weather'][0]['description'],
        "clouds_percent": data['clouds']['all'],
        "location": data.get('name', 'Unknown'),
        "country": data.get('sys', {}).get('country', 'N/A')
    }

# MCP Tool - for AI assistants
@mcp.tool()
def weather_tool(
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> dict:
    """
    Get current weather data for a location.

    Args:
        city: City name (e.g., "London", "New York")
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Weather data including temperature, humidity, rain, wind, and conditions
    """
    try:
        return get_weather_data(city, latitude, longitude)
    except Exception as e:
        return {'Error': str(e)}

# Custom HTTP routes - for REST API compatibility
# These work alongside /mcp endpoint

@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    """Root endpoint - server info"""
    return JSONResponse({
        "service": "Weather MCP Server",
        "version": "1.0.0",
        "mcp_endpoint": "/mcp",
        "rest_endpoint": "/api/weather?city=London",
        "health_check": "/health"
    })

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "healthy"})

@mcp.custom_route("/api/weather", methods=["GET"])
async def weather_endpoint(request: Request) -> JSONResponse:
    """REST API endpoint for weather data"""
    try:
        # Get query parameters
        city = request.query_params.get("city")
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")

        if lat:
            lat = float(lat)
        if lon:
            lon = float(lon)

        # Call core weather function
        data = get_weather_data(city, lat, lon)
        return JSONResponse(data)

    except ValueError as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=400
        )
    except requests.exceptions.HTTPError:
        return JSONResponse(
            {"error": "Location not found"},
            status_code=404
        )
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    mcp.run(transport="http", host="0.0.0.0", port=port)
