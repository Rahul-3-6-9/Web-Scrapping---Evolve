from pydantic import BaseModel
from typing import Optional

class EquipmentRequest(BaseModel):
    equipmentType: str = "EV Charger"
    modelNo: str = "Terra 54"
    manufacturer: Optional[str] = "ABB"
    voltageRating: Optional[str] = "480"