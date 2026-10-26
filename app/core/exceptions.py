from fastapi import HTTPException, status


class DomainException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class ResourceNotFoundException(DomainException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with identifier '{identifier}' was not found."
        )


class SlotConflictException(DomainException):
    def __init__(self, detail: str = "The requested appointment slot is already taken."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class InvalidBookingException(DomainException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class AppointmentAlreadyCancelledException(DomainException):
    def __init__(self, detail: str = "This appointment has already been cancelled."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
