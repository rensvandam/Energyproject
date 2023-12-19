# -*- coding: utf-8 -*-
"""
Created on Sat Oct 14 20:12:38 2023

@author: Rens van Dam

HOMEBATTERY PROJECT


GOAL:
    
1. Lees live energieprijzen van internet en laad deze in.
2. Vergelijk prijs met verbruik van huis.
3. bereken benodigde batterijcapaciteit op dure uren.
4. plan in welke uren je de batterij hiervoor wil opladen.

"""
from gekko import GEKKO
import numpy as np
import matplotlib.pyplot as plt
import schedule
import time
import requests
from bs4 import BeautifulSoup
import datetime

#%% load price data

def get_price_url():
    
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    yesterday_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    print(current_date)
    # Original URL
    url = 'https://www.epexspot.com/en/market-data?market_area=NL&trading_date=2023-09-02&delivery_date=2023-09-03&underlying_year=&modality=Auction&sub_modality=DayAhead&technology=&product=60&data_mode=table&period=&production_period='
    
    # Replace the dates in the URL with the current date and yesterday's date
    new_url = url.replace('2023-09-02', yesterday_date).replace('2023-09-03', current_date)

    
    return new_url


def extract_prices():
    """ 
    Extracts the current spotprices from the EPEX market.
    """ 
    
    #The URL. This changes 
    url = get_price_url()
    # Send an HTTP GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the <div> element containing the data
        div = soup.find('div', class_='js-table-values')  # Replace 'your-div-class' with the actual class name
        
        if div:
            # Find the <thead> element
            table = div.find('table')
            
            if table:
                # Find the <tbody> element
                tbody = table.find('tbody')
                
                if tbody:
                    # Find all <tr> elements within the <tbody>
                    rows = tbody.find_all('tr')
                    
                    # Initialize a list to store the extracted numbers
                    extracted_numbers = []
                    
                    # Iterate through each <tr> element
                    for row in rows:
                        # Find the <td> element within the <tr>
                        td_elements = row.find_all('td')
                    
                        if len(td_elements) >= 4:
                            # Extract the text content from the last <td> element
                            last_td = td_elements[-1]
                            cell_text = last_td.text.strip()
                            
                            extracted_numbers.append(cell_text)
                        
                        # Print the extracted numbers
                        #print(extracted_numbers)
            
                    else:
                        print("No <tbody> found")
                else:
                    print("No <table> found")
            else:
                print("No <thead> found")
        else:
            print("No <div> found")
    else:
        print("Failed to fetch the webpage")
        
    #changing it from strings to floats
    extracted_prices = [float(num_str) for num_str in extracted_numbers]

    return extracted_prices


#%% GEKKO MODEL

R = 2 #kWh, max charging per hour
C = 10 # kWh, battery capacity

#house demand
p = [0.3, 0.13, 0.13, 0.17, 0.22, 0.3, 0.57, 0.7, 0.65, 0.52, 0.39, 0.35, 0.3, 0.35, 0.39, 0.35, 0.39, 0.65, 0.87, 0.83, 0.78, 0.7, 0.52, 0.39]

print(sum(p))
#prices
#c = [0.069, 0.034, 0.00583, 0.00911, 0.0057599999999999995, 0.00767, 0.00579, 0.04683, 0.06904, 0.078, 0.04111, -0.00101, -0.00439, -0.00103, -0.0070999999999999995, 0.004860000000000001, 0.03364, 0.11159999999999999, 0.16083, 0.18763, 0.194, 0.145, 0.1368, 0.1356]
c = extract_prices() #live EPEX market energy prices
c = [item / 1000 for item in c]

m = GEKKO()
s = m.Array(m.Var,(24), lb=0, ub=R)
d = m.Array(m.Var,(24), lb=0, ub=R)

n=24
e = 0.8 #efficiency of battery charging

for i in range(n):
    if i == 0:
        m.Equation(d[i] - e * s[i] <= 0)
    else:
        sum_d = sum(d[j] for j in range(i + 1))
        sum_s = sum(s[j] for j in range(i + 1))
        m.Equation(sum_d - sum_s <= 0)

for i in range(n):
    if i == 0:
        m.Equation(s[i] - d[i] * e**(-1) <= C)
    else:
        sum_d = sum(d[j] for j in range(i + 1))
        sum_s = sum(s[j] for j in range(i + 1))
        m.Equation(sum_s - sum_d <= C)

m.Obj(sum((p+s-d)*c))
m.solve(disp=False)

s = [float(s[i].value[0]) for i in np.arange(len(c))]
d = [float(d[i].value[0]) for i in np.arange(len(c))]



#GRAPHING

fig, axs = plt.subplots(1, 3, figsize=(15, 5), facecolor='black')

hour_ticks = np.arange(0, 25, 4)
hour_labels = [str(i) + ':00' for i in hour_ticks]
 
# Plot price
axs[0].bar(np.arange(0, 24)+0.5, c, align='center', width=0.8, color='lightblue')
axs[0].set_title('Price  ('+str(datetime.datetime.now().strftime('%Y-%m-%d'))+')', color='white')
axs[0].set_xlabel('Time (hours)', color='white')
axs[0].set_ylabel('Price (EUR/kWh)', color='white')
axs[0].tick_params(axis='x', colors='white')
axs[0].tick_params(axis='y', colors='white')
axs[0].set_xticks(hour_ticks)
axs[0].set_xticklabels(hour_labels)
# Plot charge
axs[1].bar(np.arange(0, 24)+0.5, [s[i] - d[i] for i in np.arange(0,24)], align='center', width=0.8, color='lightpink')
axs[1].set_title('Battery charging and discharging', color='white')
axs[1].set_xlabel('Time (hours)', color='white')
axs[1].set_ylabel('Battery capacity (kWh)', color='white')
axs[1].tick_params(axis='x', colors='white')
axs[1].tick_params(axis='y', colors='white')
axs[1].set_xticks(hour_ticks)
axs[1].set_xticklabels(hour_labels)
 
# Plot discharge
axs[2].bar(np.arange(0, 24)+0.5, p, align='center', width=0.8, color='mediumaquamarine')
axs[2].set_title('Electricity usage', color='white')
axs[2].set_xlabel('Time (hours)', color='white')
axs[2].set_ylabel('To grid (kWh)', color='white')
axs[2].tick_params(axis='x', colors='white')
axs[2].tick_params(axis='y', colors='white')
axs[2].set_xticks(hour_ticks)
axs[2].set_xticklabels(hour_labels)

# Set the background color to black
for ax in axs:
    ax.set_facecolor('black')
    ax.grid(color='white', linestyle='dotted', linewidth=0.5)   
 
# Adjust layout and display the plot
plt.tight_layout()
plt.show()


moneyz = sum([c[i]*(s[i] - d[i]) for i in np.arange(0,24)])
print("EUROS BESPAARD:", moneyz)