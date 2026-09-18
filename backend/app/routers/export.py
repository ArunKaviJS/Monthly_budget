"""
export.py — Export the signed-in user's data as CSV or JSON.
"""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..database import get_db
from ..security import get_current_user
from .. import crud

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/json")
def export_json(
    month: Optional[str] = Query(None, description="YYYY-MM"),
    book_id: Optional[int] = Query(None, description="Filter by book"),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Export expenses as JSON."""
    data = crud.export_expenses(db, user["_id"], month=month, book_id=book_id)
    return JSONResponse(content=data)


@router.get("/csv")
def export_csv(
    month: Optional[str] = Query(None, description="YYYY-MM"),
    book_id: Optional[int] = Query(None, description="Filter by book"),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Export expenses as CSV."""
    data = crud.export_expenses(db, user["_id"], month=month, book_id=book_id)
    if not data:
        return StreamingResponse(
            io.StringIO("No data"),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)

    filename = f"expenses_{month}.csv" if month else "expenses_all.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
