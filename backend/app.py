from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import osmnx as ox
import networkx as nx
from scipy.spatial import KDTree

app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)   # IMPORTANT: allow frontend to call backend

graph = ox.load_graphml("trivandrum_map.graphml")
graph = ox.convert.to_digraph(graph)

# Only keep the largest strongly connected component to avoid "No path" errors
import networkx as nx
if not nx.is_strongly_connected(graph):
    largest_cc = max(nx.strongly_connected_components(graph), key=len)
    graph = graph.subgraph(largest_cc).copy()


# Load model
model = joblib.load("../model/safetymodel.pkl")
label_encoder = joblib.load("../model/label_encoder.pkl")

# Load dataset
df = pd.read_csv("../dataset/crime_data.csv")
import os
import csv

FEEDBACK_FILE = "../dataset/user_feedback.csv"
if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["start", "destination", "predicted_score", "user_rating", "comment"])

# Precompute coordinates of dataset locations
location_coords = {}

for loc in df["location"]:
    try:
        coords = ox.geocode(loc + ", Thiruvananthapuram, Kerala, India")
        location_coords[loc] = coords
    except:
        continue

coords_list = list(location_coords.values())
location_names = list(location_coords.keys())
tree = KDTree(coords_list)

def find_nearest_area(lat, lon):
    dist, index = tree.query([lat, lon])
    return location_names[index]

@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    start = data["start_location"]
    destination = data["destination"]

    try:
        # STEP 4 — Convert location to coordinates
        start_coords = ox.geocode(start + ", Thiruvananthapuram, Kerala, India")
        dest_coords = ox.geocode(destination + ", Thiruvananthapuram, Kerala, India")

        # STEP 5 — Find nearest road nodes
        start_node = ox.distance.nearest_nodes(graph, start_coords[1], start_coords[0])
        end_node = ox.distance.nearest_nodes(graph, dest_coords[1], dest_coords[0])

        # STEP 6 — Generate route
        # Route 1 - shortest distance
        route1 = nx.shortest_path(graph, start_node, end_node, weight="length")

        # Create modified graph for alternative route
        graph_temp = graph.copy()

        for i in range(len(route1)-1):
            u = route1[i]
            v = route1[i+1]
            if graph_temp.has_edge(u, v):
                graph_temp.remove_edge(u, v)

        # Route 2 - alternate route (wrap in try-catch because removing edges can break connectivity)
        routes = [route1]
        try:
            route2 = nx.shortest_path(graph_temp, start_node, end_node, weight="length")
            routes.append(route2)
        except nx.NetworkXNoPath:
            pass
        all_routes = []

        for route in routes:

            # STEP 7 — Convert route nodes to coordinates
            route_coords = []

            for node in route:
                lat = graph.nodes[node]['y']
                lon = graph.nodes[node]['x']
                route_coords.append((lat, lon))

            # STEP 8 — Predict safety
            area_predictions = []

            for coord in route_coords[::10]:

                area = find_nearest_area(coord[0], coord[1])

                if area is None:
                    continue

                area_data = df[df["location"].str.lower() == area.lower()]

                if area_data.empty:
                    continue

                area_data = area_data.iloc[0]

                input_data = [[
                    area_data["crime_rate"],
                    area_data["population_density"],
                    area_data["street_light"],
                    area_data["cctv"],
                    area_data["police_distance"],
                    1,
                    1
                ]]

                prediction = model.predict(input_data)
                label = label_encoder.inverse_transform(prediction)[0]

                area_predictions.append(label)

            # STEP 9 — Calculate safety score
            score_map = {
                "Safe": 2.0,
                "Moderate": 1.5,
                "Unsafe": 1
            }

            scores = [score_map.get(p,2) for p in area_predictions]

            route_score = sum(scores)/len(scores) if scores else 0

            all_routes.append({
                "route": route_coords,
                "score": route_score
            })
        safest_route = max(all_routes, key=lambda x: x["score"])
        
        print("API RESPONSE:", {
            "start": start,
            "destination": destination,
            "safest_route_score": safest_route["score"],
            "safest_route": safest_route["route"],
            "routes_checked": len(all_routes)
        })

        return jsonify({
            "start": start,
            "destination": destination,
            "safest_route_score": safest_route["score"],
            "safest_route": safest_route["route"],
            "routes_checked": len(all_routes)
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json()
    start = data.get("start")
    destination = data.get("destination")
    predicted_score = data.get("predicted_score")
    user_rating = data.get("user_rating") # "safe" or "unsafe"
    comment = data.get("comment", "")

    try:
        with open(FEEDBACK_FILE, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerow([start, destination, predicted_score, user_rating, comment])
        return jsonify({"message": "Feedback saved successfully."})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)