from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from leprikon.models.school import School, SchoolDataSource

DEFAULT_URL = "https://lkod-ftp.msmt.gov.cz/00022985/88a7c12b-6084-4e47-8b50-46097c6e683f/RSSZ-cela-CR.jsonld"


def _format_street(addr: dict) -> str:
    parts = []
    ulice = addr.get("ulice")
    if ulice:
        parts.append(str(ulice))
    cislo_dom = addr.get("cisloDomovni")
    typ = addr.get("typCislaDomovniho")
    if cislo_dom:
        if typ:
            parts.append(f"{typ} {cislo_dom}")
        else:
            parts.append(str(cislo_dom))
    cislo_or = addr.get("cisloOrientacni")
    dodatek = addr.get("dodatekOrientacnihoCisla")
    if cislo_or:
        s = str(cislo_or)
        if dodatek:
            s += str(dodatek)
        parts.append(s)
    return ", ".join([p for p in parts if p])


def _city_from_addr(addr: dict) -> str:
    # Prefer obec; castObce as additional context if present and different
    obec = (addr.get("obec") or "").strip()
    cast = (addr.get("castObce") or "").strip()
    if obec and cast and cast != obec:
        return f"{obec} ({cast})"
    return obec or cast


def upsert_school(item: dict) -> School:
    red_izo = (item.get("redIzo") or "").strip()
    ico = (item.get("ico") or "").strip()
    name = (item.get("uplnyNazev") or item.get("zkracenyNazev") or "").strip()
    addr = item.get("adresa") or {}
    street = _format_street(addr)
    city = _city_from_addr(addr)
    zip_code = (addr.get("psc") or "").strip()
    ruian_code = addr.get("kodRUIAN")
    region = (item.get("kraj") or "").strip()

    defaults = {
        "ico": ico,
        "name": name,
        "street": street,
        "city": city,
        "zip_code": zip_code,
        "ruian_code": ruian_code if ruian_code is not None else None,
        "region": region,
    }

    if red_izo:
        obj, _created = School.objects.update_or_create(
            red_izo=red_izo,
            defaults=defaults,
        )
    else:
        # Fallback: try matching by name+city (less reliable)
        obj, created = School.objects.get_or_create(name=name, city=city, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(obj, k, v)
            obj.save(update_fields=list(defaults.keys()))
    return obj


def fetch_and_update(url: str = DEFAULT_URL) -> dict:
    ds, _ = SchoolDataSource.objects.get_or_create(url=url)

    headers = {}
    if ds.etag:
        headers["If-None-Match"] = ds.etag
    if ds.last_modified:
        headers["If-Modified-Since"] = ds.last_modified

    resp = requests.get(url, headers=headers, timeout=120)
    ds.last_checked = timezone.now()

    if resp.status_code == 304:
        ds.save(update_fields=["last_checked"])
        return {"status": "not_modified", "updated": 0}

    resp.raise_for_status()

    # Update caching headers
    etag = resp.headers.get("ETag")
    last_mod = resp.headers.get("Last-Modified")
    if etag is not None:
        ds.etag = etag
    if last_mod is not None:
        ds.last_modified = last_mod

    payload = resp.json()

    output_date = payload.get("datumVystupu")
    if output_date:
        try:
            ds.output_date = datetime.strptime(output_date, "%Y-%m-%d").date()
        except Exception:
            ds.output_date = None

    items = payload.get("list") or []
    updated = 0
    with transaction.atomic():
        for item in items:
            upsert_school(item)
            updated += 1
        ds.last_success = timezone.now()
        ds.save()

    return {"status": "ok", "updated": updated}


class Command(BaseCommand):
    help = "Fetch RSSZ JSON-LD of schools and upsert into leprikon.School"

    def add_arguments(self, parser):
        parser.add_argument("--url", dest="url", default=DEFAULT_URL)
        parser.add_argument("--no-conditional", action="store_true", dest="no_conditional", default=False)

    def handle(self, *args, **options):
        url = options["url"]
        if options.get("no_conditional"):
            # clear etag/last-modified to force download
            SchoolDataSource.objects.update_or_create(url=url, defaults={"etag": "", "last_modified": ""})
        result = fetch_and_update(url)
        self.stdout.write(self.style.SUCCESS(f"Schools update: {result['status']}, updated={result['updated']}"))
