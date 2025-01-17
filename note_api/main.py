# -*- coding: utf-8 -*-
from uuid import uuid4
from typing import List, Optional
from os import getenv
from typing_extensions import Annotated

from fastapi import Depends, FastAPI
from starlette.responses import RedirectResponse
from .backends import Backend, RedisBackend, MemoryBackend, GCSBackend
from .model import Note, CreateNoteRequest

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import get_tracer
from opentelemetry import trace
import uvicorn

app = FastAPI()

resource = Resource.create({"service.name": "note-api"})
tracer_provider = TracerProvider(resource=resource)
cloud_trace_exporter = CloudTraceSpanExporter()
span_processor = BatchSpanProcessor(cloud_trace_exporter)
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

tracer = get_tracer(__name__)

my_backend: Optional[Backend] = None

def get_backend() -> Backend:
    global my_backend  # pylint: disable=global-statement
    if my_backend is None:
        backend_type = getenv('BACKEND', 'memory')
        print(backend_type)
        if backend_type == 'redis':
            my_backend = RedisBackend()
        elif backend_type == 'gcs':
            my_backend = GCSBackend()
        else:
            my_backend = MemoryBackend()
    return my_backend

@app.get('/')
def redirect_to_notes() -> None:
    return RedirectResponse(url='/notes')

@app.get('/notes')
def get_notes(backend: Annotated[Backend, Depends(get_backend)]) -> List[Note]:
    with tracer.start_as_current_span("get_notes_span"):
        keys = backend.keys()

        Notes = []
        for key in keys:
            Notes.append(backend.get(key))
        return Notes

@app.get('/notes/{note_id}')
def get_note(note_id: str,
             backend: Annotated[Backend, Depends(get_backend)]) -> Note:
    with tracer.start_as_current_span("get_note_span"):
        return backend.get(note_id)

@app.put('/notes/{note_id}')
def update_note(note_id: str,
                request: CreateNoteRequest,
                backend: Annotated[Backend, Depends(get_backend)]) -> None:
    with tracer.start_as_current_span("update_note_span"):
        backend.set(note_id, request)

@app.post('/notes')
def create_note(request: CreateNoteRequest,
                backend: Annotated[Backend, Depends(get_backend)]) -> str:
    with tracer.start_as_current_span("create_note_span"):
        note_id = str(uuid4())
        backend.set(note_id, request)
        return note_id

if __name__ == "__main__":
    port = int(getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
