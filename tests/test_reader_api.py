import asyncio
import json

import app.reader_api as reader_api
import app.service as service


def test_reader_endpoints_with_sample_project(tmp_path, monkeypatch):
    monkeypatch.setattr(reader_api, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(service, "OUTPUT_DIR", tmp_path)

    proj_id = "20261125-sample-123456"
    proj_dir = tmp_path / proj_id
    proj_dir.mkdir(parents=True)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00"
        b"\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    img_path = proj_dir / "page-001-panel-01-view-01.png"
    img_path.write_bytes(png_bytes)
    (proj_dir / "project.json").write_text(
        json.dumps(
            {
                "project_id": proj_id,
                "status": "completed",
                "request": {"brief": "Test comic", "style": "japanese_manga", "language": "he"},
                "plan": {"title": "Test Title", "style": "japanese_manga", "language": "he", "pages": []},
                "images": [f"/outputs/{proj_id}/page-001-panel-01-view-01.png"],
            }
        ),
        encoding="utf-8",
    )

    async def _run():
        info = await reader_api.lanraragi_info()
        assert info["name"] == "Comics AI Studio"

        search = await reader_api.lanraragi_search(filter="", start=0, sortby="title", order="asc")
        assert search["recordsTotal"] == 1
        assert search["data"][0]["arcid"] == proj_id

        files = await reader_api.lanraragi_files(proj_id)
        assert len(files["pages"]) == 1
        assert "page-001-panel-01-view-01.png" in files["pages"][0]

        page_resp = await reader_api.lanraragi_page(proj_id, path="page-001-panel-01-view-01.png")
        assert page_resp.path == img_path

        thumb_resp = await reader_api.lanraragi_thumbnail(proj_id)
        assert thumb_resp.path == img_path

        opds = await reader_api.opds_catalog()
        opds_text = opds.body.decode("utf-8")
        assert "Test Title" in opds_text
        assert "format=cbz" in opds_text

    asyncio.run(_run())
