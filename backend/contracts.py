"""Response contracts and middleware controls documented in OpenAPI."""
from typing import Literal
from pydantic import BaseModel
from fastapi.openapi.utils import get_openapi


class Health(BaseModel):
    status: str
    stages: int


class Stage(BaseModel):
    id: int
    title: str
    location: str
    category: str
    weight: int
    summary: str


class Catalog(BaseModel):
    stages: list[Stage]
    organizer: str
    event: str
    reward: str
    logo_ready: bool


class Progress(BaseModel):
    solved: list[int]
    points: int
    hints: dict[str, int]


class Session(BaseModel):
    name: str
    csrf: str
    modes: dict[Literal['easy', 'hard'], Progress]


class Clue(Stage):
    payload: str
    objective: str
    hints: list[str]
    sample: str
    tool: str
    artifact_name: str
    debrief: str | None


class Hints(BaseModel):
    hints: list[str]


class AnswerResult(BaseModel):
    correct: bool
    detail: str | None = None
    debrief: str | None = None
    session: Session | None = None


class Treasure(BaseModel):
    name: str
    reward: str
    event: str
    code: str
    mode: Literal['easy', 'hard']
    seconds: int
    instruction: str
    logo_ready: bool


class Entry(BaseModel):
    name: str
    solved: int
    points: int
    seconds: int | None


class Leaderboard(BaseModel):
    items: list[Entry]
    total: int
    offset: int
    limit: int


def document_controls(app):
    def schema():
        if app.openapi_schema:
            return app.openapi_schema
        data = get_openapi(title=app.title, version=app.version, routes=app.routes,
                           description='CMC Infrasec × NextFest 26. Guest sessions, five beginner puzzles, separate Easy/Hard leaderboards and completion rewards. Private event application.')
        data['servers'] = [{'url': '/', 'description': 'Same-origin application; API is proxied by Next.js.'}]
        data['security'] = []
        components = data.setdefault('components', {})
        components['securitySchemes'] = {'CookieSession': {'type': 'apiKey', 'in': 'cookie', 'name': 'expedition', 'description': 'Opaque HttpOnly SameSite=Strict guest cookie; expires after 30 days.'}}
        components.setdefault('schemas', {})['Problem'] = {
            'type': 'object', 'required': ['type', 'title', 'status', 'detail'],
            'properties': {'type': {'type': 'string'}, 'title': {'type': 'string'}, 'status': {'type': 'integer'}, 'detail': {'type': 'string'}}}
        descriptions = {400: 'Malformed request.', 401: 'Guest session missing or expired.', 403: 'Origin, custom header or CSRF validation failed.',
                        404: 'Unknown destination.', 409: 'Destination or treasure is locked.', 413: 'Request exceeds 4096 bytes.', 422: 'Invalid input.', 429: 'Rate limit reached.'}
        for path, methods in data['paths'].items():
            for method, operation in methods.items():
                public = path in ('/health', '/api/v1/catalog', '/api/v1/leaderboard') or (path == '/api/v1/session' and method == 'post')
                operation['security'] = [] if public else [{'CookieSession': []}]
                if method == 'post':
                    parameters = operation.setdefault('parameters', [])
                    parameters.extend([
                        {'name': 'Origin', 'in': 'header', 'required': True, 'schema': {'type': 'string'}, 'description': 'An origin configured in APP_ORIGINS.'},
                        {'name': 'X-Expedition', 'in': 'header', 'required': True, 'schema': {'type': 'string', 'const': '1'}, 'description': 'Application request marker.'},
                    ])
                    if not public:
                        parameters.append({'name': 'X-CSRF-Token', 'in': 'header', 'required': True, 'schema': {'type': 'string'}, 'description': 'csrf value returned by the authenticated session read.'})
                for status, description in descriptions.items():
                    operation['responses'].setdefault(str(status), {'description': description, 'content': {'application/problem+json': {'schema': {'$ref': '#/components/schemas/Problem'}}}})
        # The artifact is intentionally binary PNG or inert UTF-8 text, never HTML.
        data['paths']['/api/v1/stages/{stage}/artifact']['get']['responses']['200']['content'] = {
            'image/png': {'schema': {'type': 'string', 'format': 'binary'}},
            'text/plain': {'schema': {'type': 'string'}}}
        app.openapi_schema = data
        return data
    app.openapi = schema
