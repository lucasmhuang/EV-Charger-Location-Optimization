from flask import Flask, render_template, request, url_for, redirect, session, send_from_directory
from io import BytesIO
import base64
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import googlemaps
import dijkstras
import dijkstras1
#import kmeans_code
##################################################
# 	Normal Python Code to Call in Flask Code	 #
##################################################
# copy and paste -> command, shift , v

def sales_by_county(county):
	img = BytesIO()
	sns.set_theme()
	plt.rcParams["figure.figsize"] = (20,5)
	sales = pd.read_excel('New_ZEV_Sales.xlsx', sheet_name='County')
	county_sales = sales[sales["County"] == county]
	sales_by_make = county_sales.groupby('MAKE')['Number of Vehicles'].sum().sort_values(ascending=False)[:20]
	sns.barplot(x=sales_by_make, y=sales_by_make.index).set(title='Top EV Car Sales in '+ county)
	plt.savefig(img, format='png')
	plt.close()
	img.seek(0)
	plot_url = base64.b64encode(img.getvalue()).decode('utf8')

	return plot_url

def sales_all_counties():
	img = BytesIO()
	sns.set_theme()
	plt.rcParams["figure.figsize"] = (20,5)
	sales = pd.read_excel('New_ZEV_Sales.xlsx', sheet_name='County')
	top_ten_counties = sales.groupby('County')['Number of Vehicles'].sum().sort_values(ascending=False)[:20]
	sns.barplot(x=top_ten_counties, y=top_ten_counties.index).set(title='Top Counties for EV Sales')
	plt.savefig(img, format='png')
	plt.close()
	img.seek(0)
	plot_url = base64.b64encode(img.getvalue()).decode('utf8')
	return plot_url

def all_chargers():
	img = BytesIO()
	sns.set_theme()
	plt.rcParams["figure.figsize"] = (20,5)
	chargers = pd.read_csv('alt_fuel_stations.csv')


	chargers["Open Date"] = chargers["Open Date"].fillna(0)
	years =[]
	for x in chargers["Open Date"]:
		if x != 0:
			y = x.split("-")
			year = int(y[0])
			years.append(year)
		else:
			y = 0
			years.append(y)
	chargers["Years"] = years
	chargeryears = chargers[chargers["Years"] != 0]
	charger_years = chargeryears.groupby('Years')['ID'].sum()
	sns.lineplot(x=charger_years.index, y=charger_years).set(title='CA Charger Stations Over Time')
	plt.savefig(img, format='png')
	plt.close()
	img.seek(0)
	plot_url = base64.b64encode(img.getvalue()).decode('utf8')
	return plot_url
    
def chargers_county(county):
	img = BytesIO()
	sns.set_theme()
	plt.rcParams["figure.figsize"] = (20,5)
	chargers = pd.read_csv('alt_fuel_stations.csv')


	chargers["Open Date"] = chargers["Open Date"].fillna(0)
	years =[]
	for x in chargers["Open Date"]:
		if x != 0:
			y = x.split("-")
			year = int(y[0])
			years.append(year)
		else:
			y = 0
			years.append(y)
	chargers["Years"] = years
	chargers_city = chargers[chargers["City"] == county]
	chargeryears = chargers_city[chargers_city["Years"] != 0]
	charger_years = chargeryears.groupby('Years')['ID'].sum()
	sns.lineplot(x=charger_years.index, y=charger_years).set(title= county+' Charger Stations Over Time')
	plt.savefig(img, format='png')
	plt.close()
	img.seek(0)
	plot_url = base64.b64encode(img.getvalue()).decode('utf8')
	return plot_url


##################################################
# 					Flask Code	 				 #
##################################################

app = Flask(__name__)

# starting page (pick between user and company)
@app.route('/', methods=['POST', 'GET'])
def ind():
	
	if request.method == 'POST':
		if request.form['action'] == 'user':
			return redirect('index')
		elif request.form['action'] == 'company':
			return redirect("location")
		else:
			return render_template("start.html")

	return render_template("start.html")

