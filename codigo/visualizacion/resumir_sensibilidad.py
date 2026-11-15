"""Figura de sensibilidad desde tablas verificadas, sin volver a entrenar."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    root=Path('resultados/sensibilidad')
    z=pd.read_csv(root/'poblacion_zona.csv').pivot(index='anio',columns='zona',values='eventos_evaluables')
    ll=pd.read_csv(root/'lluvia.csv')
    rural=pd.read_csv(root/'ajuste_rural/metricas.csv').query("modelo == 'Poisson_clima_rural'").set_index('anio')
    base=ll.query("escenario == 'actual'").set_index('anio')
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    z[['RURAL','URBANA']].plot.bar(stacked=True,ax=axes[0,0],color=['#267a91','#db8d36'],rot=0)
    axes[0,0].set(title='Zona registrada: urbanos solo en 2020–2021',ylabel='Siniestros',xlabel='Año')
    for name,color in [('actual','#23466e'),('A','#249b83'),('B','#d28828')]:
        d=ll[ll.escenario==name]
        axes[0,1].plot(d.anio,d.captura5*100,'o-',label=name,color=color)
    axes[0,1].set(title='Umbrales: captura global al 5 %',ylabel='Captura (%)',xticks=[2022,2023,2024])
    axes[0,1].legend(title='actual 0,1/0,5 · A 0,05/0,5 · B 0,1/1,0',fontsize=8,title_fontsize=8)
    for name,d,color in [('Original',base,'#23466e'),('Ajuste rural',rural,'#db8d36')]:
        axes[1,0].plot(d.index,d.captura5*100,'o-',label=name,color=color)
        axes[1,1].plot(d.index,d.observado_esperado,'o-',label=name,color=color)
    axes[1,0].set(title='Excluir urbanos del entrenamiento: captura',ylabel='Captura global al 5 % (%)',xticks=[2022,2023,2024])
    axes[1,1].set(title='Excluir urbanos del entrenamiento: nivel',ylabel='Observado / esperado',xticks=[2022,2023,2024])
    axes[1,1].axhline(1,color='gray',ls='--',lw=1)
    axes[1,0].legend();axes[1,1].legend()
    fig.suptitle('Sensibilidad exploratoria · Ruta 5 Sur\nModelos sin recalibrar; no se reselecciona la candidata')
    fig.savefig(root/'sensibilidad.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
