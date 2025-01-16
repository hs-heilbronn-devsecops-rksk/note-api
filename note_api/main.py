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
from opentelemetry import trace
import uvicorn

app = FastAPI()

# OpenTelemetry Tracing
resource = Resource.create({"service.name": "note-api"})
tracer_provider = TracerProvider(resource=resource)
cloud_trace_exporter = CloudTraceSpanExporter()
span_processor = BatchSpanProcessor(cloud_trace_exporter)
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

my_backend: Optional[Backend] = None

def get_backend() -> Backend:
    global my_backend
    if my_backend is None:
        backend_type = getenv('BACKEND', 'memory')
        if backend_type == 'redis':
            my_backend = RedisBackend()
        elif backend_type == 'gcs':
            my_backend = GCSBackend()
        else:
            my_backend = MemoryBackend()
    return my_backend

@app.get("/")
def redirect_to_notes() -> None:
    return RedirectResponse(url="/notes")

@app.get("/notes")
def get_notes(backend: Annotated[Backend, Depends(get_backend)]) -> List[Note]:
    return [backend.get(key) for key in backend.keys()]

@app.get("/notes/{note_id}")
def get_note(note_id: str, backend: Annotated[Backend, Depends(get_backend)]) -> Note:
    return backend.get(note_id)

@app.put("/notes/{note_id}")
def update_note(note_id: str, request: CreateNoteRequest, backend: Annotated[Backend, Depends(get_backend)]) -> None:
    backend.set(note_id, request)

@app.post("/notes")
def create_note(request: CreateNoteRequest, backend: Annotated[Backend, Depends(get_backend)]) -> str:
    note_id = str(uuid4())
    backend.set(note_id, request)
    return note_id

if __name__ == "__main__":
    port = int(getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
