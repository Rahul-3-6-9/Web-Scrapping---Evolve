from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import time
from Test import func  # import your function

import os
print("FILES IN DIR:", os.listdir())

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
    return {
        "equipmentType": data.equipmentType,
        "modelNo": data.modelNo,
        "frontImageUrl": best_url or "Not found",
        "time taken": time.perf_counter() - starttime,
    }
