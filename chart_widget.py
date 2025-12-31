# chart_widget.py
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class EnvChart(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(dpi=100)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

        self.ax.set_title("Environment Realtime in greenhouse")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        # marker để nhìn rõ từng điểm
        self.line_temp, = self.ax.plot([], [], marker="o", label="Temp (°C)")
        self.line_hum,  = self.ax.plot([], [], marker="o", label="Humidity (%)")
        self.line_uv,   = self.ax.plot([], [], marker="o", label="UV")
        self.ax.legend(loc="upper right")

        # format thời gian HH:MM:SS
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))

        fig.tight_layout()

    def update_data(self, times, temps, hums, uvs):
        n = len(times)
        if n == 0:
            return

        # nếu mới có 1 điểm -> nhân đôi để chắc chắn thấy line/marker đẹp
        if n == 1:
            t0 = times[0]
            times = [t0, t0]
            temps = [temps[0], temps[0]]
            hums  = [hums[0], hums[0]]
            uvs   = [uvs[0], uvs[0]]

        self.line_temp.set_data(times, temps)
        self.line_hum.set_data(times, hums)
        self.line_uv.set_data(times, uvs)

        self.ax.relim()
        self.ax.autoscale_view()

        # xoay nhãn thời gian cho dễ đọc
        self.ax.figure.autofmt_xdate(rotation=30)

        self.draw()
