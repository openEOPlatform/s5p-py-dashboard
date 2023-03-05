# Load required packages
from pathlib import Path
from shiny import App, render, ui, reactive
import openeo, json, asyncio, sys, rasterio, imageio, os, re, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import date
from shiny.types import ImgData

# openeo connection and authentication 
# https://open-eo.github.io/openeo-python-client/auth.html
## In Linux terminal :
## openeo-auth oidc-auth openeo.cloud
con = openeo.connect("openeo.cloud")
con.authenticate_oidc()

# Define User Interface
app_ui = ui.page_fluid(
  
  # Title of App
  ui.panel_title("SENTINEL 5P (TROPOMI) DATA ANALYSER"),
  
  # Define that we're working with a shiny with different tabs
  ui.navset_tab(
        # Tab1 : Home Screen
        ui.nav("Home", 
        
        # Some informative text
        ui.h1("Welcome to SENTINEL 5P data analyser"),
        ui.h4("Here you may find three different framework to deeply look into SENTINEL 5P NO2 data. "),
        ui.h4("There are three frameworks free for you to use:"),
        ui.h4("the Time-Series Analyser, the Map Maker and the Spacetime Animation one."),
        
        # logo from WWU, ESA and openEO 
        ui.img(src="img.png")
        ), #end of nav
        
        # Tab2 : Time Series Analyser
        ui.nav("Time-Series Analyser", 
        
        # This tab has both a sidebar and panel
        ui.layout_sidebar(
        
          # Define Sidebar Inputs
          ui.panel_sidebar(
            
            # Bounding Box
            ui.input_numeric("w", "xmin (EPSG:4326)", 10.35, min = 0, step = .01),
            ui.input_numeric("s", "ymin (EPSG:4326)", 46.10, min = 0, step = .01),
            ui.input_numeric("e", "xmax (EPSG:4326)", 12.55, min = 0, step = .01),
            ui.input_numeric("n", "ymax (EPSG:4326)", 47.13, min = 0, step = .01),
            
            # Temporal Filter
            ui.input_date_range("date1date2", "Select timeframe", start = "2019-01-01", end = "2019-12-31",
                         min = "2019-01-01", max = str(date.today()), startview =  "year", weekstart = "1"),
                         
            # Cloud Cover 
            ui.input_numeric("cloud1", "cloud cover to be considered? (0 to 1 - 0.5 is recommended)", 0.5, min = 0, max = 1, step = .1),

            # Submit Button
            ui.input_action_button("data1", "Submit")
            
          ),
          # Time Series Plot
          ui.panel_main(
            ui.output_plot("plot_ts")
          ),
        ),
      ),
      
      ui.nav("Map Maker", 
      # This tab has both a sidebar and panel
        ui.layout_sidebar(
        
          # Define Sidebar Inputs
          ui.panel_sidebar(
            
            # Bounding Box
            ui.input_numeric("w2", "xmin (EPSG:4326)", 10.35, min = 0, step = .01),
            ui.input_numeric("s2", "ymin (EPSG:4326)", 46.10, min = 0, step = .01),
            ui.input_numeric("e2", "xmax (EPSG:4326)", 12.55, min = 0, step = .01),
            ui.input_numeric("n2", "ymax (EPSG:4326)", 47.13, min = 0, step = .01),
            
            # Temporal Filter
            ui.input_date_range("date1date22", "Select timeframe for interpolation", 
            start = "2019-01-01", end = "2019-12-31",
            min = "2019-01-01", max = str(date.today()), startview =  "year", weekstart = "1"),
            
            # Date for Plot
            ui.input_date("date", "Select Date of the Slice", startview='year', value="2019-07-15",
            min = "2019-01-01", max = str(date.today())),
                         
            # Cloud Cover 
            ui.input_numeric("cloud2", "cloud cover to be considered? (0 to 1 - 0.5 is recommended)", 0.5, min = 0, max = 1, step = .1),

            # Submit Button
            ui.input_action_button("data2", "Submit")
            
          ),
          # Time Series Plot
          ui.panel_main(
            ui.output_plot("plot_map")
          ),
        ),
      ),
      
       ui.nav("Spacetime Animation", 
      # This tab has both a sidebar and panel
        ui.layout_sidebar(
        
          # Define Sidebar Inputs
          ui.panel_sidebar(
            
            # Bounding Box
            ui.input_numeric("w3", "xmin (EPSG:4326)", 10.35, min = 0, step = .01),
            ui.input_numeric("s3", "ymin (EPSG:4326)", 46.10, min = 0, step = .01),
            ui.input_numeric("e3", "xmax (EPSG:4326)", 12.55, min = 0, step = .01),
            ui.input_numeric("n3", "ymax (EPSG:4326)", 47.13, min = 0, step = .01),
            
            # Temporal Filter
            ui.input_date_range("date1date23", "Select timeframe", start = "2019-07-01", end = "2019-07-31",
                         min = "2019-01-01", max = str(date.today()), startview =  "year", weekstart = "1"),
                         
            # Cloud Cover 
            ui.input_numeric("cloud3", "cloud cover to be considered? (0 to 1 - 0.5 is recommended)", 0.5, min = 0, max = 1, step = .1),

            # Cloud Cover 
            ui.input_numeric("fps", "Frames per Second", 2, min = 1, max = 80, step = 10),
            # Submit Button
            ui.input_action_button("data3", "Submit")
            
          ),
          # Time Series Plot
          ui.panel_main(
            ui.output_image("image")
          ),
        ),
      )
    )
  )


