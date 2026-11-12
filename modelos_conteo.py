"""Modelos comparables de conteo con exposición horaria explícita."""
import time
import numpy as np
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from modelo import ajustar

GRILLAS = {
    "Poisson": [{"l2": 3.0}, {"l2": .3}],
    "GradientBoosting": [{"max_leaf_nodes": 7, "max_iter": 160}, {"max_leaf_nodes": 31, "max_iter": 240}],
    "RandomForest": [{"max_depth": 12, "min_samples_leaf": 100}, {"max_depth": 18, "min_samples_leaf": 30}],
}


def columnas_variante(variante):
    if variante == "espacial":
        return [0]
    base = [0, 1, 2, 3, 4, 6]  # Tendencia numérica, no categoría de año futuro.
    if variante in ("clima", "clima_flujo"):
        base = [0, 1, 2, 3, 4, 5, 6]
    if variante == "clima_flujo":
        base += [7, 8]
    if variante not in ("calendario", "clima", "clima_flujo"):
        raise ValueError("Variante desconocida")
    return base


def elegir_configuracion(historial, familia, variante, cohorte, anio_prueba, tolerancia=.001):
    """Elegir con años previos exclusivamente; preferir sencillez a ≤0,1 pp."""
    filas = [r for r in historial if r["familia"] == familia and r["variante"] == variante
             and r["cohorte"] == cohorte and r["anio_prueba"] < anio_prueba]
    if not filas:
        return 0, []
    por_config = {}
    for i in range(len(GRILLAS[familia])):
        valores = [r["captura5"] for r in filas if r["configuracion"] == i]
        if not valores:
            raise ValueError("Configuración sin evaluación temporal previa")
        por_config[i] = float(np.mean(valores))
    mejor = max(por_config.values())
    elegida = min(i for i, valor in por_config.items() if valor >= mejor - tolerancia)
    return elegida, sorted({r["anio_prueba"] for r in filas})


class ModeloConteo:
    def __init__(self, familia, variante, parametros, semilla=42):
        self.familia, self.variante = familia, variante
        self.parametros, self.semilla = dict(parametros), semilla
        self.columnas = columnas_variante(variante)

    def _entrada(self, f):
        x = np.asarray(f[:, self.columnas], float)
        if not np.isfinite(x).all():
            raise ValueError("El modelo recibió atributos faltantes; no se imputa flujo desconocido")
        return x

    def fit(self, f, y, expo):
        t0 = time.monotonic()
        x = self._entrada(f)
        y, expo = np.asarray(y, float), np.asarray(expo, float)
        if len(x) != len(y) or y.shape != expo.shape or (y < 0).any() or (expo <= 0).any():
            raise ValueError("Datos/exposición inválidos")
        if self.familia == "GradientBoosting":
            categoricas = [c < 6 for c in self.columnas]
            self.modelo = HistGradientBoostingRegressor(loss="poisson", categorical_features=categoricas,
                            learning_rate=.05, min_samples_leaf=100, l2_regularization=1,
                            early_stopping=False, random_state=self.semilla, **self.parametros)
            self.modelo.fit(x, y / expo, sample_weight=expo)
            self.diagnostico = {"iteraciones": self.modelo.n_iter_, "early_stopping": False}
        else:
            cats = [i for i, c in enumerate(self.columnas) if c < 6]
            nums = [i for i, c in enumerate(self.columnas) if c >= 6]
            partes = [("categorias", OneHotEncoder(handle_unknown="ignore", dtype=np.float32), cats)]
            if nums:
                partes.append(("numericas", StandardScaler(), nums))
            self.transformador = ColumnTransformer(partes, sparse_threshold=1.0)
            xx = sparse.csr_matrix(self.transformador.fit_transform(x))
            if self.familia == "Poisson":
                xx = sparse.hstack([xx, np.ones((len(y), 1))]).tocsr()
                self.coef, self.diagnostico = ajustar(xx, y, expo, l2=self.parametros["l2"], devolver_diagnostico=True)
            elif self.familia == "RandomForest":
                self.modelo = RandomForestRegressor(n_estimators=80, criterion="poisson", bootstrap=True,
                                max_samples=min(80000, len(y)), max_features=.8, n_jobs=2,
                                random_state=self.semilla, **self.parametros)
                self.modelo.fit(xx, y / expo, sample_weight=expo)
                self.diagnostico = {"arboles": len(self.modelo.estimators_), "muestra_por_arbol": min(80000, len(y)),
                                    "criterio": "poisson", "hojas_sobre_filas_agrupadas": True}
            else:
                raise ValueError("Familia desconocida")
        self.diagnostico["segundos_ajuste"] = time.monotonic() - t0
        return self

    def predict_rate(self, f):
        x = self._entrada(f)
        if self.familia == "GradientBoosting":
            tasa = self.modelo.predict(x)
        else:
            xx = sparse.csr_matrix(self.transformador.transform(x))
            if self.familia == "Poisson":
                tasa = np.exp(xx @ self.coef[:-1] + self.coef[-1])
            else:
                tasa = self.modelo.predict(xx)
        if not np.isfinite(tasa).all() or (tasa < 0).any():
            raise ValueError("Predicción no finita o negativa")
        # RF puede producir hojas de tasa cero. Piso declarado para desvianza finita.
        return np.maximum(tasa, 1e-12)


class ModeloHibrido:
    """Usar el especialista solo con flujo completo; respaldo sin rellenar flujo."""
    def __init__(self, general, especialista, tramos_especialista):
        self.general, self.especialista = general, especialista
        self.tramos_especialista = np.asarray(tramos_especialista)

    def predict_rate(self, f):
        tasa = self.general.predict_rate(f)
        usar = np.isin(f[:, 0].astype(int), self.tramos_especialista)
        if self.especialista.variante == "clima_flujo":
            usar &= np.isfinite(f[:, [7, 8]]).all(axis=1)
        if usar.any():
            tasa[usar] = self.especialista.predict_rate(f[usar])
        return tasa
