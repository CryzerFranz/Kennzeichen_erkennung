import customtkinter as ctk
import cv2
import json
import numpy as np
from PIL import Image, ImageTk
from datetime import datetime
import csv
import os
import easyocr
from ultralytics import YOLO
import paho.mqtt.client as mqtt
import time


# Objekterkennung-Modul
class ObjectDetector:
    def __init__(self):
        self.model = YOLO("license_plate_detector.pt")
    
    def detect(self, frame, reader):
        results = self.model(frame)
        plate_number = ""
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0]) 
                x1_new = max(x1 + 0, 0) 
                cropped = frame[y1:y2, x1_new:x2]  
                gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            
                _, binary = cv2.threshold(gray, 38, 255, cv2.THRESH_BINARY_INV)
                
                text = reader.readtext(binary)
                if text:
                    cv2.imshow("Nummernschild-Erkennung", binary)

                    plate_number = " ".join([entry[1] for entry in text])  
                    print("Erkanntes Kennzeichen:", plate_number)

                    cv2.putText(frame, plate_number, (x1_new, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                                1, (0, 255, 0), 2, cv2.LINE_AA)

                # Bounding Box zeichnen
                cv2.rectangle(frame, (x1_new, y1), (x2, y2), (0, 255, 0), 2)

        # Live-Bild mit Bounding Box anzeigen
       
        return plate_number
        

# Nummernschild-OCR-Modul
class LicensePlateOCR:
    def __init__(self):
        self.reader = easyocr.Reader(["en", "de"])
        
    def read_plate(self, plate_region):
        # Dummy-Implementierung
        return "ABC123"

# Statistik-Modul
class Statistics:
    def __init__(self):
        self.car_count = 0
        self.access_granted = 0
        self.access_denied = 0
    
    def update(self, detected_cars=0, granted=False, denied=False):
        self.car_count += detected_cars
        if granted:
            self.access_granted += 1
        if denied:
            self.access_denied += 1
    
    def get_stats(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return (f"Datum/Uhrzeit: {current_time}\n"
                f"Erkannte Autos: {self.car_count}\n"
                f"Zutritt gewährt: {self.access_granted}\n"
                f"Zutritt verweigert: {self.access_denied}")

# GUI-Modul
class LicensePlateGUI:
    def __init__(self, root, mqtt_client):
        self.root = root
        self.mqtt_client = mqtt_client  # Speichere den MQTT-Client
        self.root.title("License Plate Recognition")
        self.root.geometry("1200x800")
        self.detection_zone = (200, 200, 400, 300)  # x1, y1, x2, y2
        #self.allowed_plates = ["ABC123", "XYZ789"]
        self.allowed_plates = self.load_allowed_plates()  # CSV laden
        
        self.setup_gui()

    def load_allowed_plates(self):
        """Lädt erlaubte Kennzeichen aus einer CSV-Datei"""
        allowed_plates = []
        csv_path = os.path.join(os.path.dirname(__file__), "Kennzeichen.csv")
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                # Angenommen, die CSV hat eine Spalte mit Kennzeichen
                for row in reader:
                    if row:  # Prüft, ob die Zeile nicht leer ist
                        allowed_plates.append(row[0].strip())
        except FileNotFoundError:
            print("CSV-Datei nicht gefunden. Erstelle leere Liste.")
        except Exception as e:
            print(f"Fehler beim Laden der CSV: {e}")
        return allowed_plates
    
    def save_allowed_plates(self):
        """Speichert die erlaubten Kennzeichen in die CSV-Datei"""
        csv_path = os.path.join(os.path.dirname(__file__), "Kennzeichen.csv")
        try:
            with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
             writer = csv.writer(csvfile, delimiter=';')
             for plate in self.allowed_plates:
                writer.writerow([plate])  # Schreibe jedes Kennzeichen als eigene Zeile
        except Exception as e:
            print(f"Fehler beim Speichern der CSV: {e}")

    def setup_gui(self):
        # Webcam Frame
        self.webcam_frame = ctk.CTkFrame(self.root, width=640, height=480)
        self.webcam_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        self.webcam_label = ctk.CTkLabel(self.webcam_frame, text="")
        self.webcam_label.pack()

        # Erkanntes Nummernschild
        self.plate_text = ctk.CTkLabel(self.root, text="Erkanntes Nummernschild: ", font=("Arial", 20))
        self.plate_text.grid(row=0, column=1, padx=10, pady=10)

        # Nummernschild-Liste
        self.setup_plate_list()

        # Access-Anzeige
        self.access_label = ctk.CTkLabel(self.root, text="Access: Waiting", font=("Arial", 24))
        self.access_label.grid(row=2, column=0, padx=10, pady=10)

        # Broker-Status
        self.broker_status_label = ctk.CTkLabel(self.root, text="Broker: Verbindungsstatus wird geprüft...", font=("Arial", 16))
        self.broker_status_label.grid(row=3, column=1, padx=10, pady=5, sticky="n")

        # Statistikfeld
        self.stats_frame = ctk.CTkFrame(self.root)
        self.stats_frame.grid(row=2, column=1, padx=10, pady=10)
        self.stats_label = ctk.CTkLabel(self.stats_frame, text="", font=("Arial", 14))
        self.stats_label.pack(pady=5)

    def setup_plate_list(self):
        self.plate_list_frame = ctk.CTkFrame(self.root)
        self.plate_list_frame.grid(row=1, column=1, padx=10, pady=10)
        
        self.plate_list = ctk.CTkTextbox(self.plate_list_frame, width=200, height=200)
        self.plate_list.pack(pady=5)
        self.update_plate_list()
        
        self.new_plate_entry = ctk.CTkEntry(self.plate_list_frame, placeholder_text="Neues Nummernschild")
        self.new_plate_entry.pack(pady=5)
        
        self.add_button = ctk.CTkButton(self.plate_list_frame, text="Hinzufügen", command=self.add_plate)
        self.add_button.pack(pady=5)
        
        self.remove_button = ctk.CTkButton(self.plate_list_frame, text="Entfernen", command=self.remove_plate)
        self.remove_button.pack(pady=5)

    def update_plate_list(self):
        self.plate_list.delete("0.0", "end")
        for plate in self.allowed_plates:
            self.plate_list.insert("end", f"{plate}\n")

    def update_broker_status(self):
        """Aktualisiert den Verbindungsstatus des MQTT-Brokers in der GUI"""
        if self.mqtt_client.client.is_connected():
            self.broker_status_label.configure(text="Broker: Verbunden", text_color="green")
        else:
            self.broker_status_label.configure(text="Broker: Nicht verbunden", text_color="red")

    def add_plate(self):
        new_plate = self.new_plate_entry.get().strip()
        if new_plate and new_plate not in self.allowed_plates:
            self.allowed_plates.append(new_plate)
            self.update_plate_list()
            self.save_allowed_plates()  # Speichere die aktualisierte Liste in die CSV
            self.new_plate_entry.delete(0, "end")

    def remove_plate(self):
        selected = self.plate_list.get("sel.first", "sel.last").strip()
        if selected in self.allowed_plates:
            self.allowed_plates.remove(selected)
            self.update_plate_list()
            self.save_allowed_plates()

class MQTT_Client:
    def __init__(self):
        self.client = mqtt.Client()
        #self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        #self.client.on_connect = on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.broker_address = "172.5.232.218"
        self.port = 1883
        self.message = 0
        
        try:
            self.client.connect(self.broker_address, self.port)
        except Exception as e:
            print(f"Verbindungsfehler: {e}")
            exit(1)
        
    def on_message(self, client, userdata, msg):
        print(f"Topic: {msg.topic} | Nachricht: {msg.payload.decode()}")
        if(msg.topic == "parkhaus/einfahrt_motion"):
            if msg.payload.decode() == "1": 
                self.message = 1
            else:
                self.message = 0
            
        
        

    def on_disconnect(self, client, userdata, rc):
        print("Verbindung zum Broker getrennt")
        
    def connect(self):
        try:
            self.client.connect(self.broker_address, self.port)
            self.client.loop_start()
            self.client.subscribe("parkhaus/einfahrt_motion")
        except Exception as e:
            print(f"Verbindungsfehler: {e}")
            
            
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
    
# Hauptklasse
class LicensePlateApp:
    def __init__(self, mqtt_client):
        self.mqtt = mqtt_client
        self.root = ctk.CTk()
        self.detector = ObjectDetector()
        self.ocr = LicensePlateOCR()
        self.stats = Statistics()
        self.gui = LicensePlateGUI(self.root, self.mqtt)
        self.cap = cv2.VideoCapture(0)
        self.tmp_plate = ""
        
        self.update()
        self.root.mainloop()

    def process_frame(self, frame, reader):
        current_plate = ""
        if self.mqtt.message == 1:
            current_plate = self.detector.detect(frame, reader)

        cars_detected = 0
        if current_plate != "" and self.tmp_plate != current_plate:
            cars_detected+=1

        return frame, current_plate, cars_detected

    def update_access(self, plate):
        
    
        if plate and (self.tmp_plate == "" or self.tmp_plate != plate):
            self.gui.plate_text.configure(text=f"Erkanntes Nummernschild: {plate}")
            if plate in self.gui.allowed_plates:
                self.gui.access_label.configure(text="Access: Granted", text_color="green")
                self.stats.update(granted=True)
                payload = {
                    "status": "granted",
                    "kennzeichen": plate
                }
                json_payload = json.dumps(payload)
                self.mqtt.client.publish("parkhaus/einfahrt", json_payload)
                #self.mqtt.client.publish("parkhaus/einfahrt", "granted")
                time.sleep(2)
            else:
                self.gui.access_label.configure(text="Access: Denied", text_color="red")
                self.stats.update(denied=True)
                payload = {
                    "status": "denied",
                    "kennzeichen": plate
                }
                json_payload = json.dumps(payload)
                self.mqtt.client.publish("parkhaus/einfahrt", json_payload)
                time.sleep(2)
            if self.tmp_plate == "":
                self.tmp_plate = plate
            if self.tmp_plate != plate:
                self.tmp_plate = plate
        else:
            self.gui.plate_text.configure(text="Erkanntes Nummernschild: Keine Erkennung")
            self.gui.access_label.configure(text="Access: Waiting", text_color="black")

    def update(self):
        #if self.mqtt.message == 1:
        ret, frame = self.cap.read()
        if ret:
                print(self.mqtt.message)
                frame, plate, cars_detected = self.process_frame(frame, self.ocr.reader)
                self.stats.update(detected_cars=cars_detected)
                self.update_access(plate)
                self.gui.stats_label.configure(text=self.stats.get_stats())
                self.gui.update_broker_status()  # Aktualisiere den Broker-Status

                # Bild anzeigen
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.gui.webcam_label.configure(image=imgtk)
                self.gui.webcam_label.image = imgtk

        self.root.after(10, self.update)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

if __name__ == "__main__":
    mqtt_client = MQTT_Client()
    mqtt_client.connect()
    
    app = LicensePlateApp(mqtt_client)
