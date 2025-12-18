from typing import Literal, Optional

from pydantic import BaseModel, Field

from analytics.models import TimeWindow

Op = Literal["=", "!=", ">", ">=", "<", "<=", "in", "between", "like", "ilike"]


class ClientSegmentRequest(BaseModel):
    time: TimeWindow = Field(default_factory=TimeWindow)
    min_monthly_revenue: float = 40000
    uf: Optional[str] = None
    min_monthly_revenue: float = 40000
    uf: Optional[str] = None
