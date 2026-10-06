import uvicorn


def main() -> None:
    uvicorn.run("api.app:create_app", factory=True, host="0.0.0.0", port=8000)
