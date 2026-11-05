from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.vehiculos import router as vehiculos_router
from app.services.vehiculo import VehiculoError
from app.routers.celdas import router as celdas_router
from app.services.celda import CeldaError
from app.routers.usuarios import router as usuarios_router
from app.services.usuario import UsuarioError
from app.routers.estancias import router as estancias_router
from app.services.estancia import EstanciaError

app = FastAPI(title="Parkeo API")
app.include_router(vehiculos_router)
app.include_router(celdas_router)
app.include_router(usuarios_router)
app.include_router(estancias_router)


@app.exception_handler(VehiculoError)
@app.exception_handler(CeldaError)
@app.exception_handler(UsuarioError)
@app.exception_handler(EstanciaError)
async def entity_error_handler(request, error: VehiculoError | CeldaError | UsuarioError | EstanciaError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
