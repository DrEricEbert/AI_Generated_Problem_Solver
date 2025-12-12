import numpy as np
import scipy.fft as fft
import scipy.signal as signal
from matplotlib.figure import Figure

class PlotWrapper:
    def __init__(self, fig): self.figure = fig

def sig_fft_plot(y, fs, size=(5, 3)):
    y = np.array(y).flatten()
    if len(y) == 0: return "Leeres Signal"

    fs = float(fs)
    N = len(y)
    T = 1.0 / fs
    yf = fft.fft(y)
    xf = fft.fftfreq(N, T)[:N//2]

    fig = Figure(figsize=size, dpi=100)
    ax = fig.add_subplot(111)
    ax.plot(xf, 2.0/N * np.abs(yf[0:N//2]))
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_title("FFT Spektrum")
    ax.set_xlabel("Frequenz [Hz]")
    ax.set_ylabel("Amplitude")
    return PlotWrapper(fig)

def sig_gen_sine(freq, duration, fs):
    t = np.linspace(0, float(duration), int(float(fs)*float(duration)), endpoint=False)
    s = np.sin(2 * np.pi * float(freq) * t)
    return t, s

toolbox_meta = {
    'name': 'Signalverarbeitung',
    'functions': {
        'fft_plot': sig_fft_plot,
        'gen_sine': sig_gen_sine,
        'sawtooth': signal.sawtooth,
        'square': signal.square
    },
    'demo_code': """# Signal Demo
fs = 1000.0
t, s1 = gen_sine(50, 1.0, fs)
t, s2 = gen_sine(120, 1.0, fs)
sig = s1 + 0.5 * s2
fft_plot(sig, fs, size=(6,4))"""
}
