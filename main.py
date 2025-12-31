import sys
import os
from datetime import datetime

from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtGui import QPixmap, QKeySequence

# Qt Resource (icon)
try:
    import image_rc
except Exception:
    try:
        import image
    except Exception:
        pass

from weather_api import WeatherClient
from chart_widget import EnvChart
from data_logger import append_weather
from ai_predictor import predict_next_env


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_FILE = os.path.join(BASE_DIR, "greenhouse_monitor_updated.ui")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_FILE, self)

        # ===== Weather =====
        API_KEY = "731c6415649945c1be1134638252312"
        LOCATION = "Ho Chi Minh"
        self.weather = WeatherClient(API_KEY, LOCATION)

        # ===== Mode =====
        self.auto_mode = False
        self.shortcut_mode = QtWidgets.QShortcut(QKeySequence("M"), self)
        self.shortcut_mode.activated.connect(self.toggle_mode)

        # ===== Thresholds =====
        self.FAN_TH = 30.0
        self.HEATER_TH = 25.0
        self.WATER_HUM_TH = 50.0

        # ===== AUTO memory (cooldown) =====
        self.last_water_time = None
        self.WATER_COOLDOWN_MIN = 5

        # ===== Device states =====
        self.fan_on = False
        self.heater_on = False
        self.water_on = False

        # Fix overlap icons (remove stylesheet background image)
        for lb in (self.label_3, self.label_5, self.label_6):
            lb.clear()
            lb.setText("")
            lb.setStyleSheet("")
            lb.setScaledContents(True)

        # Manual buttons
        self.pushFan.clicked.connect(self.toggle_fan)
        self.pushFan_2.clicked.connect(self.toggle_heater)
        self.pushButton.clicked.connect(self.toggle_water)

        # Predicted box
        self.label_tempPred.setWordWrap(True)
        self.label_tempPred.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.refresh_device_ui()
        self.apply_mode_ui()

        # ===== Chart buffers =====
        self.times, self.temps, self.hums, self.uvs = [], [], [], []
        self.max_points = 60

        # ===== Embed chart =====
        self.chart = EnvChart(parent=self.chartContainer)
        layout = QtWidgets.QVBoxLayout(self.chartContainer)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.chart)
        self.chartContainer.setMaximumHeight(430)

        # ===== Timer =====
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_weather_and_chart)
        self.timer.start(60_000)

        self.update_weather_and_chart()

    # ---------- MODE ----------
    def toggle_mode(self):
        self.auto_mode = not self.auto_mode
        self.apply_mode_ui()

        mode_txt = "AUTO" if self.auto_mode else "MANUAL"
        self.statusBar().showMessage(f"MODE: {mode_txt}", 3000)

        # If just switched to AUTO, apply immediately (no need wait 60s)
        if self.auto_mode:
            self.apply_auto_from_current()

    def apply_mode_ui(self):
        manual_enabled = not self.auto_mode
        self.pushFan.setEnabled(manual_enabled)
        self.pushFan_2.setEnabled(manual_enabled)
        self.pushButton.setEnabled(manual_enabled)

    # ---------- MANUAL TOGGLES ----------
    def toggle_fan(self):
        if self.auto_mode:
            return
        self.fan_on = not self.fan_on
        self.refresh_device_ui()

    def toggle_heater(self):
        if self.auto_mode:
            return
        self.heater_on = not self.heater_on
        self.refresh_device_ui()

    def toggle_water(self):
        if self.auto_mode:
            return
        self.water_on = not self.water_on
        self.refresh_device_ui()

    def refresh_device_ui(self):
        self.pushFan.setText(f"Fan : {'ON' if self.fan_on else 'OFF'}")
        self.pushFan_2.setText(f"Heater: {'ON' if self.heater_on else 'OFF'}")
        self.pushButton.setText(f"Watering Can: {'ON' if self.water_on else 'OFF'}")

        self.label_3.clear()
        self.label_5.clear()
        self.label_6.clear()

        fan_icon = ":/myimage/fan_on.png" if self.fan_on else ":/myimage/fan_off.png"
        heater_icon = ":/myimage/heater_on.png" if self.heater_on else ":/myimage/heater_off.png"
        water_icon = ":/myimage/water_on.png" if self.water_on else ":/myimage/water_off.png"

        self.label_3.setPixmap(QPixmap(fan_icon))
        self.label_5.setPixmap(QPixmap(heater_icon))
        self.label_6.setPixmap(QPixmap(water_icon))

    # ---------- AUTO DECISION (HYBRID) ----------
    def auto_decide(self, temp_now, hum_now, temp_pred, hum_pred):
        """
        AUTO logic thực tế:
        - Heater: theo TEMP NOW + hysteresis
        - Fan: theo TEMP PRED (10m) + emergency theo TEMP NOW + hysteresis
        - Water: theo HUM NOW + cooldown + hysteresis
        """
        temp_now = float(temp_now)
        hum_now = float(hum_now)
        temp_pred = float(temp_pred)
        hum_pred = float(hum_pred)

        # ===== HEATER (NOW + hysteresis) =====
        HEATER_ON = self.HEATER_TH          # 25
        HEATER_OFF = self.HEATER_TH + 1.0   # 26

        if self.heater_on:
            heater = temp_now < HEATER_OFF
        else:
            heater = temp_now < HEATER_ON

        # ===== FAN (PRED + emergency NOW + hysteresis) =====
        FAN_ON_PRED = self.FAN_TH           # 30
        FAN_OFF_PRED = self.FAN_TH - 1.0    # 29
        FAN_EMERGENCY_ON_NOW = 32.0
        FAN_EMERGENCY_OFF_NOW = 31.0

        if self.fan_on:
            fan = (temp_pred > FAN_OFF_PRED) or (temp_now > FAN_EMERGENCY_OFF_NOW)
        else:
            fan = (temp_pred > FAN_ON_PRED) or (temp_now > FAN_EMERGENCY_ON_NOW)

        # ===== WATER (NOW + cooldown + hysteresis) =====
        WATER_ON = self.WATER_HUM_TH        # 50
        WATER_OFF = self.WATER_HUM_TH + 5.0 # 55

        cooldown_ok = True
        if self.last_water_time is not None:
            mins = (datetime.now() - self.last_water_time).total_seconds() / 60.0
            cooldown_ok = mins >= self.WATER_COOLDOWN_MIN

        if self.water_on:
            water = hum_now < WATER_OFF
        else:
            water = (hum_now < WATER_ON) and cooldown_ok

        # update last_water_time on OFF->ON
        if (not self.water_on) and water:
            self.last_water_time = datetime.now()

        # ===== avoid conflict =====
        if heater:
            fan = False

        return fan, heater, water

    def apply_auto_from_current(self):
        """Apply AUTO immediately using latest buffered NOW data + model prediction."""
        if len(self.temps) == 0:
            return

        temp_now = self.temps[-1]
        hum_now = self.hums[-1]
        uv_now = self.uvs[-1]

        # Predict 10 minutes ahead (model already trained for 10m)
        temp_pred, hum_pred, uv_pred = predict_next_env(temp_now, hum_now, uv_now)

        fan_rec, heater_rec, water_rec = self.auto_decide(temp_now, hum_now, temp_pred, hum_pred)

        self.fan_on = fan_rec
        self.heater_on = heater_rec
        self.water_on = water_rec
        self.refresh_device_ui()

        # Update predicted box for immediate feedback
        mode_txt = "AUTO" if self.auto_mode else "MANUAL"
        self.label_tempPred.setText(
            f"Next (10m): {temp_pred:.1f}°C | {hum_pred:.0f}% | UV {uv_pred:.1f}\n"
            f"AUTO action: Fan {'ON' if fan_rec else 'OFF'} (predicted) | "
            f"Heater {'ON' if heater_rec else 'OFF'} (now) | "
            f"Water {'ON' if water_rec else 'OFF'} (now)\n"
            f"MODE: {mode_txt}  |  Press M to toggle"
        )

    # ---------- UPDATE LOOP ----------
    def update_weather_and_chart(self):
        try:
            temp_c, humidity, uv = self.weather.get_current()
            now = datetime.now()

            # Log CSV (only when API OK)
            append_weather(temp_c, humidity, uv)

            # Update NOW labels
            self.label_tempNow.setText(f"Temp now: {temp_c:.1f} °C")
            self.label_humNow.setText(f"Humidity: {humidity:.0f} %")
            self.label_uvNow.setText(f"UV Index: {uv:.1f}")

            # Update buffers
            self.times.append(now)
            self.temps.append(temp_c)
            self.hums.append(humidity)
            self.uvs.append(uv)

            if len(self.times) > self.max_points:
                self.times = self.times[-self.max_points:]
                self.temps = self.temps[-self.max_points:]
                self.hums = self.hums[-self.max_points:]
                self.uvs = self.uvs[-self.max_points:]

            # Update chart
            self.chart.update_data(self.times, self.temps, self.hums, self.uvs)

            # AI predict (10m)
            temp_pred, hum_pred, uv_pred = predict_next_env(temp_c, humidity, uv)

            # AUTO decision (hybrid)
            fan_rec, heater_rec, water_rec = self.auto_decide(temp_c, humidity, temp_pred, hum_pred)

            # Apply in AUTO mode
            if self.auto_mode:
                self.fan_on = fan_rec
                self.heater_on = heater_rec
                self.water_on = water_rec
                self.refresh_device_ui()

            # Update predicted box
            mode_txt = "AUTO" if self.auto_mode else "MANUAL"
            action_title = "AUTO action" if self.auto_mode else "Recommend"

            self.label_tempPred.setText(
                f"Next (10m): {temp_pred:.1f}°C | {hum_pred:.0f}% | UV {uv_pred:.1f}\n"
                f"{action_title}: Fan {'ON' if fan_rec else 'OFF'} (predicted) | "
                f"Heater {'ON' if heater_rec else 'OFF'} (now) | "
                f"Water {'ON' if water_rec else 'OFF'} (now)\n"
                f"MODE: {mode_txt}  |  Press M to toggle"
            )

            self.statusBar().showMessage(
                f"OK {now.strftime('%H:%M:%S')} | Temp {temp_c:.1f} | Hum {humidity:.0f} | UV {uv:.1f}"
            )

        except Exception as e:
            self.statusBar().showMessage(f"Error: {repr(e)}", 12000)
            self.label_tempPred.setText("AI: ERROR")
            self.label_tempNow.setText("Temp now: ERROR")
            self.label_humNow.setText("Humidity: ERROR")
            self.label_uvNow.setText("UV Index: ERROR")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
