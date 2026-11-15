"""Recalibración global de conteos; conserva el orden de priorización."""
import numpy as np


class ModeloCalibrado:
    def __init__(self, modelo, factor, anio_factor):
        if not np.isfinite(factor) or factor <= 0:
            raise ValueError("El factor de recalibración debe ser finito y positivo")
        self.modelo = modelo
        self.factor = float(factor)
        self.anio_factor = int(anio_factor)

    def predict_rate(self, f):
        return self.modelo.predict_rate(f) * self.factor
