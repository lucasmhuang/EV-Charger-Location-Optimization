import pandas as pd
import numpy as np
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from operator import add
from uszipcode import SearchEngine
import gmplot
from shapely.geometry import MultiPoint, Polygon
import gurobipy as gp
from gurobipy import GRB
from geopy.distance import great_circle
from collections import defaultdict
import haversine as hs
from scipy.spatial import ConvexHull
import hdbscan
from global_land_mask import globe

def maximal_coverage(city, num_predictions=50, state="CA"):
    conf = SparkConf()
    conf.setMaster("local").setAppName("My app")
    sc = SparkContext(conf=conf)

    # Columns : ['Data Year', 'Fuel Type', 'ZIP', 'Number of Vehicles']
    data = sc.textFile("sales.csv").filter(lambda row : row.split(',')[2] != 'ZIP')
    # (zip, number of vehicles)
    # # First filter for sales in last 5 years
    data_rdd = data.filter(lambda row : int(row.split(',')[2]) >= 2018).map(lambda row : (row.split(',')[2], int(row.split(',')[3])))
    data_existing_chargers = pd.read_csv('alt_fuel_stations_Feb_2_2023.csv', usecols=['Latitude', 'Longitude'])
    existing_chargers = data_existing_chargers[['Latitude', 'Longitude']].values.tolist()

    # not real zipcodes?
    fake_zips = ["94003", "94029", "92670", "92680", "99999"]
    zipcode_sales = data_rdd.reduceByKey(add).filter(lambda row : row[0] not in fake_zips) \
        .sortBy(lambda row : -row[1]).collectAsMap()
    # https://uszipcode.readthedocs.io/01-Usage-Example/index.html
    # https://uszipcode.readthedocs.io/02-Advanced-Tutorial/index.html
    search = SearchEngine()
    source_result = search.by_city_and_state(city=city, state=state)[0]
    source_latlng = tuple([source_result.lat, source_result.lng])

    def latlng_from_zip(zipcode):
        result = search.by_zipcode(zipcode)
        return tuple([float(result.lat), float(result.lng)])
    latlng_sales = {}
    for zipcode in zipcode_sales:
        lat_lng = latlng_from_zip(zipcode)
        # https://pypi.org/project/haversine/
        if hs.haversine(source_latlng, lat_lng, unit='mi') < 75:
            latlng_sales[lat_lng] = zipcode_sales[zipcode]  
    demand_points = list(latlng_sales.keys())

    def get_centermost_point(cluster):
        centroid = (MultiPoint(cluster).centroid.x, MultiPoint(cluster).centroid.y)
        centermost_point = min(cluster, key=lambda point: great_circle(point, centroid).m)
        return tuple(centermost_point)
    charging_stations = []
    for station in existing_chargers:   
        if hs.haversine(source_latlng, station, unit='mi') < 75:
            charging_stations.append(tuple(station))

    # https://hdbscan.readthedocs.io/en/latest/api.html
    # https://hdbscan.readthedocs.io/en/latest/parameter_selection.html
    # Cluster existing charger locations to get clusters of "coverage"
    # # Haversine distance uses radians
    # # Merge clusters within a distance of 1 miles
    miles_per_radian = 3959.0
    hdbs = hdbscan.HDBSCAN(min_cluster_size=5, metric='haversine', min_samples=1, cluster_selection_epsilon=(1.0 / miles_per_radian)).fit(np.radians(charging_stations))
    # -1 cluster represents data points of noise
    clusters_chargers = sc.parallelize(hdbs.labels_).zipWithIndex().map(lambda row : (row[0], charging_stations[row[1]])) \
        .groupByKey().map(lambda row : (row[0], list(row[1])))            
    # find the point in each cluster that is closest to its centroid
    charger_cluster_center_points = clusters_chargers.filter(lambda row : row[0] != -1).map(lambda row : get_centermost_point(row[1])).collect()

    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html
    # https://shapely.readthedocs.io/en/stable/manual.html#shapely.geometry.shape
    # Get potental locations, points within the grid formed by demand points
    # # Our grid has points spaced 0.07 degrees (about 5 miles) apart
    convex_hull = ConvexHull(demand_points)
    # # (min x, min y, max x, max y) where x = lat, y = lng
    demand_points_shape = list(Polygon([demand_points[idx] for idx in convex_hull.vertices]).bounds)
    lat_min = demand_points_shape[0]
    lat_max = demand_points_shape[2]
    lon_min = demand_points_shape[1]
    lon_max = demand_points_shape[3]
    lat = lat_min
    lon = lon_min
    potential_locations = []
    while True:
        if lon > lon_max:
            break
        lat = lat_min
        while True:
            if lat > lat_max:
                break
            # Make sure our potential location is on land (not in the ocean)
            if globe.is_land(lat, lon):
                potential_locations.append(tuple([lat, lon]))
            lat += 0.07
        lon += 0.07

    # https://www.gurobi.com/documentation/9.5/refman/py_model2.html    
    model = gp.Model("MCLP")
    # Add all potential locations as x variables
    # # 1 if location is used in optimal solution, 0 if not
    x = {}
    for charger_idx in range(len(potential_locations)):
        x[charger_idx] = model.addVar(vtype=GRB.BINARY, name="x_" + str(charger_idx))
    # Add all demand nodes as y variables
    # # 1 when covered, 0 when not
    y = {}
    for location_idx in range(len(demand_points)):
        y[location_idx] = model.addVar(vtype=GRB.BINARY, name="y_" + str(location_idx))
    
    # Map demand points to all potential charging locations within 10 miles, which is our criteria for coverage
    valid_locations = defaultdict(set)
    for demand_point in range(len(demand_points)):
        for location in range(len(potential_locations)):  
            if hs.haversine(demand_points[demand_point], potential_locations[location], unit='mi') < 10:
                valid_locations[demand_point].add(location)

    # Create two constraints for our MCLP 
    # # len(number of valid locations) >= y for every demand point
    for demand_point in range(len(demand_points)):
        # # if 1+ valid locations, our condition is true
        if valid_locations[demand_point]:
            model.addConstr(sum([x[potential_location] for potential_location in valid_locations[demand_point]]) >= y[demand_point])
        # # if 0 valid locations, y should be 0 to represent not covered
        else:
            model.addConstr(y[demand_point] == 0)
    # # Number of final predicted locations
    model.addConstr(sum([x[location] for location in range(len(potential_locations))]) == num_predictions)
    
    # Maximize population covered
    # # Maximize total sum over all demand locations: (sales in location) * (1 if covered, 0 if not covered)
    model.setObjective(sum([latlng_sales[demand_points[point]] * y[point] for point in range(len(demand_points))]), GRB.MAXIMIZE)
    model.update()
    model.optimize()

    # https://www.gurobi.com/documentation/10.0/quickstart_windows/cs_example_mip1_py.html
    final_charger_locations = []
    final_covered_locations = []
    for v in model.getVars():
        curr_variable = v.varName.split("_")
        if curr_variable[0] == "x" and v.X == 1:
            final_charger_locations.append(int(curr_variable[1]))
        elif curr_variable[0] == "y" and v.X == 1:
            final_covered_locations.append(int(curr_variable[1]))

    print("{:,} charger points clustered to {:,} points, {:.3f}.".format(len(charging_stations), len(charger_cluster_center_points), len(charger_cluster_center_points) / len(charging_stations)))
    print("Model considered {:,} potential locations for new chargers.".format(len(potential_locations)))    
    print("{:,} optimal charger locations found.".format(len(final_charger_locations)))    
    print("{:,} demand points covered at conclusion of model, {:.3f}.".format(len(final_covered_locations), len(final_covered_locations) / len(demand_points))) 
    
    final_predicted_locations = [potential_locations[location] for location in final_charger_locations]

    miles_per_meter = 0.000621371
    def scatter_new_coverage():
        gmap = gmplot.GoogleMapPlotter(lat=source_latlng[0], lng=source_latlng[1], zoom=10, apikey=apikey)
        gmap.scatter(*zip(*final_predicted_locations), color='red', marker=False, size=(10.0 / miles_per_meter))
        gmap.scatter(*zip(*charger_cluster_center_points), color='green', marker=True)
        gmap.draw('mclp-new-coverage-map.html')    
    def scatter_new_marker():
        gmap = gmplot.GoogleMapPlotter(lat=source_latlng[0], lng=source_latlng[1], zoom=10, apikey=apikey)
        gmap.scatter(*zip(*final_predicted_locations), color='red', marker=True)
        gmap.scatter(*zip(*charger_cluster_center_points), color='green', marker=True)
        gmap.draw('mclp-new-location-map.html')    
    def scatter_new_both():
        gmap = gmplot.GoogleMapPlotter(lat=source_latlng[0], lng=source_latlng[1], zoom=10, apikey=apikey)
        gmap.scatter(*zip(*final_predicted_locations), color='red', marker=True)
        gmap.scatter(*zip(*final_predicted_locations), color='red', marker=False, size=(10.0 / miles_per_meter))
        gmap.scatter(*zip(*charger_cluster_center_points), color='green', marker=True)
        gmap.draw('mclp.html')    
    scatter_new_coverage()
    scatter_new_marker()
    scatter_new_both()

def main():
    import sys
    input_numpreds = int(sys.argv[1])
    input_city = ' '.join(sys.argv[2:])
    maximal_coverage(city=input_city, num_predictions=input_numpreds)

if __name__ == "__main__":
    main()
