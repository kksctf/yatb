"""Domain services: request-shaped logic that more than one router needs.

Routers in `api/` and `view/` are meant to be thin mappers over these — a service
returns *what happened*, and each router decides how to say it (JSON status codes vs
htmx toasts). Nothing here may import from `fastapi.HTTPException` territory.
"""
