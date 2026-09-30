from pathlib import Path

MAIN = Path(__file__).with_name("main.py")
ROUTES = Path(__file__).with_name("settings_routes.py")

if not ROUTES.exists():
    raise SystemExit("settings_routes.py is missing")

text = MAIN.read_text(encoding="utf-8-sig")

if "from settings_routes import router as settings_router" not in text:
    marker = "from auth_routes import router as auth_router"
    if marker not in text:
        raise SystemExit("Could not find auth_routes import in main.py")
    text = text.replace(
        marker,
        marker + "\nfrom settings_routes import router as settings_router",
        1,
    )

if "app.include_router(settings_router)" not in text:
    marker = "app.include_router(auth_router)"
    if marker not in text:
        raise SystemExit("Could not find app.include_router(auth_router) in main.py")
    text = text.replace(
        marker,
        marker + "\napp.include_router(settings_router)",
        1,
    )

MAIN.write_text(text, encoding="utf-8")
print("main.py updated successfully.")
print("settings router import + include_router verified.")
