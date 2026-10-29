"""Headless Chromium smoke test of the exact generated static MRI preview."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/"preview-dist"

def main():
    if not (ROOT/"index.html").is_file() or not (ROOT/"data/mri_public.json").is_file():
        raise SystemExit("generated preview missing")
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=1)
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            response=page.goto(f"http://127.0.0.1:{server.server_port}/index.html",wait_until="networkidle")
            assert response is not None and response.status==200
            page.locator("article").first.wait_for()
            assert page.locator("article").count()==2
            assert page.get_by_text("Pokémon Chine — 2022").count()==1
            assert page.get_by_text("LEGO Black Pearl — 2025").count()==1
            assert page.locator("article a").count()==3
            assert page.get_by_text("2 dossiers de recherche affichés",exact=False).count()==1
            assert not errors, errors
            page.screenshot(path=str(ROOT/"browser-screenshot.png"),full_page=True)
            print("Chromium 390x844: 2 research cases, 3 safe links, 0 JS errors — PASS")
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=3)

if __name__=="__main__":
    main()
