from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Settings, get_settings

from routers import __all__ as routers


def get_application(settings: Settings):
    application = FastAPI(
        title='SBS-Test-API',
        version='pre-release',
        debug=settings.DEBUG,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in routers:
        application.include_router(router)

    return application


app = get_application(get_settings())
