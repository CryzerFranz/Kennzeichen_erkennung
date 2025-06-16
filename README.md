# Teilprojekt für das Parkhaus
In diesem Teilprojekt geht es um die automatisierte Kennzeichenerkennung, sobald ein Fahrzeug vor der Schranke eines Parkhauses erkannt wird.

Nach erfolgreicher Erkennung des Kennzeichens wird geprüft, ob es in einer CSV-Datei hinterlegt ist. Ist das der Fall, wird der Zutritt gewährt – andernfalls verweigert.

Die grafische Benutzeroberfläche (GUI) bietet folgende Funktionen:

  - Live-Videoanzeige der Kamera
  - Anzeige, ob der Zugang erlaubt oder verweigert wurde
  - Übersicht über die aktuelle MQTT-Verbindung (Verbindungsstatus sichtbar)
  - Möglichkeit, Kennzeichen zur CSV-Datei hinzuzufügen oder zu entfernen
  - Aktuelle Uhrzeit und Datum

## Technologien
- Python + customtkinter
- YOLOv8 für Kennzeichen erkennung
- easyocr für die Texterkennung
- MQTT für die Kommunikation zwischen Parkhaussystem und Kennzeichenerkennung

## easyocr
Für die optimale Texterkennung wurden folgende Schritte gemacht:
```x1, y1, x2, y2 = map(int, box.xyxy[0])```
Zweck: Extrahieren der Koordinaten des vom YOLO-Modell erkannten Bounding Boxes (rechteckiger Bereich um das Nummernschild).
Hintergrund: YOLO gibt Koordinaten in Form von [x1, y1, x2, y2] zurück – die Ecken des Rechtecks.

```x1_new = max(x1 + 0, 0)```
Zweck: Sicherheitsmaßnahme, um sicherzustellen, dass der linke Rand nicht außerhalb des Bildbereichs liegt.
Hinweis: +0 ist redundant, aber eventuell Platzhalter für eine spätere manuelle Korrektur oder Justierung.

```cropped = frame[y1:y2, x1_new:x2]```
Zweck: Zuschneiden des Bildes auf den Bereich, der das erkannte Kennzeichen enthält.
Vorteil: Reduziert die Datenmenge für die OCR und fokussiert nur auf den relevanten Bildinhalt.

```gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)```
Zweck: Umwandlung des Farbbildes in ein Graustufenbild.
Begründung: OCR-Engines (wie EasyOCR oder Tesseract) arbeiten effizienter mit Graustufenbildern, da Farbinformationen für die Zeichenerkennung irrelevant sind.

```_, binary = cv2.threshold(gray, 38, 255, cv2.THRESH_BINARY_INV)```
Zweck: Binarisierung des Bildes: Alle Pixel unterhalb eines Grauwerts von 38 werden auf 255 (weiß), alle darüber auf 0 (schwarz) gesetzt – invertiert.
Begründung:
- Kontrastverstärkung zwischen Schrift (meist dunkel) und Hintergrund (hell).
- EASYOCR funktioniert deutlich zuverlässiger bei hohem Kontrast und klaren Rändern.

## MQTT-Kommunikation

Die Kommunikation erfolgt über folgende MQTT-Topics:

#### Topics
  - parkhaus/einfahrt
  - parkhaus/einfahrt_motion

#### Topic: parkhaus/einfahrt_motion

Dieses Topic übermittelt einen Binärwert:

- 1: Bewegung an der Einfahrt des Parkhauses erkannt
- 0: Keine Bewegung erkannt

#### Topic: parkhaus/einfahrt

Dieses Topic übermittelt ein JSON-Objekt im folgenden Format:

```
{
  "status": "granted",
  "kennzeichen": "<plate>"
}
```

status: Entweder "granted" (Zufahrt erlaubt) oder "denied" (Zufahrt verweigert)
kennzeichen: Das erkannte Fahrzeugkennzeichen, gespeichert in der Variable <plate>



