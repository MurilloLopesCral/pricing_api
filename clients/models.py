from typing import List, Optional

from pydantic import BaseModel, Field


class RecurringClientsRequest(BaseModel):
    year: int = Field(..., description="Ano de referência, ex: 2025")
    months: List[int] = Field(..., description="Lista de meses, ex: [10, 11]")
    uf: Optional[str] = Field(None, description="Filtrar por UF (opcional)")
    min_total_revenue: Optional[float] = Field(
        None, description="Faturamento mínimo total (opcional)"
    )


class RecurringClient(BaseModel):
    cliente: str
    faturamento_total: float


class RecurringClientsResponse(BaseModel):
    year: int
    months: List[int]
    clientes: List[RecurringClient]
    months: List[int]
    clientes: List[RecurringClient]
