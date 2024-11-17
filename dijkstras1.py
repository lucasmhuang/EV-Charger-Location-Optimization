import googlemaps
import heapq
import pandas as pd
import sys
import gmplot 
import math
from bs4 import BeautifulSoup
import folium
import gmaps
import requests


# Replace YOUR_API_KEY with the actual API key
gmaps = googlemaps.Client(key='AIzaSyBl3Rkg0qZeIFlmT6b3wonjzZNf2ENFsXg')
speed_limit_api_key = 'AIzaSyBysUEbl_ITiXRsb4WmCaXbDDg6ADEWE9M'

def geocode_address(address):
    geocode_result = gmaps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        return None
    
def reverse_geocode(lat, lng):
    result = gmaps.reverse_geocode((lat, lng))
    if result:
        return result[0]['formatted_address']
    else:
        return None

def snap_to_roads(start_location, end_location, speed_limit_api_key):
    roads_client = googlemaps.Client(speed_limit_api_key)
    path = [start_location, end_location]
    try:
        snapped_points = roads_client.snap_to_roads(path, interpolate=True)
        return snapped_points
    except Exception as e:
        print(f"Error in Snap to Roads API call: {e}")
        return None

def request_speed_limits(snapped_points, speed_limit_api_key):
    if snapped_points is None:
        return None

    place_ids = [point['placeId'] for point in snapped_points]
    roads_client = googlemaps.Client(speed_limit_api_key)
    try:
        speed_limits = roads_client.speed_limits(place_ids)
        return speed_limits
    except Exception as e:
        print(f"Error in Speed Limits API call: {e}")
        return None

def calculate_average_speed_limit(speed_limit_data):
    if speed_limit_data is None or 'speedLimits' not in speed_limit_data:
        return None

    speed_limits = [item['speedLimit'] for item in speed_limit_data['speedLimits']]
    if speed_limits:
        return sum(speed_limits) / len(speed_limits)
    else:
        return None

def filter_locations_by_distance(current_location, locations, target_distance, max_distance_diff):
    filtered_locations = []

    for location in locations:
        straight_line_distance, _ = get_distance_duration(current_location, location)
        distance_diff = abs(target_distance - straight_line_distance)

        if distance_diff <= max_distance_diff:
            filtered_locations.append(location)

    return filtered_locations


def find_suitable_location(current_location, locations, target_distance, speed_limit_api_key, max_distance_diff=10000):
    filtered_locations = filter_locations_by_distance(current_location, locations, target_distance, max_distance_diff)
    best_location_index = None
    best_penalty = float('infinity')
    best_average_speed_limit = 0

    for i, location in enumerate(filtered_locations):
        route_distance, _ = get_route_distance_duration(current_location, location)

        if route_distance is None:
            continue

        distance_diff = abs(target_distance - route_distance)

        snapped_points = snap_to_roads(current_location, location, speed_limit_api_key)
        speed_limit_data = request_speed_limits(snapped_points, speed_limit_api_key)
        average_speed_limit = calculate_average_speed_limit(speed_limit_data)

        if average_speed_limit is None:
            continue

        # Penalize routes with an average speed limit far from the desired speed (55 mph)
        speed_penalty = abs(55 - average_speed_limit)
        total_penalty = distance_diff + speed_penalty

        if total_penalty < best_penalty:
            best_penalty = total_penalty
            best_location_index = i
            best_average_speed_limit = average_speed_limit

    return best_location_index, best_average_speed_limit

