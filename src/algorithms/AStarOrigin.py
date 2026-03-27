import math
import heapq

def a_star_search(coords, adj, start, goal):
    goal_lat, goal_lon = coords[goal]
    deg_to_m = 111319.0
    lon_factor = math.cos(math.radians(goal_lat))
    
    # Heuristic tối ưu: dùng Euclidean thay vì Haversine
    def heuristic(node_id):
        n_lat, n_lon = coords[node_id]
        dy = (n_lat - goal_lat) * deg_to_m
        dx = (n_lon - goal_lon) * deg_to_m * lon_factor
        return math.sqrt(dx*dx + dy*dy)
    
    g_score = {start: 0.0}
    came_from = {}
    open_heap = [(heuristic(start), start)]
    closed_set = set()
    visited_count = 0
    heap_pop = heapq.heappop
    heap_push = heapq.heappush

    while open_heap:
        _, current = heap_pop(open_heap)

        if current in closed_set:
            continue
        
        closed_set.add(current)
        visited_count += 1
        
        if current == goal:
            # Khôi phục đường đi
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1], g_score[goal], visited_count

        for neighbor, edge_cost in adj.get(current, []):
            if neighbor in closed_set:
                continue
            
            tentative_g = g_score[current] + edge_cost
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_val = tentative_g + heuristic(neighbor)
                heap_push(open_heap, (f_val, neighbor))

    return None, float('inf'), visited_count