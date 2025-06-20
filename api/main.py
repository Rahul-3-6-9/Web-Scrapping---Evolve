from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import time
from .Test import func
from .Test2 import specSheet

app = FastAPI()
starttime = time.perf_counter()

class EquipmentRequest(BaseModel):
    equipmentType: str
    modelNo: str
    manufacturer: Optional[str] = ""
    voltageRating: Optional[str] = ""

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.post("/get-front-image")
async def get_front_image(data: EquipmentRequest):
    best_url = func(data.dict())
    spec_url = specSheet(data.dict(), max_pages=3, delay=2)
    return {
        "equipmentType": data.equipmentType,
        "modelNo": data.modelNo,
        "specSheetUrl": spec_url or "Not found",
        "frontImageUrl": best_url or "Not found",
        "time taken": time.perf_counter() - starttime,
    }
