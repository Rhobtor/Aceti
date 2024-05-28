import tkinter
import tkinter.font
import tkinter.ttk
import os, sys, webbrowser, platform
import signal
import random
from tkintermapview import TkinterMapView
from tkintermapview.canvas_position_marker import CanvasPositionMarker
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

import threading
import time
import screeninfo
import traceback
import re
import math
import pandas as pd
from PIL import Image, ImageTk
sys.path.append('../')
from shared import *
from assets import *
from widgets.ListboxEditable import ListboxEditable
from widgets.labels import *
import datetime
import torch
from tabs.GPModels import GaussianProcessGPyTorch
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import cv2
import utm
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import MySQLdb
import pandas as pd
import numpy as np
import cv2
import matplotlib.pyplot as plt
import utm
from math import radians, cos, sin, sqrt, atan2
import torch
import colorcet
import datetime
from tkinter import *


max_retain_data=40

class SHIP(CanvasPositionMarker):
    def __init__(self, name, deg_x: float, deg_y: float,text: str = None, parent=None):
        
        if parent is None:
            super().__init__(self,(deg_x,deg_y),text=text,**kwargs)
            return #stop doing anything


        #store parent
        self.parent=parent
        self.map_widget=parent.map_widget

        #store bag name
        self.name=name
        
        #restore context
        super().__init__(self.map_widget,(deg_x,deg_y), text=text, image_zoom_visibility=(0, float("inf")),  icon=ImageTk.PhotoImage(self.parent.assets.image_ship),command=self.leftclick)
        
        #draw it
        self.draw()
        self.map_widget.canvas_marker_list.append(self)

    def mouse_enter(self,event=None):
        self.set_text(self.name)
        super().mouse_enter(event)
        self.draw()

    def mouse_leave(self, event=None):
        self.set_text("")
        super().mouse_leave(event)

    def leftclick(self, event=None):
        pass

    def update_rotation(self,degrees):
        self.change_icon(ImageTk.PhotoImage(self.parent.assets.image_ship.rotate(degrees)))
## aqui lo de gauss y sensor
class SENSOR(CanvasPositionMarker):
    def __init__(self, name, deg_x: float, deg_y: float,text: str = None, parent=None):
        
        if parent is None:
            super().__init__(self,(deg_x,deg_y),text=text,**kwargs)
            return #stop doing anything


        #store parent
        self.parent=parent
        self.map_widget=parent.map_widget
        self.last_value=-200
        #store bag name
        self.name=name
        
        #restore context
        super().__init__(self.map_widget,(deg_x,deg_y), text=text, image_zoom_visibility=(0, float("inf")),command=self.leftclick, icon=self.parent.assets.icon_waste[random.randint(0, self.parent.assets.waste_len-1)])
        
        #draw it
        self.draw()
        self.map_widget.canvas_marker_list.append(self)

    def mouse_enter(self,event=None):
        self.set_text(self.name)
        super().mouse_enter(event)
        self.draw()

    def mouse_leave(self, event=None):
        self.set_text("")
        super().mouse_leave(event)

    def leftclick(self, event=None):
        pass

    def update(self, value):
        if abs(value-self.last_value)>max_retain_data:
            self.hide_image(True)
    
    def update_position(self, value, lat, lon):
        self.hide_image(False)
        self.last_value=value
        self.set_position(lat,lon)


