# Imports
import pandas as pd
import googlemaps
from datetime import datetime
import haversine as hs
import folium

# ox.settings.log_console=True
# ox.settings.use_cache=True


def convert_addresses(gmaps, start, end):
    """Converts addresses into corresponding latitude and longitude coordinates. Not necessary for implementation (gmaps automatically converts addresses) but included if needed.


    Args:
        gmaps (class): Google maps api class
        start (str): Starting address
        end (str): Destination address

    Returns:
        tup(start_coords, end_coords): Coordinates for both starting location and destination
    """

    

    start_info = gmaps.geocode(start)[0]
    end_info = gmaps.geocode(end)[0]

    start_coords = (start_info['geometry']['location']
                    ['lat'], start_info['geometry']['location']['lng'])
    end_coords = (end_info['geometry']['location']['lat'],
                  end_info['geometry']['location']['lng'])

    return start_coords, end_coords


def main_route_steps(gmaps, start_coords, end_coords):
    """Generate gmaps directions and parse out steps for a starting and ending location.

    Args:
        gmaps (class): Google maps api class
        start_coords (tuple): Coordinates corresponding to starting location
        end_coords (tuple): Coordinates corresponding to destination

    Returns:
        tup(route, steps) object: Gmaps route object and steps object
    """

    now = datetime.now()  # Will also plan to implement user defined time for planned drives
    main_route = gmaps.directions(
        start_coords, end_coords, mode="driving", departure_time=now)
    steps = main_route[0]['legs'][0]['steps']

    return main_route, steps


def distance_matrix(gmaps, curr_location, candidate_stations):
    """Create distance matrix between current location and 10 candidate stations nearby based on haversine distance.

    Args:
        gmaps (class): Google maps api class
        curr_location (tuple): Coordinates corresponding to a start of a step where a start is needed
        candidate_stations (list): List of coordinates corresponding to candidate statiosn

    Returns:
        string: Station address
    """

    dist_matrix = gmaps.distance_matrix(
        origins=curr_location, destinations=candidate_stations)

    dist_df = pd.DataFrame(dist_matrix['rows'][0]['elements'])
    dist_df['station'] = dist_matrix['destination_addresses']
    dist_df['extracted_distance'] = dist_df['distance'].apply(
        lambda x: float(x['text'].split(' ')[0]))
    dist_df.sort_values('extracted_distance', inplace=True)

    return dist_df.head(1).station.values[0]


def closest_stations(stations, curr_coords):
    """Identifies ten closest stations to current location based on haversine distance

    Args:
        stations (dataframe): Dataframe including coordinates of stations
        curr_coords (tuple): Current geolocation

    Returns:
        List: Coordinates of 10 closest stations
    """

    stations['distance_from_point'] = stations.apply(lambda row: hs.haversine(
        curr_coords, (row['Latitude'], row['Longitude']), unit=hs.Unit.MILES), axis=1)
    ten_closest_stations = stations.sort_values('distance_from_point').head(10)

    return ten_closest_stations[['Latitude', 'Longitude']].itertuples(index=False, name=None)


def get_distance(step):
    """Extract the distance (and convert units) from a particular step in a route.

    Args:
        step (object): Gmaps object corresponding to particular step in a route

    Returns:
        float: Distance of step
    """

    distance_text = step['distance']['text']
    distance = float(distance_text.split(' ')[0])

    # Convert feet to miles if necessary on any step of the route
    if 'ft' in distance_text:
        distance = distance / 5280

    return distance


# , nodes, instructions):
def identify_ev_stops(gmaps, steps, current_range, total_range, buffer, stations, end_coords, ev_stops=[]):

    # ev_stops = []

    # Iterate through steps in the route
    for step in steps:

        # Identify starting and ending locations for the route
        step_start = step['start_location']
        step_end = step['end_location']
        distance = get_distance(step)

        # If step would take EV past its range, find nearest charger and add it to the list of EV waypoints
        if distance > (current_range - buffer):

            # Establish current (starting) coordinates of step
            curr_location = (step_start['lat'], step_start['lng'])

            # Find candidate stations based on haversine distance -- prune station dataset to reduce google api queries
            candidate_stations = closest_stations(stations, curr_location)

            # Analyze candidate stations using gmaps api (distance matrix) and return the closest station
            closest_station = distance_matrix(
                gmaps, curr_location, candidate_stations)

            # Add closest station to sequence of coordinates where we need to travel --> will use this for our final route
            ev_stops.append(closest_station)

            # Reset range assuming fully charged
            current_range = total_range

        else:
            current_range -= distance

    return ev_stops


def generate_polyline_coords(steps):
    coords = []
    for step in steps:
        polyline = step['polyline']['points']
        decoded_polyline = googlemaps.convert.decode_polyline(polyline)
        coords.extend(decoded_polyline)

    processed_coordinates = list(map(lambda x: (x['lat'], x['lng']), coords))

    return processed_coordinates


def folium_map(gmaps, route, start_coords, end_coords, ev_waypoints):



    for i, waypoint in enumerate(ev_waypoints):

        
        waypoint_geocoded = gmaps.geocode(waypoint)[0]  # geocode address
        coords = [waypoint_geocoded['geometry']['location']['lat'], waypoint_geocoded['geometry']['location']['lng']]  # extract lat/longitude
        # processed_coordinates = list(map(lambda x: (x['lat'], x['lng']), coords))

        if i == 0:
            folium_map = folium.Map(location=coords)


        folium.Marker(location=coords, popup=waypoint, zoom=6.5).add_to(folium_map)

    folium.Marker(location=start_coords, popup='Origin').add_to(folium_map)
    folium.Marker(location=end_coords, popup='Destination').add_to(folium_map)


    steps = route[0]['legs'][0]['steps']

    route_coords = generate_polyline_coords(steps)

    folium.PolyLine(locations=route_coords, color='blue', weight=5).add_to(folium_map)

    folium_map.save('folium_map.html')




def main(start, end, current_range, total_range):

    # buffer range to account for variations in traffic, EV range, etc.
    buffer = 25

    # Data file
    data = pd.read_csv('./data/alt_fuel_stations_Feb_2_2023.csv')
    # Parse out only coordinates for data efficiency
    coords = data[['Latitude', 'Longitude']].copy()

    # Will need to hide this token
    with open('./api.txt') as f:
        token = f.read()

    # Initialize gmaps
    gmaps = googlemaps.Client(key=token)

    # Parse out the coordinates based on addresses --> not necessarily needed but including anyways
    start_coords, end_coords = convert_addresses(gmaps, start, end)

    # Gather route information (icluding each particular steps)
    route, steps = main_route_steps(gmaps, start_coords, end_coords)

    ev_waypoints = identify_ev_stops(
        gmaps, steps, current_range, total_range, buffer, coords, end_coords)
    
    ev_waypoints = list(map(lambda x: f'via:{x}', ev_waypoints))  # ensures that polyline doesn't stop at first destination

    # Generate final route with waypoints
    final_route = gmaps.directions(start, end, mode='driving', waypoints=ev_waypoints,
                                   departure_time=datetime.now(), optimize_waypoints=True)
    

    folium_map(gmaps, final_route, start_coords, end_coords, ev_waypoints)

    # return final_route


start_address = 'San Diego, CA'
end_address = 'Redding, CA'
total_range = 225  # average EV range based on: https://www.bloomberg.com/news/articles/2023-03-09/average-range-for-us-electric-cars-reached-a-record-291-miles#xj4y7vzkg
# value used to reset the range whenever rerouted to a EV charging station
current_range = 225


main(start_address, end_address, current_range, total_range)