def server(input, output, session):
    @output
    @render.plot
    @reactive.event(input.data1) 
    async def plot_ts():
      
      # Define the Spatial Extent
      extent = { # Münster
        "type": "Polygon",
        "coordinates": [[
          [input.w(), input.n()],
          [input.e(), input.n()],
          [input.e(), input.s()],
          [input.w(), input.s()],
          [input.w(), input.n()]
          ]]
          }
          
      # Build the Datacube    
      datacube = con.load_collection(
        "TERRASCOPE_S5P_L3_NO2_TD_V1",
        spatial_extent = extent,
        temporal_extent = [input.date1date2()[0], input.date1date2()[1]]
        )
      
      # datacube = con.load_collection(
      #   "SENTINEL_5P_L2",
      #   spatial_extent = extent,
      #   temporal_extent = [input.date1date2()[0], input.date1date2()[1]],
      #   bands=["NO2"]
      #   )
      #   
      # datacube_cloud = con.load_collection(
      #   "SENTINEL_5P_L2",
      #   spatial_extent = extent,
      #   temporal_extent = [input.date1date2()[0], input.date1date2()[1]],
      #   bands=["CLOUD_FRACTION"]
      #   )
      # 
      # # mask for cloud cover
      # def threshold_(data):
      #   
      #   threshold = data[0].gte(input.cloud())
      #   
      #   return threshold
      # 
      # # apply the threshold to the cube
      # cloud_threshold = datacube_cloud.apply(process = threshold_)
      # 
      # #   # mask the cloud cover with the calculated mask
      # datacube = datacube.mask(cloud_threshold)
      
      # Fill Gaps
      datacube = datacube.apply_dimension(dimension = "t", process = "array_interpolate_linear")
      
      # Moving Average Window
      moving_average_window = 31
      
      with open('ma.py', 'r') as file:
        udf_file = file.read()
        
      udf = openeo.UDF(udf_file.format(n = moving_average_window))
      datacube_ma = datacube.apply_dimension(dimension = "t", process = udf)
      
      # Timeseries as JSON
      print("Processing and Downloading Results...")
      
      ## Mean as Aggregator
      datacube_mean = datacube.aggregate_spatial(geometries = extent, reducer = "mean")
      datacube_mean = datacube_mean.download("data/time-series-mean.json")
      
      ## Max as Aggregator
      datacube_max = datacube.aggregate_spatial(geometries = extent, reducer = "max")
      datacube_max = datacube_max.download("data/time-series-max.json")
      
      ## Mean as Aggregator for Moving Average Data Cube
      datacube_ma = datacube_ma.aggregate_spatial(geometries = extent, reducer = "mean")
      datacube_ma = datacube_ma.download("data/time-series-ma.json")
      
      # Read in JSONs
      with open("data/time-series-mean.json", "r") as f:
        ts_mean = json.load(f)
      print("mean time series read")
      
      with open("data/time-series-max.json", "r") as f:
        ts_max = json.load(f)
      print("max time series read")

      with open("data/time-series-ma.json", "r") as f:
        ts_ma = json.load(f)
      print("ma time series read")

      ts_df = pd.DataFrame.from_dict(ts_mean, orient='index', columns=['Mean']).reset_index()
      ts_df.columns = ['Date', 'Mean']
      ts_df['Mean'] = ts_df['Mean'].str.get(0)
     
      ts_max_df = pd.DataFrame.from_dict(ts_max, orient='index', columns=['Max']).reset_index()
      ts_max_df.columns = ['Date', 'Max']
      ts_df['Max'] = ts_max_df['Max'].str.get(0) 
      
      ts_ma_df = pd.DataFrame.from_dict(ts_ma, orient='index', columns=['MA']).reset_index()
      ts_ma_df.columns = ['Date', 'MA']
      ts_df['MA'] = ts_ma_df['MA'].str.get(0)
      
      # convert 'Date' column to datetime dtype
      ts_df['Date'] = pd.to_datetime(ts_df['Date'])
      
      # set 'Date' column as index
      ts_df.set_index('Date', inplace=True)
      
      # Time Series Smoothing
      ts_df['Smooth'] = ts_df['Mean'].rolling(31).mean()

      # plot time series for each column
      fig, ax = plt.subplots(figsize=(16, 12))
      ts_df.plot(ax=ax)
      ax.set_xlabel('Time')
      ax.set_ylabel('Value')
      ax.set_title('NO2 Time Series from SENTINEL 5P')
      # plt.show()
      
      return fig
    
    @output
    @render.plot
    @reactive.event(input.data2)
    async def plot_map():
      
      # Define the Spatial Extent
      extent = { # Münster
        "type": "Polygon",
        "coordinates": [[
          [input.w2(), input.n2()],
          [input.e2(), input.n2()],
          [input.e2(), input.s2()],
          [input.w2(), input.s2()],
          [input.w2(), input.n2()]
          ]]
          }
          
      # Build the Datacube    
      datacube = con.load_collection(
        "TERRASCOPE_S5P_L3_NO2_TD_V1",
        spatial_extent = extent,
        temporal_extent = [input.date1date22()[0], input.date1date22()[1]]
        )
      
      # datacube = con.load_collection(
      #   "SENTINEL_5P_L2",
      #   spatial_extent = extent,
      #   temporal_extent = [input.date1date22()[0], input.date1date22()[1]],
      #   bands=["NO2"]
      #   )
      #   
      # datacube_cloud = con.load_collection(
      #   "SENTINEL_5P_L2",
      #   spatial_extent = extent,
      #   temporal_extent = [input.date1date22()[0], input.date1date22()[1]],
      #   bands=["CLOUD_FRACTION"]
      #   )
      # 
      # # mask for cloud cover
      # def threshold_(data):
      #   
      #   threshold = data[0].gte(input.cloud2())
      #   
      #   return threshold
      # 
      # # apply the threshold to the cube
      # cloud_threshold = datacube_cloud.apply(process = threshold_)
      # 
      # #   # mask the cloud cover with the calculated mask
      # datacube = datacube.mask(cloud_threshold)
      
      # Fill Gaps
      datacube = datacube.apply_dimension(dimension = "t", process = "array_interpolate_linear")
      
      # Filter Temporal
      datacube = datacube.filter_temporal(extent = [input.date(), input.date()])
      
      # Safer for interpolation and plot dates
      if input.date() > input.date1date22()[1] or input.date() < input.date1date22()[0]:
        sys.exit("Date of Plot should be between the interpolation dates")

      # Download TIF
      print("Processing and Downloading Results...")
      datacube.download("data/map.tif")
      
      # Open TIF file
      with rasterio.open("data/map.tif") as src:
          image = src.read(1, masked=True)
          vmin, vmax = image.min(), image.max() # Define minimum and maximum values for the color map
      print("raster read")
      
      # Create figure and axis objects
      fig, ax = plt.subplots()
      
      # Plot image as a continuous variable with a color legend
      im = ax.imshow(image, cmap='viridis', vmin=vmin, vmax=vmax)
      
      # Add colorbar and title
      cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
      ax.set_title('NO2 Concentration Screenshot at '+input.date().strftime('%Y-%m-%d'))
      
      # Show plot
      # plt.show()
      return fig
      
    @output
    @render.image
    @reactive.event(input.data3) 
    async def image():
      
      generate_gif()
      
      print("done with function")
      from pathlib import Path
      
      dir = Path(__file__).resolve().parent
      img: ImgData = {"src": str(dir / "PNG" / 'spacetime-animation.gif'), "width": "1000px"}# Define the Spatial Extent
    
      return img
    
    #Generate a GIF function
    def generate_gif():
      extent = {
        "type": "Polygon",
        "coordinates": [[
          [input.w3(), input.n3()],
          [input.e3(), input.n3()],
          [input.e3(), input.s3()],
          [input.w3(), input.s3()],
          [input.w3(), input.n3()]
          ]]}
              
      # Build the Datacube    
      datacube = con.load_collection(
        "TERRASCOPE_S5P_L3_NO2_TD_V1",
        spatial_extent = extent,
        temporal_extent = [input.date1date23()[0], input.date1date23()[1]])
          
      # datacube = con.load_collection(
      #   "SENTINEL_5P_L2",
      #   spatial_extent = extent,
      #   temporal_extent = [input.date1date23()[0], input.date1date23()[1]],
      #   bands=["NO2"]
      #   )
      #   
      # datacube_cloud = con.load_collection(
      #   "SENTINEL_5P_L2",
      #   spatial_extent = extent,
      #   temporal_extent = [input.date1date23()[0], input.date1date23()[1]],
      #   bands=["CLOUD_FRACTION"]
      #   )
      # 
      # # mask for cloud cover
      # def threshold_(data):
      #   
      #   threshold = data[0].gte(input.cloud3())
      #   
      #   return threshold
      # 
      # # apply the threshold to the cube
      # cloud_threshold = datacube_cloud.apply(process = threshold_)
      # 
      # #   # mask the cloud cover with the calculated mask
      # datacube = datacube.mask(cloud_threshold)
      
      # Fill Gaps
      datacube = datacube.apply_dimension(dimension = "t", process = "array_interpolate_linear")
      
      # Create job to download all raster in the time range
      job = datacube.create_job()
      print("Starting the job")
      job.start_and_wait()
      job.get_results().download_files("animation")
    
      # Read in all TIF files in folder
      input_folder = "animation"
      output_folder = "PNG"
      print("Reading TIFs")
      filenames = os.listdir("animation")
      tif_regex = re.compile(r'openEO_(\d{4}-\d{2}-\d{2})Z\.tif')
      tif_files = [filename for filename in filenames if tif_regex.match(filename)]
      tif_files_sorted = sorted(tif_files, key=lambda x: datetime.datetime.strptime(tif_regex.match(x).group(1), '%Y-%m-%d'))
          
      # Initialize variables to hold minimum and maximum values
      global_min = float('inf')
      global_max = float('-inf')
          
      for filename in tif_files_sorted:
      # Open TIF file
        filepath = os.path.join(input_folder, filename)
        with rasterio.open(filepath) as src:
          image = src.read(1, masked=True)
                
        # Update minimum and maximum values
        file_min = np.min(image)
        file_max = np.max(image)
        if file_min < global_min:
          global_min = file_min
        if file_max > global_max:
          global_max = file_max
          
      for filename in tif_files_sorted:
      # Open TIF file
        filepath = os.path.join(input_folder, filename)
        with rasterio.open(filepath) as src:
          image = src.read(1, masked=True)
        
        # Extract date from file name
        date_str = tif_regex.match(filename).group(1)
        input_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        
        # Create figure and axis objects
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Plot image as a continuous variable with a color legend
        im = ax.imshow(image, cmap='viridis', vmin=global_min, vmax=global_max)
        
        # Add colorbar and title
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_title('NO2 Concentration at ' + input_date.strftime('%Y-%m-%d'))
        
        # Save plot as PNG file
        output_filename = os.path.join("PNG", date_str + '.png')
        plt.savefig(output_filename)
            
        # delete every tif file
        os.remove(filepath)
    
      # Create animated GIF from PNG files
      images = []
      print("Reading PNGs")
      for filename in os.listdir("PNG"):
        if filename.endswith('.png'):
          filepath = os.path.join("PNG", filename)
          images.append(imageio.imread(filepath))
      output_filename = os.path.join("PNG", 'spacetime-animation.gif')
      print("Rendering GIF")
      imageio.mimsave(output_filename, images, fps=input.fps())

      print("GIF saved")
      # Render for Shiny UI
        
      # Remove images
      for file in os.listdir("PNG"):
        if file.endswith(".png"):
         file_path = os.path.join("PNG", file)
         os.remove(file_path)
        
      return None

www_dir = Path(__file__).parent / "WWW"
app = App(app_ui, server, static_assets=www_dir)