class SENSORTAB(tkinter.ttk.PanedWindow):
    def __init__(self, parent=None):
        if parent is None:
            parent = tkinter.Tk()
        self.parent = parent
        self.trash_markers = []
        self.df_procesado = None  # Inicializa el DataFrame procesado
        # inherit
        try:
            self.assets = self.parent.assets
            self.shared = self.parent.shared
        except:
            self.assets = Assets()
            self.shared = SHARED()

        super().__init__(orient="horizontal")

        self.create_panels()
        self.sensor_tab()

    def create_panels(self):
        # Create the left panel for the map
        self.map_panel = ttk.PanedWindow(self, orient="vertical")
        self.add(self.map_panel)

        # Create the right panel for GPS and plot
        self.GPS_panel = ttk.PanedWindow(self, orient="vertical")
        self.add(self.GPS_panel)

        # Distribute the space of the panels
        self.map_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.GPS_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def sensor_tab(self):
        # Create map widget in the map panel
        self.map_widget = TkinterMapView(self.map_panel, corner_radius=0, height=int(self.parent.winfo_screenheight() * 0.8) + 1)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        self.map_panel.add(self.map_widget)

        self.topleft = [37.420088, -6.001346]
        self.bottomright = [37.418399, -5.997504]
        self.map_widget.fit_bounding_box(self.topleft, self.bottomright)

        self.trashes = []
        self.ships = []
        self.sensor = []
        self.sensor_paths = []

        # Create the plot frame in the GPS panel
        self.plot_frame = ttk.PanedWindow(self.GPS_panel, orient="vertical")
        self.GPS_panel.add(self.plot_frame)

        # Create info bar in GPS panel
        gps_data = ttk.Frame(self.GPS_panel)  # Change to Frame
        gps_data.pack(side=tk.BOTTOM, fill=tk.X)  # Pack at the bottom

        # Create timeline
        self.timeline = tk.Scale(gps_data, from_=0, to=0, orient="horizontal", length=self.parent.winfo_screenwidth() * 0.9, command=self.go_to_time)
        self.timeline.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X, expand=True)

        self.play_callback = None

        # Create play and center buttons
        aux = tk.Frame(gps_data)
        aux.pack(side=tk.BOTTOM, fill=tk.X)

        buttons_frame = tk.Frame(aux)
        buttons_frame.pack(side=tk.TOP, fill=tk.X)

        self.play_button = tk.Button(buttons_frame, image=self.assets.icon_play, command=self.play, width=35, height=35)
        self.play_button.pack(side=tk.LEFT)

        self.play_status = False

        self.play_button["state"] = "disabled"
        self.center_button = tk.Button(buttons_frame, text="Center", command=self.center_map, width=10, height=1)
        self.center_button.pack(side=tk.RIGHT, expand="true", fill="both")
        self.speed_button = tk.Label(buttons_frame, text="x1", relief="raised", width=5, height=1)
        self.speed_button.bind("<Button-1>", self.increase_speed)
        self.speed_button.bind("<Button-3>", self.decrease_speed)
        self.speed = 1
        self.speed_button.pack(side=tk.RIGHT, expand="true", fill="y")

        self.plot_button = ttk.Button(gps_data, text="Display Plot", command=self.display_plot_from_button)
        self.plot_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Sensor variable selector
        self.sensor_var = tk.StringVar()
        self.sensor_var.set("Sonar")
        self.sensor_menu = ttk.Combobox(gps_data, textvariable=self.sensor_var, values=["Sonar", "Conductivity", "PH", "Temperature", "Turbidity"])
        self.sensor_menu.pack(side=tk.LEFT, padx=5, pady=5)

        # Date display
        self.date_var = tk.StringVar()
        self.date_label = tk.Label(aux, textvariable=self.date_var, width=int(self.parent.winfo_screenwidth() * 0.08), height=1, font=tk.font.Font(weight='bold', size=12))
        self.date_label.pack(side=tk.BOTTOM, padx=0, pady=2, anchor="c")

    def play(self):
        if self.play_status:
            self.play_button.config(image=self.assets.icon_play)
            self.parent.after_cancel(self.play_callback)
            self.play_status = False
        else:
            if self.timeline.get() - 1 == self.shared.database.index[-1]:
                self.timeline.set(0)
            self.play_button.config(image=self.assets.icon_pause)
            self.play_callback = self.parent.after(200 // self.speed, self.execute_time)
            self.play_status = True

    def go_to_time(self, value):
        value = int(value)
        if value >= self.shared.database.index[-1]:
            return

        self.date_var.set(self.shared.rawdatabase.at[value, "Date"])
        self.ships[0].set_position(self.shared.rawdatabase.at[value, "Latitude"], self.shared.rawdatabase.at[value, "Longitude"])

        for path in self.sensor_paths:
            path.delete()
        self.sensor_paths.clear()

        sensor_colors = {"Sonar": "blue", "Turbidity": "green", "Temperature": "red", "PH": "yellow", "Conductivity": "purple"}
        current_sensor = self.shared.rawdatabase.at[value, "Sensor"]
        current_lat = self.shared.rawdatabase.at[value, "Latitude"]
        current_lon = self.shared.rawdatabase.at[value, "Longitude"]

        color = sensor_colors.get(current_sensor, "black")
        sensor_data = self.shared.rawdatabase[self.shared.rawdatabase['Sensor'] == current_sensor]
        positions = list(zip(sensor_data['Latitude'], sensor_data['Longitude']))
        current_position = (current_lat, current_lon)
        if current_position in positions:
            pos_index = positions.index(current_position)
            path_positions = positions[:pos_index + 1]
            path = self.map_widget.set_path(path_positions, color=color, width=2)
            self.sensor_paths.append(path)

    def execute_time(self):
        if self.timeline.get() - 1 == self.shared.database.index[-1] and self.play_status:
            self.play()
            return
        self.timeline.set(self.timeline.get() + 1)
        self.play_callback = self.parent.after(200 // self.speed, self.execute_time)

    def increase_speed(self, event=None):
        if self.speed < 8:
            self.speed += 1
        self.speed_button.config(text=f"x{self.speed}")

    def decrease_speed(self, event=None):
        if self.speed > 1:
            self.speed -= 1
        self.speed_button.config(text=f"x{self.speed}")

    def center_map(self, event=None):
        self.map_widget.fit_bounding_box(self.topleft, self.bottomright)

    def update_database(self):
        self.date_var.set(self.shared.rawdatabase.at[0, "Date"])
        self.timeline.config(to=len(self.shared.rawdatabase) - 1)

        ship_latitude = self.shared.rawdatabase.at[0, "Latitude"]
        ship_longitude = self.shared.rawdatabase.at[0, "Longitude"]
        self.ships.append(SHIP("vehicle_1", ship_latitude, ship_longitude, parent=self))

    def display_plot_from_button(self):
        end_time_index = int(self.timeline.get())
        current_sensor = self.sensor_var.get()
        self.display_plot(current_sensor, end_time_index)

    def display_plot(self, sensor, end_time_index):
        start_time_index = 0
        start_time = self.shared.rawdatabase.at[start_time_index, "Date"]
        end_time = self.shared.rawdatabase.at[end_time_index, "Date"]

        try:
            mean_map, _, x, y = self.get_gp(sensor, start_time, end_time)
            fig = self.plot_mean(mean_map, sensor, x, y)

            # Clear the previous plot from plot_frame
            for widget in self.plot_frame.winfo_children():
                widget.destroy()

            # Add the new plot to plot_frame
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
            toolbar.update()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))


    def get_gp(self, sensor,start_time, end_time):
        self.df_procesado = self.shared.rawdatabase.copy()
        self.selected_map = 'alamillo'
        image = cv2.imread(f'/home/rhobtor/codeInWindows/aceti/Aceti/Maps/{self.selected_map.capitalize()}Image2.png', 0)
        _, binary_image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        binary_image = np.where(binary_image > 0, 1, 0)
        if np.any(binary_image):
            print("Se encontraron algunos valores distintos de cero en binary_image.")
        else:
            print("No se encontraron valores distintos de cero en binary_image.")

        if self.selected_map == 'alamillo':
            map_coords = {'lat_min': 37.417823087, 'lat_max': 37.421340387, 'lon_min': -6.001553482, 'lon_max': -5.997342323}
            pos_ini = utm.from_latlon(map_coords['lat_min'], map_coords['lon_min'])
            self.scenario_map = np.genfromtxt(f'/home/rhobtor/codeInWindows/aceti/Aceti/Maps/{self.selected_map}.csv', delimiter=',')
            satelite_img = plt.imread(f'/home/rhobtor/codeInWindows/aceti/Aceti/Maps/{self.selected_map.capitalize()}Sat.png')
        
        rows, cols = self.scenario_map.shape
        self.res_lat, self.res_lon = (map_coords['lat_max'] - map_coords['lat_min']) / rows, (map_coords['lon_max'] - map_coords['lon_min']) / cols

        sensor_df = self.shared.rawdatabase[self.shared.rawdatabase['Sensor'] == sensor].reset_index(drop=True)
        # sensor_df = sensor_df[(sensor_df['Date'] > start_time) & (sensor_df['Date'] < end_time)].reset_index(drop=True)
        sensor_df = sensor_df[(sensor_df['Date'] > start_time) & (sensor_df['Date'] < end_time)].reset_index(drop=True)
        # Quitar las medidas con valor cero
        # sensor_df = sensor_df[sensor_df['Data'] != 0].reset_index(drop=True)
        if sensor_df.empty:
            raise ValueError(f"No data available for sensor {sensor} on date {date}")
        
        n = 8
        latitudes = np.array(sensor_df['Latitude'].astype(float))[::n]
        longitudes = np.array(sensor_df['Longitude'].astype(float))[::n]
        
        if len(latitudes) == 0 or len(longitudes) == 0:
            raise ValueError(f"No latitude/longitude data available for sensor {sensor} on date {date}")
        
        y, x = zip(*[self.gps_to_matrix_idx(lat, lon, self.topleft[0], self.bottomright[1], self.res_lat, self.res_lon) for lat, lon in zip(latitudes, longitudes)])
        
        xy = list(zip(y, x))
        data = np.array(sensor_df['Data'].astype(float))[::n]  # Suponiendo que la columna con los datos de los sensores se llama 'Data'

        gaussian_process = GaussianProcessGPyTorch(scenario_map = self.scenario_map, initial_lengthscale = 300, kernel_bounds = (200, 400), training_iterations = 50, scale_kernel=True, device = 'cuda' if torch.cuda.is_available() else 'cpu')        
        gaussian_process.fit_gp(X_new=xy, y_new=data, variances_new=[0.005]*len(data))
        mean_map, uncertainty_map = gaussian_process.predict_gt()

        return mean_map, uncertainty_map, x, y

    def plot_mean(self,mean_map, sensor, x, y):
        fig, axis = plt.subplots()
        plt.text(350, 1100, 'Punto de despliegue', fontsize=9, rotation=0, ha='center', va='center', color='w')
        plt.scatter(175, 1050, c='r', s=50, marker='X', zorder=2)
        plt.xticks([])
        plt.yticks([])
        cs_internos = plt.contour(mean_map, colors='black', alpha=0.7, linewidths=0.7, zorder=1)
        cs_externo = plt.contour(mean_map, colors='black', alpha=1, linewidths=1.7, zorder=1)
        cs_internos.collections[0].remove()
        for i in range(1, len(cs_externo.collections)):
            cs_externo.collections[i].remove()
        plt.clabel(cs_internos, inline=1, fontsize=3.5)
        plt.scatter(x, y, c='black', s=1, marker='.', alpha=0.5)
        if np.any(mean_map):
            print("Se encontraron algunos valores distintos de cero en mean_map2.")
        else:
            print("No se encontraron valores distintos de cero en mean_map2.")
        # if np.any(mean_map):
        #     vmin = np.min(mean_map[mean_map > 0])
        # else:
        #     vmin = 0
        # vmin = 0
        # vmax= 0
        # if np.any(self.mean_map > 0):
        #     vmin = np.min(self.mean_map[self.mean_map > 0])
        # else:
        #     print("No se encontraron valores min válidos en mean_map.")
        vmin = np.min(mean_map[mean_map > 0])
        vmax = np.max(mean_map[mean_map > 0])

        # if np.any(self.mean_map > 0):
        #     vmax = np.max(self.mean_map[self.mean_map > 0])
        # else:
        #     print("No se encontraron valores max válidos en mean_map.")
        
        plt.imshow(mean_map, cmap='viridis', alpha=1, origin='upper', vmin=vmin, vmax=vmax)
        if self.selected_map == 'alamillo':
            plt.ylim(1150, 200)
        unidades_dict = {'Sonar': 'Profundidad (m)', 'Conductivity': 'Conductividad (mS/cm)', 'PH': 'pH', 'Temperature': 'Temperatura (ºC)', 'Turbidity': 'Turbidez (NTU)'}
        nombre_dict = {'Sonar': 'Batimetría', 'Conductivity': 'Conductividad', 'PH': 'pH', 'Temperature': 'Temperatura', 'Turbidez': 'Turbidez'}
        plt.colorbar(shrink=0.65).set_label(label=unidades_dict[sensor], size=12)
        if self.selected_map == 'alamillo':
            plt.title(f'{nombre_dict[sensor]} del Lago Mayor (Parque del Alamillo)')
        return fig

    def gps_to_matrix_idx(self, lat, lon, lat_max, lon_min, res_lat, res_lon):
        row_idx = int((lat_max - lat) / res_lat)
        col_idx = int((lon - lon_min) / res_lon)
        return row_idx, col_idx