# First page for user where they enter the info
@app.route('/index')
def ind1():

	# this method gets the info they enter
	if request.method == "POST":
		dest = request.form.get("dest")
		current = request.form.get("current")
		remain = request.form.get("remain")
		total = request.form.get("total")

		# this sends the info to the page where their routing is displayed
		return redirect(url_for('route', dest = dest, cur=current, rem= remain, total=total))
		#return render_template("route.html", dest = dest)
	#else:
	return render_template("index.html")

# This is the second page after the user enters their info
# This will display their route
@app.route('/route', methods=['POST', 'GET'])
def route():
	dest = request.form.get("dest")
	cur = request.form.get("current")
	rem = request.form.get("remain")
	total = request.form.get("total")

	start,destination, charger = dijkstras.main(cur,dest, int(rem), 'alt_fuel_stations.csv')
	
	t=charger[1]['Access Days Time']
	p=charger[1]['Cards Accepted']
	c= charger[1]['Fuel Type Code']

	if p !=str():
		p ="Not Available"
	# if c!= '':
	# 	c="Not Available"
	# if t != '':
	# 	t="Not Available"

	return render_template("route.html", dest = dest, cur=cur, rem=rem, start = start, charger = charger,t=t,p=p, c=c, destination = destination)

@app.route('/route_map')
def route_map():
		return send_from_directory('templates', 'route_map.html')

# @app.route('/recLA')
# def recLA():
# 		return send_from_directory('templates', 'recLA.html')

# @app.route('/recV')
# def recV():
# 		return send_from_directory('templates', 'recV.html')
# this is for displaying general data about sales or chargers

@app.route('/rec22)')
def rec22():
		return send_from_directory('templates', 'rec22.html')

@app.route('/rec1)')
def rec1():
		return send_from_directory('templates', 'rec1.html')

@app.route('/rec2)')
def rec2():
		return send_from_directory('templates', 'rec2.html')

@app.route('/rec3)')
def rec3():
		return send_from_directory('templates', 'rec3.html')

@app.route('/rec4)')
def rec4():
		return send_from_directory('templates', 'rec4.html')

@app.route('/rec5)')
def rec5():
		return send_from_directory('templates', 'rec5.html')

@app.route('/rec6)')
def rec6():
		return send_from_directory('templates', 'rec6.html')

@app.route('/rec7)')
def rec7():
		return send_from_directory('templates', 'rec7.html')

@app.route('/rec8)')
def rec8():
		return send_from_directory('templates', 'rec8.html')

@app.route('/rec9)')
def rec9():
		return send_from_directory('templates', 'rec9.html')

@app.route('/rec10)')
def rec10():
		return send_from_directory('templates', 'rec10.html')

@app.route('/rec11)')
def rec11():
		return send_from_directory('templates', 'rec11.html')


@app.route('/rec12)')
def rec12():
		return send_from_directory('templates', 'rec12.html')

@app.route('/rec13)')
def rec13():
		return send_from_directory('templates', 'rec13.html')

@app.route('/rec14)')
def rec14():
		return send_from_directory('templates', 'rec14.html')

@app.route('/rec15)')
def rec15():
		return send_from_directory('templates', 'rec15.html')

@app.route('/rec16)')
def rec16():
		return send_from_directory('templates', 'rec16.html')

@app.route('/rec17)')
def rec17():
		return send_from_directory('templates', 'rec17.html')

@app.route('/rec18)')
def rec18():
		return send_from_directory('templates', 'rec18.html')

@app.route('/rec19)')
def rec19():
		return send_from_directory('templates', 'rec19.html')

@app.route('/rec20)')
def rec20():
		return send_from_directory('templates', 'rec20.html')

@app.route('/rec21)')
def rec21():
		return send_from_directory('templates', 'rec21.html')


