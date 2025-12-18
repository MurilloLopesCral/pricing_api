from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Op = Literal["=", "!=", ">", ">=", "<", "<=", "in", "between", "like", "ilike"]


class Filter(BaseModel):
    field: str
    op: Op
    value: Any


class Having(BaseModel):
    metric: str
    op: Literal["=", "!=", ">", ">=", "<", "<="]
    value: float


class OrderBy(BaseModel):
    metric: str
    dir: Literal["asc", "desc"] = "desc"


class TimeWindow(BaseModel):
    mode: Literal["rolling", "range"] = "rolling"
    days: Optional[int] = 90
    start: Optional[str] = None  # "YYYY-MM-DD"
    end: Optional[str] = None  # "YYYY-MM-DD"


class AnalyticsQuery(BaseModel):
    time: TimeWindow = Field(default_factory=TimeWindow)
    filters: list[Filter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    having: list[Having] = Field(default_factory=list)
    order_by: list[OrderBy] = Field(default_factory=list)
    limit: int = 200


class AnchorMonth(BaseModel):
    type: Literal["month"] = "month"
    year: int
    month: int


class CompareRequest(BaseModel):
    anchor: AnchorMonth
    window_days: int = 90
    filters: list[Filter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metric: str = "mc_percentual_ponderado"
