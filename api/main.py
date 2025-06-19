from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import time
from api.Test import func 
from api.Test2 import specSheet
app = FastAPI()
starttime = time.perf_counter()
class EquipmentRequest(BaseModel):
    equipmentType: str
    modelNo: str
    manufacturer: Optional[str] = ""
    voltageRating: Optional[str] = ""

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
