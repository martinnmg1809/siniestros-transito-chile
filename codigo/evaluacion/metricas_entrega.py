"""Métricas complementarias del notebook: conteos y diagnóstico binario auxiliar.

No modifica las métricas ni el criterio de selección del experimento original.
El umbral binario es el percentil 95 del conteo predicho en entrenamiento,
con comparación estricta > para que una tasa constante no alerte por empates.
"""
import numpy as np
from sklearn.metrics import (roc_auc_score, average_precision_score, roc_curve,
                             precision_recall_curve, confusion_matrix)


def vectores(y, mu, expo):
    y, mu = np.asarray(y, float), np.asarray(mu, float)
    e = np.broadcast_to(expo, y.shape)
    ok = e > 0
    if y.shape != mu.shape or not np.isfinite(y[ok]).all() or not np.isfinite(mu[ok]).all():
        raise ValueError('Conteos o predicciones inválidos')
    if (y[ok] < 0).any() or (mu[ok] < 0).any():
        raise ValueError('Conteos negativos')
    return y[ok], mu[ok]


def metricas_conteo(y, mu, expo):
    yy, mm = vectores(y, mu, expo)
    yt = np.asarray(y).reshape(len(y), -1, 12).sum(axis=(0, 2))
    mt = np.asarray(mu).reshape(len(y), -1, 12).sum(axis=(0, 2))
    return {'mae_celda': float(np.abs(yy-mm).mean()),
            'rmse_celda': float(np.sqrt(np.mean((yy-mm)**2))),
            'rmse_total_turno': float(np.sqrt(np.mean((yt-mt)**2))),
            'mae_total_turno': float(np.abs(yt-mt).mean())}


def umbral_entrenamiento(y, mu, expo):
    _, score = vectores(y, mu, expo)
    return float(np.quantile(score, .95, method='higher'))


def diagnostico_binario(y, mu, expo, umbral, curvas=False):
    yy, score = vectores(y, mu, expo)
    etiqueta = yy > 0
    pred = score > umbral
    tn, fp, fn, tp = confusion_matrix(etiqueta, pred, labels=[False, True]).ravel()
    def div(a, b): return float(a/b) if b else 0.
    p, r = div(tp, tp+fp), div(tp, tp+fn)
    dos_clases = np.unique(etiqueta).size == 2
    met = {'umbral_train_p95': umbral, 'n_celdas': len(yy),
        'prevalencia': float(etiqueta.mean()), 'fraccion_alertada': float(pred.mean()),
        'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp),
        'accuracy': div(tp+tn, len(yy)), 'precision': p, 'recall': r,
        'f1': div(2*p*r, p+r), 'especificidad': div(tn, tn+fp),
        'balanced_accuracy': (r+div(tn, tn+fp))/2 if dos_clases else np.nan,
        'accuracy_siempre_cero': float((~etiqueta).mean()),
        'roc_auc': float(roc_auc_score(etiqueta, score)) if dos_clases else np.nan,
        'pr_auc_ap': float(average_precision_score(etiqueta, score)) if dos_clases else np.nan}
    puntos = []
    if curvas and dos_clases:
        fpr, tpr, _ = roc_curve(etiqueta, score)
        prec, rec, _ = precision_recall_curve(etiqueta, score, drop_intermediate=True)
        # Submuestrear solo los puntos dibujados; las áreas se calculan con todos los datos.
        for tipo, x, z in [('ROC', fpr, tpr), ('PR', rec, prec)]:
            ix = np.unique(np.linspace(0, len(x)-1, min(len(x), 800), dtype=int))
            puntos.extend({'curva': tipo, 'x': float(x[i]), 'y': float(z[i])} for i in ix)
    return met, puntos
