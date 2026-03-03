import folium
import os
import pandas as pd
import requests
import time

# Mapbox API token
MAPBOX_TOKEN = 'pk.eyJ1Ijoicm9kdmlsbGFyZWFsIiwiYSI6ImNtMXppcjNtNDA3aG4yam9idjU4eWdxZjUifQ.Rp18zrkadGvSnUpvFKb7AQ'

def geocode_address(address):
    """
    Geocode an address using Mapbox Geocoding API
    Returns (latitude, longitude) tuple or None if geocoding fails
    """
    base_url = 'https://api.mapbox.com/geocoding/v5/mapbox.places/'
    
    # URL encode the address
    encoded_address = requests.utils.quote(address)
    
    # Construct the full URL
    url = f'{base_url}{encoded_address}.json?access_token={MAPBOX_TOKEN}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data['features']:
            # Get the first result's coordinates [longitude, latitude]
            coords = data['features'][0]['center']
            # Return as [latitude, longitude] for folium
            return (coords[1], coords[0])
        else:
            print(f"No results found for: {address}")
            return None
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
        return None

# Read the CSV file
csv_file = '../McAllen CSV.csv'
df = pd.read_csv(csv_file)

# Add columns for coordinates
df['Latitude'] = None
df['Longitude'] = None

# Geocode each address
print("Geocoding addresses...")
for index, row in df.iterrows():
    address = row['Address']
    print(f"Geocoding: {address}")
    
    coords = geocode_address(address)
    if coords:
        df.at[index, 'Latitude'] = coords[0]
        df.at[index, 'Longitude'] = coords[1]
        print(f"  -> Success: {coords}")
    else:
        print(f"  -> Failed")
    
    # Add a small delay to avoid rate limiting
    time.sleep(0.5)

# Calculate the center point (average of all coordinates)
valid_coords = df[df['Latitude'].notna()]
if len(valid_coords) > 0:
    center_lat = valid_coords['Latitude'].mean()
    center_lon = valid_coords['Longitude'].mean()
    hometown_coords = [center_lat, center_lon]
else:
    # Default to McAllen, TX
    hometown_coords = [26.2034, -98.2300]

# Custom Mapbox style URL
MAPBOX_STYLE_ID = 'rodvillareal/cmm3n85w500lj01s3dqzg2osm'
MAPBOX_TILES_URL = (
    f'https://api.mapbox.com/styles/v1/{MAPBOX_STYLE_ID}/tiles/256/{{z}}/{{x}}/{{y}}@2x'
    f'?access_token={MAPBOX_TOKEN}'
)

# Create the map with the custom Mapbox basemap
m = folium.Map(
    location=hometown_coords,
    zoom_start=13,
    tiles=MAPBOX_TILES_URL,
    attr='© <a href="https://www.mapbox.com/">Mapbox</a>'
)

# Style map: color + Font Awesome icon per location type
# Colors: 'red','blue','green','purple','orange','darkred','lightred','beige',
#         'darkblue','darkgreen','cadetblue','darkpurple','white','pink',
#         'lightblue','lightgreen','gray','black','lightgray'
type_style_map = {
    'Church':        {'color': 'blue',       'icon': 'cross',         'prefix': 'fa'},
    'High School':   {'color': 'green',      'icon': 'graduation-cap','prefix': 'fa'},
    'Park':          {'color': 'lightgreen', 'icon': 'tree',          'prefix': 'fa'},
    'Country Club':  {'color': 'orange',     'icon': 'flag',          'prefix': 'fa'},
    'Gym':           {'color': 'red',        'icon': 'heartbeat',     'prefix': 'fa'},
    'Book store':    {'color': 'purple',     'icon': 'book',          'prefix': 'fa'},
    'Movie theater': {'color': 'cadetblue',  'icon': 'film',          'prefix': 'fa'},
    'Museum':        {'color': 'darkblue',   'icon': 'university',    'prefix': 'fa'},
}

# Add markers for each location
for index, row in df.iterrows():
    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
        location = [row['Latitude'], row['Longitude']]
        place_type = str(row['Type']).strip()
        style   = type_style_map.get(place_type, {'color': 'gray', 'icon': 'map-marker', 'prefix': 'fa'})
        color   = style['color']
        icon    = style['icon']
        prefix  = style['prefix']
        
        # Build image HTML — the CSV stores a base64 data URI in 'Image URL'
        image_url = str(row.get('Image URL', '')).strip()
        if image_url and image_url.lower() != 'nan':
            image_html = (
                f'<img src="{image_url}" '
                f'style="width:100%; height:160px; object-fit:cover; '
                f'border-radius:6px 6px 0 0; display:block;" '
                f'alt="{row["Name"]}">'
            )
        else:
            image_html = ''

        # Rich popup: image → name banner → description
        popup_html = f"""
        <div style="
            width: 260px;
            font-family: Arial, sans-serif;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        ">
            {image_html}
            <div style="padding: 10px 12px 12px;">
                <h3 style="margin: 0 0 4px; font-size: 15px; color: #1a1a2e;">
                    {row['Name']}
                </h3>
                <p style="
                    margin: 0 0 8px;
                    font-size: 11px;
                    color: #666;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                ">
                    {str(row['Type']).strip()}
                </p>
                <p style="margin: 0; font-size: 12px; color: #333; line-height: 1.5;">
                    {row['Description']}
                </p>
            </div>
        </div>
        """

        folium.Marker(
            location=location,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"<b>{row['Name']}</b> — {str(row['Type']).strip()}",
            icon=folium.Icon(color=color, icon=icon, prefix=prefix)
        ).add_to(m)

# Save the geocoded data back to CSV
output_csv = '../McAllen CSV_geocoded.csv'
df.to_csv(output_csv, index=False)
print(f"\nGeocoded data saved to: {output_csv}")

# Save the map as an HTML file in the portfolio root (one level up from /images)
output_html = os.path.join(os.path.dirname(__file__), '..', 'hometown_map.html')
output_html = os.path.abspath(output_html)
m.save(output_html)

# Inject a descriptive <title> into the saved HTML
with open(output_html, 'r', encoding='utf-8') as f:
    html_content = f.read()
html_content = html_content.replace(
    '<head>',
    '<head>\n    <title>My Hometown Map — McAllen, TX</title>',
    1
)
with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\nMap saved to: {output_html}")
print("Open 'hometown_map.html' in a browser to view your interactive map.")
print(f"Total locations plotted: {len(valid_coords)}/{len(df)}")

