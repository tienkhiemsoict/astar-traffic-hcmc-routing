import os
import logging
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from scipy.spatial import KDTree
from functools import lru_cache
import ast
from shapely import wkt
import time

from src.algorithms.Dijkstra import dijkstra_search
from src.algorithms.AStarOrigin import a_star_search
from src.algorithms.DWAStar import dwa_star_search
from src.load_graph import load_graph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SLOT_TO_INDEX_OFFSET = 1
MIN_DISPLAYABLE_EDGE_LENGTH_METERS = 10
DEFAULT_HIGHWAY_WIDTH = 2
DEFAULT_TRAFFIC_COLOR = "#e74c3c"  # Red
TRAFFIC_OPACITY = 0.6

class TrafficConfig:
    """Configuration for traffic visualization."""
    IMPORTANT_HIGHWAYS = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']
    
    HIGHWAY_WIDTHS = {
        'motorway': 6,
        'trunk': 5,
        'primary': 4,
        'secondary': 2.5,
        'tertiary': 1.2
    }
    
    # LOS thresholds with colors (Green -> Yellow -> Orange -> Red)
    LOS_COLOR_THRESHOLDS = [
        (1.1, "#2ecc71"),  # Green
        (1.3, "#f1c40f"),  # Yellow
        (1.5, "#e67e22"),  # Orange
    ]

# Initialize FastAPI app
app = FastAPI(
    title="HCMC Traffic Routing API",
    description="Route finding with traffic-aware algorithms",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_PATH = os.path.join(BASE_DIR, "data", "processed", "nodes.csv")
EDGES_PATH = os.path.join(BASE_DIR, "data", "processed", "edges.csv")

# Load data
try:
    nodes_df = pd.read_csv(NODES_PATH)
    edges_df = pd.read_csv(EDGES_PATH)
    spatial_index = KDTree(nodes_df[['y', 'x']].values)
    logger.info(f"Loaded {len(nodes_df)} nodes and {len(edges_df)} edges")
except Exception as e:
    logger.error(f"Failed to load data: {e}")
    raise

# Models
class RouteRequest(BaseModel):
    """Request model for route calculation."""
    start_id: int = Field(..., description="Start node OSM ID")
    end_id: int = Field(..., description="End node OSM ID")
    slot: int = Field(..., ge=1, le=48, description="Time slot (1-48)")

class SnapNodeResponse(BaseModel):
    """Response model for node snapping."""
    id: int
    lat: float
    lng: float

# Helper functions
def filter_edges_for_display(edges: pd.DataFrame) -> pd.DataFrame:
    """Filter edges suitable for traffic visualization."""
    return edges[
        (edges['length'] >= MIN_DISPLAYABLE_EDGE_LENGTH_METERS) & 
        edges['highway'].isin(TrafficConfig.IMPORTANT_HIGHWAYS)
    ]

def get_traffic_color(los_value: float) -> str:
    """Map Level of Service value to color code."""
    for threshold, color in TrafficConfig.LOS_COLOR_THRESHOLDS:
        if los_value < threshold:
            return color
    return DEFAULT_TRAFFIC_COLOR

def edge_to_geojson_feature(
    row: pd.Series, 
    slot_index: int
) -> Optional[Dict[str, Any]]:
    """Convert edge row to GeoJSON feature with traffic data."""
    try:
        los_list = ast.literal_eval(row['los'])
        los_value = float(los_list[slot_index])
        geom = wkt.loads(row['geometry']).__geo_interface__
        
        return {
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "color": get_traffic_color(los_value),
                "weight": TrafficConfig.HIGHWAY_WIDTHS.get(
                    row['highway'], 
                    DEFAULT_HIGHWAY_WIDTH
                ),
                "opacity": TRAFFIC_OPACITY
            }
        }
    except (ValueError, SyntaxError, KeyError, IndexError) as e:
        logger.warning(f"Failed to convert edge to GeoJSON: {e}")
        return None

def convert_numpy_types(obj: Any) -> Any:
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    return obj

@lru_cache(maxsize=10)
def get_cached_graph_data(slot: int) -> Tuple:
    """Load and cache graph data for specific time slot."""
    logger.info(f"Loading graph data for slot {slot}")
    return load_graph(NODES_PATH, EDGES_PATH, slot)

# API Endpoints
@app.get("/api/snap-node", response_model=SnapNodeResponse)
async def snap_to_nearest_node(lat: float, lng: float) -> SnapNodeResponse:
    """Find nearest graph node to given coordinates."""
    try:
        distance, index = spatial_index.query([lat, lng])
        node = nodes_df.iloc[index]
        
        return SnapNodeResponse(
            id=int(node['osmid']),
            lat=float(node['y']),
            lng=float(node['x'])
        )
    except Exception as e:
        logger.error(f"Snap node failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traffic-geojson")
async def get_traffic_geojson(slot: int) -> Dict[str, Any]:
    """Get traffic layer as GeoJSON for visualization."""
    if not 1 <= slot <= 48:
        raise HTTPException(
            status_code=400, 
            detail="Slot must be between 1 and 48"
        )
    
    try:
        slot_index = slot - SLOT_TO_INDEX_OFFSET
        filtered_edges = filter_edges_for_display(edges_df)
        
        features = [
            feature for feature in (
                edge_to_geojson_feature(row, slot_index) 
                for _, row in filtered_edges.iterrows()
            ) if feature is not None
        ]
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    except Exception as e:
        logger.error(f"Traffic GeoJSON generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/route")
async def calculate_route(request: RouteRequest) -> Dict[str, Any]:
    """Calculate optimal route using DWA* algorithm."""
    try:
        coords, adjacency, _ = get_cached_graph_data(request.slot)
        
        path, cost, visited_count = dwa_star_search(
            coords, 
            adjacency, 
            request.start_id, 
            request.end_id
        )
        
        if not path:
            return {
                "status": "error",
                "message": "No route found between specified nodes"
            }
        
        path_coords = [
            [coords[node_id][0], coords[node_id][1]]
            for node_id in path
            if node_id in coords
        ]
        
        return {
            "status": "success",
            "path_coords": path_coords,
            "stats": {
                "distance_m": convert_numpy_types(cost),
                "visited_nodes": convert_numpy_types(visited_count)
            }
        }
    except Exception as e:
        logger.error(f"Route calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare")
async def compare_algorithms(request: RouteRequest) -> List[Dict[str, Any]]:
    """Compare performance of different routing algorithms."""
    try:
        coords, adjacency, _ = get_cached_graph_data(request.slot)
        
        algorithms = [
            ("DWA*", dwa_star_search),
            ("Dijkstra", dijkstra_search),
            ("A*", a_star_search)
        ]
        
        results = []
        for algo_name, algo_func in algorithms:
            start_time = time.perf_counter()
            _, cost, visited = algo_func(
                coords, 
                adjacency, 
                request.start_id, 
                request.end_id
            )
            elapsed_time = time.perf_counter() - start_time
            
            results.append({
                "algo": algo_name,
                "dist": convert_numpy_types(cost),
                "visited": convert_numpy_types(visited),
                "time_ms": round(elapsed_time * 1000, 2)
            })
        
        logger.info(f"Algorithm comparison completed for route {request.start_id} -> {request.end_id}")
        return results
        
    except Exception as e:
        logger.error(f"Algorithm comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000,
        log_level="info"
    )