@app.route('/visual', methods=['POST', 'GET'])
def visual():
	if request.method == "POST":
		c = request.form.get("countyL")
		g = request.form.get("graphs")

		
		#session["dest"] = dest
		print(dest)
		return redirect(url_for('route', c =c, g=g ))
	allCounties = sales_all_counties()
	locations = ['Los Angeles', 'Orange', 'San Bernardino', 'San Mateo', 'Santa Barbara', 'Tulare', 'Ventura', 'Placer', 'Napa', 'Sacramento', 'Alameda', 'Contra Costa', 'Humboldt', 'Kern', 'Marin', 'San Diego', 'San Francisco', 'San Luis Obispo', 'Santa Clara', 'Sonoma', 'Stanislaus', 'Yolo', 'Amador', 'Fresno', 'Lake', 'Monterey', 'Riverside', 'San Benito', 'San Joaquin', 'Santa Cruz', 'Butte', 'Calaveras', 'Del Norte', 'El Dorado', 'Imperial', 'Kings', 'Lassen', 'Madera', 'Mariposa', 'Mendocino', 'Merced', 'Nevada', 'Shasta', 'Solano', 'Tehama', 'Trinity', 'Tuolumne', 'Yuba', 'Inyo', 'Plumas', 'Siskiyou', 'Sutter', 'Alpine', 'Glenn', 'Mono', 'Colusa', 'Modoc', 'Sierra']
	graphs = ["Sales Data", "Charger Data"]
	return render_template('visual.html', countyL = locations, graphs = graphs, gr = allCounties)
	
# This page is for the kmeans
@app.route('/location', methods =['POST', 'GET'])
def location():

	if request.method == "POST":
		county = request.form.get("countyL")
		print(c)
		return redirect(url_for('predict', c = county))

	#locations = ['Los Angeles', 'Ventura','Orange', 'Santa Barbara', 'Sacramento', 'San Diego', 'San Francisco', 'San Luis Obispo', 'Santa Clara', 'Monterey', 'Riverside', 'Santa Cruz']
	locations = ['Los Angeles', 'Orange', 'San Bernardino', 'San Mateo', 'Santa Barbara', 'Ventura', 'Napa', 'Sacramento', 'Alameda', 'Marin', 'San Diego', 'San Francisco', 'San Luis Obispo', 'Santa Clara', 'Sonoma','Monterey', 'Riverside', 'Santa Cruz',  'Mariposa', 'Mendocino', 'Merced', 'Sierra']

	return render_template('location.html', countyL = locations)


# this page is for the kmeans results
@app.route('/predict', methods=["POST", "GET"])
def predict():
	c = request.form.get("countyL")

	if c == 'Los Angeles':
		mp='rec22'
	if c == 'Orange':
		mp = 'rec1'
	if c == 'San Bernardino':
		mp = 'rec2'
	if c == 'San Mateo':
		mp = 'rec3'
	if c == 'Santa Barbara':
		mp ='rec4'
	if c == 'Ventura':
		mp ='rec5'
	if c == 'Napa':
		mp ='rec6'
	if c=='Sacramento':
		mp='rec7'
	if c=='Alameda':
		mp='rec8'
	if c=='Marin':
		mp='rec9'
	if c=='San Diego':
		mp='rec10'
	if c=='San Francisco':
		mp='rec11'
	if c=='San Luis Obispo':
		mp='rec12'
	if c=='Santa Clara':
		mp='rec13'
	if c=='Sonoma':
		mp='rec14'
	if c=='Monterey':
		mp='rec15'
	if c=='Riverside':
		mp='rec16'
	if c=='Santa Cruz':
		mp='rec17'
	if c=='Mariposa':
		mp='rec18'
	if c=='Mendocino':
		mp='rec19'
	if c=='Merced':
		mp='rec20'
	if c=='Sierra':
		mp='rec21'
	#kmeans_code.main()

	return render_template('predict.html', c=c, mp=mp)




# this page is for displaying the data 
@app.route('/graph', methods=['POST', 'GET'])
def graph():
	c = request.form.get("countyL")
	g = request.form.get("graphs")
	if g=="Sales Data":
		allCounties = sales_all_counties()
		counties = sales_by_county(c)
	elif g =="Charger Data":
		counties= chargers_county(c)
		allCounties=all_chargers()

	#cars = ['Mustang: 500', 'Toyota: 400', 'Range Rover: 300', 'Tesla: 200', 'Lucid: 100']

	return render_template('graph.html', c=c, g=g, a = allCounties, cs = counties)






if __name__ == '__main__':
   app.run()