def get_route_distance_duration(origin, destination):
    directions_result = gmaps.directions(origin, destination)

    if not directions_result:
        return None, None

    route = directions_result[0]
    leg = route['legs'][0]
    distance = leg['distance']['value']
    duration = leg['duration']['value']

    return distance, duration

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371e3  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) * math.sin(delta_phi / 2) +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2) * math.sin(delta_lambda / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def get_distance_duration(origin, destination):
    lat1, lon1 = origin
    lat2, lon2 = destination

    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return distance, None

def read_csv_and_get_locations(file_path):
    df = pd.read_csv(file_path)
    locations = [tuple(x) for x in df[['Latitude', 'Longitude']].to_records(index=False)]
    additional_info = df[['Station Name', 'Access Days Time', 'Cards Accepted', 'Fuel Type Code']].to_dict('records')
    return locations, additional_info

def decode_polyline(polyline_str):
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if result & 1:
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = result >> 1

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append((lat / 100000.0, lng / 100000.0))

    return coordinates


def plot_route_on_map(start_address, end_address, suitable_location_address, suitable_location_info, api_key):
    gmaps = googlemaps.Client(key=api_key)

    # Get directions between the points
    directions_to_stop = gmaps.directions(start_address, suitable_location_address)
    directions_from_stop = gmaps.directions(suitable_location_address, end_address)

    # Extract the polyline from the directions response
    polyline_to_stop = directions_to_stop[0]['overview_polyline']['points']
    polyline_from_stop = directions_from_stop[0]['overview_polyline']['points']

    # Decode the polyline
    path_to_stop = decode_polyline(polyline_to_stop)
    path_from_stop = decode_polyline(polyline_from_stop)

    gmap = gmplot.GoogleMapPlotter(path_to_stop[0][0], path_to_stop[0][1], zoom=5, apikey=api_key)

    # Plot the route
    gmap.plot(*zip(*path_to_stop), edge_width=2.5, color='blue')
    gmap.plot(*zip(*path_from_stop), edge_width=2.5, color='blue')

    gmap.marker(path_to_stop[0][0], path_to_stop[0][1], title=f"A: {start_address}", label='A')
    gmap.marker(path_from_stop[0][0], path_from_stop[0][1], title=f"B: {suitable_location_address}", label='B')
    gmap.marker(path_from_stop[-1][0], path_from_stop[-1][1], title=f"C: {end_address}", label='C')

    # Save the map as an HTML file
    gmap.draw("route_map.html")
    print(f"The map of the route from {start_address} to {end_address} with the stop at {suitable_location_address} has been saved as 'route_map.html'.")

def clean_html(html_text):
    return BeautifulSoup(html_text, 'html.parser').get_text()

def main(start_address, end_address, max_distance_miles, csv_file_path):
    start = geocode_address(start_address)
    end = geocode_address(end_address)
    speed_limit_api_key = 'AIzaSyBl3Rkg0qZeIFlmT6b3wonjzZNf2ENFsXg'
    if start is None or end is None:
        print("Unable to geocode one or both addresses. Please check the input.")
        return

    max_distance_meters = max_distance_miles * 1609.34  # Convert miles to meters
    locations, additional_info = read_csv_and_get_locations(csv_file_path)

    remaining_distance = haversine_distance(start[0], start[1], end[0], end[1])

    if remaining_distance > max_distance_meters:
        target_distance = max_distance_meters
        snapped_points = snap_to_roads(start, end, speed_limit_api_key)
        speed_limit_data = request_speed_limits(snapped_points, speed_limit_api_key)
        average_speed_limit = calculate_average_speed_limit(speed_limit_data)
        suitable_location_index, best_average_speed_limit = find_suitable_location(start, locations, target_distance, speed_limit_api_key)

        if suitable_location_index is not None:
            suitable_location = locations[suitable_location_index]
            suitable_location_info = additional_info[suitable_location_index]

            suitable_location_address = reverse_geocode(suitable_location[0], suitable_location[1])
            if suitable_location_address:
                print(f"The nearest suitable location from {start_address} with an average speed limit close to 55 mph is {suitable_location_address}.")
                print(f"Average speed limit: {best_average_speed_limit} mph")

                # Rest of the code remains the same
                # Get directions to the suitable location
                directions_to_stop = gmaps.directions(start_address, suitable_location_address)
                print("\nDirections to the suitable location:")
                directions_s=[]
                directions_f =[]
                for i, step in enumerate(directions_to_stop[0]['legs'][0]['steps']):
                    print(f"{i + 1}. {clean_html(step['html_instructions'])} ({step['distance']['text']})")
                    directions_s.append((f"{i + 1}. {clean_html(step['html_instructions'])} ({step['distance']['text']})"))
                # Get directions from the suitable location to the end location
                directions_from_stop = gmaps.directions(suitable_location_address, end_address)
                print(f"\nStop at: {suitable_location_address}")
                print("\nDirections from the suitable location to the end location:")
                for i, step in enumerate(directions_from_stop[0]['legs'][0]['steps']):
                    print(f"{i + 1}. {clean_html(step['html_instructions'])} ({step['distance']['text']})")
                    directions_f.append((f"{i + 1}.{clean_html(step['html_instructions'])} ({step['distance']['text']})"))
                # Plot the route on the map
                path_to_stop = [start] + [tuple(step['end_location'].values()) for step in directions_to_stop[0]['legs'][0]['steps']]
                path_from_stop = [tuple(step['end_location'].values()) for step in directions_from_stop[0]['legs'][0]['steps']] + [end]
                plot_route_on_map(start_address, end_address, suitable_location_address, suitable_location_info, 'AIzaSyBl3Rkg0qZeIFlmT6b3wonjzZNf2ENFsXg')

                # Return the required lists
                print(suitable_location_info)
                return directions_s , directions_f, [suitable_location_address, suitable_location_info]

            else:
                print("Unable to reverse geocode the suitable location.")
        else:
            print("No suitable location found.")
    else:
        print("You can directly reach the destination without any stops.")
        return [], [], []

# if __name__ == "__main__":
#     if len(sys.argv) != 5:
#         print("Usage: python script.py <start_address> <end_address> <max_distance>")
#         sys.exit(1)

#     file_path = sys.argv[1]
#     start_address = sys.argv[2]
#     end_address = sys.argv[3]
#     max_distance = int(sys.argv[4])
#     main(start_address, end_address, max_distance, file_path)