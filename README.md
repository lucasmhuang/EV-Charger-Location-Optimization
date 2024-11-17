## Deployment

In the project directory, run the following 2 commands:

#### `pip install -r requirements.txt`

#### `python backend.py`

This installs all dependences and runs the app. Open the URL given in your terminal to view it in your browser.\

## Task Specifics
### Routing Drivers
This script is a route planner that finds a suitable stop location between a start and end address based on the maximum range of an EV and an average speed limit close to 55 mph. It reads a CSV file containing potential charger locations and calculates the route using Google Maps API.

To run the alogrithm and obtain routing results maually:

#### `python script.py <start_address> <end_address> <max_distance_miles> <csv_file_path>`
> `<start_address>`: The starting address (e.g., "123 Main St, Anytown, USA").  
`<end_address>`: The ending address (e.g., "789 Elm St, Othertown, USA").  
`<max_distance_miles>`: The maximum distance (in miles) the vehicle can travel before needing to stop.  
`<csv_file_path>`: The path to the CSV file containing potential stop locations.

When entering routes please make sure the destination and starting location are far apart, if the locations are too close and the mileage entered is enough to get from point A to B then the routing doesn't work because of the buffer we have added for a user's range of 15-50 miles. If this happens, click back to the previous page and retry a different remaining mileage or locations.

Some example routes:
> Destination: 650 Gateway Center Dr, San Diego, CA 92102  
Current Location: 31790 Oak Ranch CT Westlake Village CA 91361  
Remaining Mileage: 100  
Total Mileage: 200

> Destination: PIER 39 The Embarcadero &, Beach St, San Francisco, CA 94133  
Current Location: 31790 Oak Ranch CT Westlake Village CA 91361  
Remaining Mileage: 200  
Total Mileage: 400

> Destination: 886 Cannery Row, Monterey, CA 93940  
Current Location: 1 UCEN Rd, Santa Barbara, CA 93106  
Remaining Mileage: 100  
Total Mileage: 200

### Predicting Charger Locations
This script is a location predictor that finds a set of optimal locations for electric vehicle chargers. It reads two CSV files. First, sales.csv which contains sales numbers for electric vehicles in California by zip code. Second, alt_fuel_stations.csv which contains existing electric vehicle charger locations in California by latitude/longitude.

To run the alogrithm and obtain optimal charger location results maually:

#### `python location_prediction_mclp.py <num_chargers> <city>`
> `<num_chargers>`: The desired number of optimal charger locations to find. Our model defaults to a value of 50.  
`<city>`: The desired city to find optimal electric vehicle charger locations within a 75 mile radius (e.g., "Los Angeles" or "San Jose").

The model outputs 3 .html maps: 
- mclp-new-coverage-map.html draws optimal charger locations with 10 mile size circles. This output is best when desiring visual results, for visualizing the coverage of the found optimal configuration of charging stations.
- mclp-new-location-map.html draws optimal charger locations with simple markers. This output is best when desiring a clean view, for detailed examination of the latitude/longitude optimal locations that the model outputs. 
- mclp.html draws both a circle and marker as detailed above for each optimal charger location.

## Known Issues

- For our route page, when entering locations the map may not refresh. You can open the 'route_map.html' in the templates folder in a browser and see that the map file creates the correct map. This visualization issue is due to how browsers handle caching; due to this, we recommend using the web browser Google Chrome to avoid such problems. If the issue persists, clear your browsers cache. 

- Due to computer enviroment differences, we encountered difficulties importing and running our predictive location algorithm file in the overall project's backend.py. Due to this, we stored our algorithm's .html map output of predicted locations locally. To verify results or utilize the algorithm with different parameters, please follow the steps outline above in "Task Specifics". 
