"""Local PDF extraction and Portbase XLS export. No documents are stored."""
from io import BytesIO
from pathlib import Path
import os
import re
import secrets
import time
from threading import Lock
from urllib.parse import urlsplit

import pdfplumber
import xlrd
from xlutils.filter import XLRDReader, XLWTWriter, process
from flask import Flask, jsonify, request, send_file
from waitress import serve

ROOT = Path(__file__).resolve().parent
MRN_PATTERN = re.compile(r"\b[0-9]{2}[A-Z]{2}[A-Z0-9]{14}\b")
app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
downloads = {}
download_lock = Lock()


def extract_truck(page):
    fields = [
        (r"Identity transport means at departure|Departure transport means", "19 05"),
        (r"Transport means at border", "19 04"),
        (r"Active border transport means", "19 08"),
    ]
    fallback = ("", "")
    for pattern, source in fields:
        anchors = page.search(pattern,case=False) or []
        if not anchors:
            continue
        anchor = anchors[0]
        # Stay inside the left-hand transport field, clear of neighbouring goods/delivery fields.
        words = page.extract_words()
        value_words = [w for w in words if w["x0"] >= anchor["x0"]-1 and w["x1"] < page.width*.53
                       and anchor["bottom"]+1 < w["top"] < anchor["bottom"]+14]
        value = " ".join(w["text"] for w in sorted(value_words,key=lambda w:w["x0"]))
        numbered = re.search(r"\bTRUCK\s+\d+(?:\s+\d+-[A-Z])?\b",value,re.I)
        if numbered:
            return numbered.group().upper(),source
        if not fallback[0] and re.search(r"\bTRUCK\b",value,re.I):
            fallback = (value,source)
    return fallback


def extract_document(data):
    if not data.startswith(b"%PDF-"):
        raise ValueError("Dit bestand is geen geldig PDF-bestand.")
    try:
        pdf = pdfplumber.open(BytesIO(data))
    except Exception as exc:
        raise ValueError("De PDF kan niet worden geopend. Controleer of deze beschadigd of beveiligd is.") from exc
    with pdf:
        if not pdf.pages or len(pdf.pages) > 50:
            raise ValueError("Gebruik een PDF met 1 tot 50 pagina’s.")
        page = pdf.pages[0]
        text = page.extract_text() or ""
        if not text.strip():
            raise ValueError("Deze PDF bevat geen leesbare tekst. Scans worden nog niet ondersteund.")
        header = page.crop((page.width * .5, 0, page.width, page.height * .3)).extract_text() or ""
        mrns = set(MRN_PATTERN.findall(header))
        warnings = []
        mrn = next(iter(mrns)) if len(mrns) == 1 else ""
        if not mrn:
            warnings.append("Het MRN bij de barcode is niet eenduidig gevonden. Controleer het document.")
        for following in pdf.pages[1:]:
            top = following.crop((following.width*.5, 0, following.width, following.height*.2)).extract_text() or ""
            following_mrns = set(MRN_PATTERN.findall(top))
            if following_mrns and (not mrn or following_mrns != {mrn}):
                raise ValueError("Deze PDF bevat verschillende MRN’s. Splits deze eerst in afzonderlijke documenten.")
        # Locate the explicitly labelled destination field, never a transit office or address.
        anchors = page.search(r"Country\s+of\s+destination", case=False) or []
        countries = set()
        for anchor in anchors:
            box = (anchor["x0"]-2, max(0,anchor["top"]-2), page.width, min(page.height,anchor["bottom"]+20))
            words = page.crop(box).extract_words()
            found = [w for w in words if re.fullmatch(r"[A-Z]{2}",w["text"])]
            if found:
                nearest = min(found, key=lambda w: abs(w["top"]-anchor["top"]))
                countries.add(nearest["text"])
        country = next(iter(countries)) if len(countries) == 1 else ""
        if not country:
            warnings.append("Country of destination is niet eenduidig gevonden. Vul het bestemmingsland in.")
        truck,truck_source = extract_truck(page)
        return {"mrn": mrn, "country": country, "type": "EU" if country == "GB" else "TT2" if country else "", "truck": truck, "truck_source": truck_source, "pages": len(pdf.pages), "warnings": warnings}


