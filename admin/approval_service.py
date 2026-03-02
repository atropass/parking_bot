from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from fastapi.responses import HTMLResponse
from db.sql_store import (
    get_pending_reservations,
    get_reservation,
    update_reservation_status,
)


app = FastAPI(
    title="Parking Admin API",
    description="Human-in-the-loop reservation approval service",
    version="1.0.0",
)


class ApprovalRequest(BaseModel):
    comment: Optional[str] = Field(
        default=None,
        description="Optional comment from admin (e.g., 'Approved for VIP customer')"
    )


class RejectionRequest(BaseModel):
    reason: str = Field(
        description="Required reason for rejection (e.g., 'No space available')"
    )


class ReservationResponse(BaseModel):
    id: int
    full_name: str
    license_plate: str
    start_datetime: str
    end_datetime: str
    zone_preference: Optional[str]
    status: str
    created_at: str
    reviewed_at: Optional[str]
    admin_comment: Optional[str]


class PendingReservationResponse(BaseModel):
    id: int
    full_name: str
    license_plate: str
    start_datetime: str
    end_datetime: str
    zone_preference: Optional[str]
    created_at: str


class StatusResponse(BaseModel):
    success: bool
    message: str


@app.get("/")
def root():
    return {"status": "ok", "service": "Parking Admin API"}


@app.get("/admin/pending", response_model=list[PendingReservationResponse])
def list_pending_reservations():
    pending = get_pending_reservations()
    return pending


@app.get("/admin/reservation/{reservation_id}", response_model=ReservationResponse)
def get_reservation_details(reservation_id: int):
    reservation = get_reservation(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation {reservation_id} not found")
    return reservation


@app.post("/admin/approve/{reservation_id}", response_model=StatusResponse)
def approve_reservation(reservation_id: int, request: ApprovalRequest):
    reservation = get_reservation(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation {reservation_id} not found")

    if reservation["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation {reservation_id} is already {reservation['status']}"
        )

    success = update_reservation_status(
        reservation_id=reservation_id,
        status="approved",
        admin_comment=request.comment,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reservation")

    return StatusResponse(
        success=True,
        message=f"Reservation {reservation_id} approved successfully"
    )


@app.post("/admin/reject/{reservation_id}", response_model=StatusResponse)
def reject_reservation(reservation_id: int, request: RejectionRequest):
    reservation = get_reservation(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail=f"Reservation {reservation_id} not found")

    if reservation["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation {reservation_id} is already {reservation['status']}"
        )

    success = update_reservation_status(
        reservation_id=reservation_id,
        status="rejected",
        admin_comment=request.reason,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update reservation")

    return StatusResponse(
        success=True,
        message=f"Reservation {reservation_id} rejected: {request.reason}"
    )


@app.get("/admin/dashboard", include_in_schema=False)
def admin_dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Parking Admin Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .reservation { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
            button { padding: 8px 15px; margin: 5px; cursor: pointer; }
            .approve { background: #4CAF50; color: white; border: none; }
            .reject { background: #f44336; color: white; border: none; }
        </style>
    </head>
    <body>
        <h1>Parking Reservation Admin</h1>
        <p>Use the API endpoints to approve/reject reservations.</p>
        <ul>
            <li>GET <code>/admin/pending</code> - List pending reservations</li>
            <li>POST <code>/admin/approve/{id}</code> - Approve reservation</li>
            <li>POST <code>/admin/reject/{id}</code> - Reject reservation</li>
        </ul>
        <p>Access <a href="/docs">Interactive API Docs</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
