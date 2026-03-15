import osmnx as ox

# City to download
place = "Thiruvananthapuram, Kerala, India"

print("Downloading road network...")

# Download map
graph = ox.graph_from_place(place, network_type="drive")

print("Map downloaded successfully")

# Save the graph to a file
ox.save_graphml(graph, "trivandrum_map.graphml")

print("Map saved as trivandrum_map.graphml")