def export_workbook(documents):
    if not isinstance(documents, list) or not 1 <= len(documents) <= 200:
        raise ValueError("Exporteer 1 tot 200 documentregels.")
    seen = set()
    for number, doc in enumerate(documents, 1):
        if not isinstance(doc, dict):
            raise ValueError("Ongeldige documentregel.")
        for field in ["mrn", "country", "plate", "booking"]:
            value = doc.get(field)
            if not isinstance(value,str) or not value.strip() or len(value) > 100:
                raise ValueError(f"Regel {number}: vul MRN, bestemmingsland, kenteken en bookingnummer in.")
            doc[field] = value.strip()
        doc["mrn"] = doc["mrn"].upper()
        doc["country"] = doc["country"].upper()
        if not MRN_PATTERN.fullmatch(doc["mrn"]) or not re.fullmatch(r"[A-Z]{2}",doc["country"]):
            raise ValueError(f"Regel {number}: controleer het MRN (18 tekens) en de landcode (2 letters).")
        if doc["mrn"] in seen:
            raise ValueError("Hetzelfde MRN staat meerdere keren in de export. Controleer de documentregels.")
        seen.add(doc["mrn"])
    original = xlrd.open_workbook(ROOT / "templates" / "NEDTemplate.xls", formatting_info=True)
    sheet = original.sheet_by_index(0)
    assert [sheet.cell_value(2,c) for c in [0,1,4,5]] == ["DOCNR","DOCTYPE","TRANSPORTEQUIPMENTID","BOOKINGREF"]
    writer = XLWTWriter()
    process(XLRDReader(original, "NEDTemplate.xls"), writer)
    workbook = writer.output[0][1]
    for index,rgb in original.colour_map.items():
        if 8 <= index <= 63 and rgb is not None:
            workbook.set_colour_RGB(index,*rgb)
    target = workbook.get_sheet(0)
    for row,doc in enumerate(documents,3):
        values = {0:doc["mrn"],1:"EU" if doc["country"]=="GB" else "TT2",4:doc["plate"],5:doc["booking"]}
        for col,value in values.items():
            style = writer.style_list[sheet.cell_xf_index(row if row < sheet.nrows else 4,col)]
            target.write(row,col,value,style)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


@app.before_request
def local_requests_only():
    with download_lock:
        for token in list(downloads):
            if downloads[token][0] < time.monotonic():
                del downloads[token]
    if request.host.split(":")[0] not in {"localhost","127.0.0.1"}:
        return jsonify(error="Deze testomgeving is alleen lokaal bereikbaar."),403
    if request.path.startswith("/api/") and request.method=="POST":
        if request.headers.get("X-Portbase-Request") != "local":
            return jsonify(error="Ongeldige aanvraag."),403
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error="Ongeldige herkomst."),403


@app.after_request
def response_headers(response):
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Cache-Control"]="no-store"
    response.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/extract")
def extract():
    try:
        result=extract_document(request.get_data())
        return jsonify(result)
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    except Exception:
        return jsonify(error="Deze PDF kon niet worden uitgelezen. Probeer een andere PDF."),400


@app.post("/api/export")
@app.post("/api/prepare-export")
def export():
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict):
        return jsonify(error="Ongeldige exportaanvraag."),400
    try:
        output=export_workbook(payload.get("documents"))
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    if request.path == "/api/prepare-export":
        token = secrets.token_urlsafe(32)
        with download_lock:
            downloads[token] = (time.monotonic()+60,output.getvalue())
        return jsonify(download_url="/api/download/"+token)
    return send_file(output,mimetype="application/vnd.ms-excel",as_attachment=True,download_name="Portbase-import.xls")


@app.get("/api/download/<token>")
def download(token):
    with download_lock:
        item = downloads.pop(token,None)
    if not item or item[0] < time.monotonic():
        return jsonify(error="Deze download is verlopen. Klik opnieuw op Download importbestand."),404
    return send_file(BytesIO(item[1]),mimetype="application/vnd.ms-excel",as_attachment=True,download_name="Portbase-import.xls")


@app.errorhandler(413)
def too_large(error):
    return jsonify(error="Een bestand mag maximaal 20 MB groot zijn."),413


if __name__ == "__main__":
    port=int(os.environ.get("PORT","8766"))
    print(f"Portbase lokaal: http://127.0.0.1:{port}/",flush=True)
    serve(app,host="127.0.0.1",port=port,threads=4)
