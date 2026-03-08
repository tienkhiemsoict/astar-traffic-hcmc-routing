import folium
import pandas as pd
from shapely import wkt

print("Đang khởi tạo bản đồ Folium...")

nodes_df = pd.read_csv('data/nodes.csv')
edges_df = pd.read_csv('data/edges.csv')

nodes_df = nodes_df.set_index('osmid')

center_lat = nodes_df['y'].mean()
center_lon = nodes_df['x'].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=13,
    tiles='CartoDB dark_matter'
)

print("Đang vẽ edges với geometry...")

for _, row in edges_df.iterrows():

    try:

        # Nếu có geometry
        if 'geometry' in edges_df.columns and pd.notna(row['geometry']):

            geom = wkt.loads(row['geometry'])

            coords = [(lat, lon) for lon, lat in geom.coords]

        else:
            # fallback nếu không có geometry
            u = row['u']
            v = row['v']

            if u not in nodes_df.index or v not in nodes_df.index:
                continue

            coords = [
                (nodes_df.loc[u,'y'], nodes_df.loc[u,'x']),
                (nodes_df.loc[v,'y'], nodes_df.loc[v,'x'])
            ]

        folium.PolyLine(
            locations=coords,
            color='cyan',
            weight=1,
            opacity=0.7
        ).add_to(m)

    except:
        continue


print("Đang vẽ nodes...")

for osmid, row in nodes_df.iterrows():

    folium.CircleMarker(
        location=(row['y'], row['x']),
        radius=1,
        color='white',
        fill=True,
        fill_opacity=0.7
    ).add_to(m)

file_name = "map_edges_nodes.html"
m.save(file_name)

print("Đã lưu bản đồ:", file_name)