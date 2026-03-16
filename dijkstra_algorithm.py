import heapq

# =========================
# 1) Dijkstra Search Algorithm
# =========================

def dijkstra_search(coords, adj, start, goal):
    # Priority Queue: (distance, current_node)
    open_set = [(0, start)]
    
    came_from = {}
    distances = {node: float('inf') for node in coords}
    distances[start] = 0
    
    visited_count = 0

    while open_set:
        current_dist, current = heapq.heappop(open_set)

        if current_dist > distances[current]:
            continue
            
        visited_count += 1

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1], distances[goal], visited_count

        for neighbor, weight in adj.get(current, []):
            distance = current_dist + weight
            
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                came_from[neighbor] = current
                heapq.heappush(open_set, (distance, neighbor))
                
    return None, float('inf'), visited_count

