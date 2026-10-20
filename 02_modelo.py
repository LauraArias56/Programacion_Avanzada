"""Modelo RLM: Y=promedio_mensual, X1=maximo, X2=minimo. Muestra n=10. Sin sklearn (numpy puro)."""
import pandas as pd, numpy as np, calendar

df = pd.read_csv("datos_completos.csv")

# Muestra intencional estratificada (cubre rango bajo/medio/alto y 8 fuentes distintas)
filtros = [
    (2000,1,"AGUA"), (2000,1,"GAS"), (2000,2,"CARBON"), (2000,4,"OTROS"),
    (2001,2,"ACPM"), (2001,4,"GAS"), (2000,8,"BAGAZO"), (2000,12,"COMBUSTOLEO"),
    (2001,2,"JET-A1"), (2000,12,"AGUA"),
]
rows = []
for a,m,f in filtros:
    r = df[(df.ano==a)&(df.mes==m)&(df.fuente==f)]
    assert len(r)==1, (a,m,f,len(r))
    rows.append(r.iloc[0])
muestra = pd.DataFrame(rows).reset_index(drop=True)
muestra.to_csv("muestra_10.csv", index=False)
print(muestra[["ano","mes","fuente","promedio_mensual_gwh","maximo_gwh","minimo_gwh"]].to_string(index=True))

# --- Datos ---
y = muestra["promedio_mensual_gwh"].to_numpy(dtype=float)          # (10,)
X1 = muestra["maximo_gwh"].to_numpy(dtype=float)
X2 = muestra["minimo_gwh"].to_numpy(dtype=float)
m = len(y)
X = np.column_stack([np.ones(m), X1, X2])                          # diseño m x 3
print("\nVector y:", np.round(y,6))
print("X1:", np.round(X1,6))
print("X2:", np.round(X2,6))

# --- Ecuación normal paso a paso ---
XtX = X.T @ X
Xty = X.T @ y
print("\n=== XtX (3x3) ==="); print(np.round(XtX,6))
print("\n=== Xty (3x1) ==="); print(np.round(Xty,6))
det = np.linalg.det(XtX)
print(f"\ndet(XtX) = {det:.6f}")
XtX_inv = np.linalg.inv(XtX)
print("\n=== (XtX)^-1 ==="); print(np.round(XtX_inv,10))
theta = XtX_inv @ Xty
print(f"\n=== theta = [b0, b1, b2] ===\n{theta}")
print(f"b0={theta[0]:.6f}, b1={theta[1]:.6f}, b2={theta[2]:.6f}")

np.savetxt("XtX.csv", XtX, delimiter=",")
np.savetxt("XtX_inv.csv", XtX_inv, delimiter=",")
np.savetxt("theta.csv", theta, delimiter=",")

# --- Predicciones y métricas manuales ---
yhat = X @ theta
e = y - yhat
tabla = pd.DataFrame({"y":y,"y_hat":yhat,"e":e,"e2":e**2,"abs_e":np.abs(e)})
print("\n"+tabla.round(6).to_string())
SSE = float(np.sum(e**2)); MSE = SSE/m
RMSE = float(np.sqrt(MSE)); MAE = float(np.mean(np.abs(e)))
SST = float(np.sum((y-y.mean())**2)); R2 = 1-SSE/SST
n,p = m,2; R2adj = 1-(1-R2)*(m-1)/(m-p-1)
print(f"\nSSE={SSE:.6f}\nMSE={MSE:.6f}\nRMSE={RMSE:.6f}\nMAE={MAE:.6f}")
print(f"y_mean={y.mean():.6f}, SST={SST:.6f}\nR2={R2:.6f}\nR2_adj={R2adj:.6f}")
tabla.to_csv("tabla_metricas.csv", index_label="i")

# --- Gradiente descendente con features estandarizadas (para tabla de iteraciones) ---
mu1, sd1 = X1.mean(), X1.std(ddof=0); mu2, sd2 = X2.mean(), X2.std(ddof=0)
Z1 = (X1-mu1)/sd1; Z2 = (X2-mu2)/sd2
Z = np.column_stack([np.ones(m), Z1, Z2])
th = np.zeros(3); alpha=0.1; iters=2000
hist_J=[]; log=[]
for k in range(iters+1):
    err = Z@th - y
    J = float(err@err/(2*m))
    hist_J.append(J)
    if k<=10 or k%100==0 or k==iters:
        log.append((k,float(th[0]),float(th[1]),float(th[2]),J))
    grad = (Z.T@err)/m
    th = th - alpha*grad
print(f"\nEstandarización: mu1={mu1:.6f} sd1={sd1:.6f} | mu2={mu2:.6f} sd2={sd2:.6f}")
print("Iter | th0 | th1 | th2 | J")
for row in log: print(f"{row[0]:4d} | {row[1]:10.4f} | {row[2]:9.4f} | {row[3]:9.4f} | {row[4]:12.4f}")
# Devolver a escala original
b2_o = th[2]/sd2; b1_o = th[1]/sd1; b0_o = th[0]-th[1]*mu1/sd1-th[2]*mu2/sd2
print(f"\nTheta GD (escala original): b0={b0_o:.6f}, b1={b1_o:.6f}, b2={b2_o:.6f}")
print(f"Diferencia vs normal: {np.array([b0_o,b1_o,b2_o])-theta}")
pd.DataFrame(log, columns=["iter","th0","th1","th2","J"]).to_csv("gradiente_iters.csv", index=False)
np.savetxt("costo_hist.csv", np.array(hist_J), delimiter=",")

# --- Predicción nuevo dato ---
x1n, x2n = 20.0, 10.0
yn = theta[0]+theta[1]*x1n+theta[2]*x2n
print(f"\nNuevo dato: max={x1n}, min={x2n} -> y_pred={yn:.4f} GWh")
# Intervalo aprox ± RMSE
print(f"Intervalo aprox ±RMSE: [{yn-RMSE:.4f}, {yn+RMSE:.4f}]")

# --- Gráficos ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot(np.array(hist_J)); ax.set_xlabel("Iteración"); ax.set_ylabel("Costo J"); ax.set_title("Convergencia gradiente descendente (alpha=0.1)")
fig.savefig("fig_convergencia.png", dpi=150, bbox_inches="tight"); plt.close(fig)
fig, ax = plt.subplots()
ax.scatter(y, yhat); ax.plot([y.min(),y.max()],[y.min(),y.max()], linestyle="--")
ax.set_xlabel("y real (promedio GWh)"); ax.set_ylabel("y predicho"); ax.set_title("Real vs Predicho (n=10)")
fig.savefig("fig_real_vs_pred.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("\nArchivos: muestra_10.csv, tabla_metricas.csv, gradiente_iters.csv, theta.csv, fig_*.png OK")
