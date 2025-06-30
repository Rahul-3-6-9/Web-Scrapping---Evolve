from fastapi import FastAPI
import time
from fastapi.responses import RedirectResponse
from .ImageURL import ImageURL
from .SpecSheetURL import SpecSheetURL
from .schemas import EquipmentRequest

app = FastAPI()
starttime = time.perf_counter()

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.post("/get-front-image")
async def get_front_image(data: EquipmentRequest):
    _ImageURL = ImageURL(data.dict())
    _SpecSheetURL = SpecSheetURL(data.dict())
    best_url = _ImageURL.imageURLFinder()
    spec_url = _SpecSheetURL.specSheet(max_pages=3, delay=2)
    return {
        "equipmentType": data.equipmentType,
        "modelNo": data.modelNo,
        "specSheetUrl": spec_url or "Not found",
        "frontImageUrl": best_url or "Not found",
        "time taken": time.perf_counter() - starttime,
    }
