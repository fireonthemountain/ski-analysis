"""End-to-end: a rendered synthetic clip / stills go through the real HTTP API.

Real stages exercised: multipart upload -> video decode + frame sampling -> pose
from PIXELS (colour-marker estimator standing in for MediaPipe) -> smoothing ->
turn segmentation -> metrics -> validation -> annotated frames + result.json.
"""
import json
import os
import time

import cv2
import pytest
from fastapi.testclient import TestClient

from pipeline.synthetic import RunSpec, SkierParams, write_sample_clip, write_sample_stills

SPEC = RunSpec(duration_s=8, fps=30, peak_inclination_deg=30, angulation_deg=14, knee_min_deg=118, knee_max_deg=166,
               stance_ratio=1.1, heading_deg=180)


@pytest.fixture(scope="module")
def client():
    import main
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    return write_sample_clip(str(tmp_path_factory.mktemp("media") / "synthetic_run.mp4"), SPEC)


def submit(client, assessment: dict, paths: list[str], user: str | None = None) -> dict:
    files = [("files", (os.path.basename(p), open(p, "rb"), "application/octet-stream")) for p in paths]
    headers = {"X-User-Id": user} if user else {}
    r = client.post("/api/v1/validations", data={"assessment": json.dumps(assessment)}, files=files, headers=headers)
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]
    for _ in range(600):
        body = client.get(f"/api/v1/validations/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.1)
    raise AssertionError("validation did not finish")


def items(**ratings):
    return [{"item_id": k, "rating": v} for k, v in ratings.items()]


def test_catalog_endpoint(client):
    body = client.get("/api/v1/assessment/catalog").json()
    ids = {i["id"] for i in body["items"]}
    assert {"stance_width", "edge_angle", "angulation", "separation", "pole_plant", "fore_aft", "turn_shape", "counter"} <= ids
    edge = next(i for i in body["items"] if i["id"] == "edge_angle")
    assert edge["bounds"] == [20.0, 40.0] and edge["needs_view"] == "frontal"


def test_video_end_to_end(client, clip):
    assessment = {"run_label": "synthetic clip", "items": items(
        edge_angle="moderate", angulation="moderate", stance_width="functional", turn_shape="round",
        turn_symmetry="symmetric", pole_plant="on_time",
        stance_height="tall",          # 2D-only + front view: must NOT get a verdict
        separation="moderate",         # needs 3D, which the marker estimator does not have
        fore_aft="centered")}          # needs a side view
    body = submit(client, assessment, [clip], user="e2e-video")
    assert body["status"] == "completed", body.get("error")
    res = body["result"]
    by = {r["item_id"]: r for r in res["results"]}

    assert res["media"]["kind"] == "video" and res["media"]["analysis_fps"] == 15.0
    assert res["pose"]["frames"] == pytest.approx(120, abs=2) and res["pose"]["frames_detected"] >= 115
    assert res["view"] == {"view": "frontal", "source": "auto", "facing": "toward camera"}
    assert len(res["turns"]) == 8 and res["turns"][0]["direction"] == "right"

    for k in ("edge_angle", "angulation", "stance_width", "turn_shape", "turn_symmetry", "pole_plant"):
        assert by[k]["verdict"] == "agree", (k, by[k]["reason"])
    assert by["edge_angle"]["measured"]["value"] == pytest.approx(30, abs=2.5)       # ground truth 30 deg
    assert by["angulation"]["measured"]["value"] == pytest.approx(12, abs=3)
    assert by["stance_width"]["measured"]["value"] == pytest.approx(1.1, abs=0.12)
    assert by["separation"]["verdict"] == "inconclusive" and "3D" in by["separation"]["reason"]
    assert by["fore_aft"]["verdict"] == "inconclusive" and "side view" in by["fore_aft"]["reason"]
    assert by["stance_height"]["verdict"] == "inconclusive" and "foreshortens" in by["stance_height"]["reason"]
    assert res["summary"] == {"agree": 6, "disagree": 0, "inconclusive": 3, "total": 9, "decided": 6, "agreement_rate": 1.0}

    # evidence frames exist, are served, and are real images
    ev = by["edge_angle"]["evidence"]
    assert ev and ev[0]["image"].startswith("frames/")
    r = client.get(f"/api/v1/validations/{body['id']}/files/{ev[0]['image']}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and len(r.content) > 5000
    assert set(res["series"]) >= {"t", "inclination", "edge_proxy", "angulation", "pose_conf"}
    assert len(res["series"]["t"]) == res["pose"]["frames"]
    if res["annotated_video"]:
        assert client.get(f"/api/v1/validations/{body['id']}/files/annotated.mp4").status_code == 200
    # path traversal is refused
    assert client.get(f"/api/v1/validations/{body['id']}/files/../result.json").status_code == 404
    assert client.get(f"/api/v1/validations/{body['id']}/files/result.json").status_code == 404


def test_wrong_assessment_disagrees_end_to_end(client, clip):
    body = submit(client, {"items": items(edge_angle="high", angulation="banked", stance_width="narrow", turn_shape="abrupt")}, [clip])
    by = {r["item_id"]: r for r in body["result"]["results"]}
    assert all(r["verdict"] == "disagree" for r in by.values()), {k: v["reason"] for k, v in by.items()}
    assert body["result"]["summary"]["agreement_rate"] == 0.0


def test_screenshots_end_to_end(client, tmp_path):
    paths = write_sample_stills(str(tmp_path), [
        SkierParams(heading_deg=180, inclination_deg=33, angulation_deg=14, knee_angle_deg=130, stance_ratio=1.1),
        SkierParams(heading_deg=180, inclination_deg=-30, angulation_deg=12, knee_angle_deg=135, stance_ratio=1.1),
        SkierParams(heading_deg=180, inclination_deg=5, knee_angle_deg=150, stance_ratio=1.0),
    ])
    body = submit(client, {"run_label": "stills", "items": items(
        edge_angle="moderate", angulation="moderate", stance_width="functional",
        turn_shape="round", pole_plant="on_time", vertical_movement="active")}, paths)
    assert body["status"] == "completed", body.get("error")
    res = body["result"]
    by = {r["item_id"]: r for r in res["results"]}
    assert res["media"]["kind"] == "images" and res["turns"] == [] and res["annotated_video"] is None
    assert len(res["gallery"]) == 3 and all(g["detected"] for g in res["gallery"])
    for k in ("edge_angle", "angulation", "stance_width"):
        assert by[k]["verdict"] == "agree", (k, by[k]["reason"])
    assert by["edge_angle"]["measured"]["value"] == pytest.approx(33, abs=2.5)
    for k in ("turn_shape", "pole_plant", "vertical_movement"):
        assert by[k]["verdict"] == "inconclusive" and "Needs video" in by[k]["reason"]


def test_blank_media_never_gets_a_verdict(client, tmp_path):
    import numpy as np
    p = str(tmp_path / "blank.png")
    cv2.imwrite(p, np.full((480, 640, 3), 200, np.uint8))
    body = submit(client, {"items": items(edge_angle="moderate", stance_width="functional", angulation="moderate")}, [p])
    assert body["status"] == "completed"
    assert all(r["verdict"] == "inconclusive" and r["measured"] is None for r in body["result"]["results"])
    assert "No skier was detected" in body["result"]["results"][0]["reason"]
    assert body["result"]["warnings"]


def test_bad_requests(client, clip, tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("hi")
    post = lambda a, paths: client.post("/api/v1/validations", data={"assessment": a},
                                        files=[("files", (os.path.basename(p), open(p, "rb"))) for p in paths])
    ok = json.dumps({"items": items(edge_angle="low")})
    assert post("{not json", [clip]).status_code == 422
    assert post(json.dumps({"items": items(edge_angle="enormous")}), [clip]).status_code == 422
    assert post(json.dumps({"items": []}), [clip]).status_code == 422
    assert post(ok, [str(txt)]).status_code == 400
    assert post(ok, [clip, clip]).status_code == 400
    assert client.get("/api/v1/validations/not-a-uuid").status_code == 400


def test_runs_are_scoped_to_x_user_id(client, tmp_path):
    p = write_sample_stills(str(tmp_path), [SkierParams(heading_deg=180, inclination_deg=30, angulation_deg=10)])
    body = submit(client, {"items": items(edge_angle="moderate")}, p, user="alice")
    mine = client.get("/api/v1/validations", headers={"X-User-Id": "alice"}).json()
    assert mine["user"] == "alice" and body["id"] in [v["id"] for v in mine["validations"]]
    other = client.get("/api/v1/validations", headers={"X-User-Id": "bob"}).json()
    assert body["id"] not in [v["id"] for v in other["validations"]]
    assert client.get(f"/api/v1/validations/{body['id']}", headers={"X-User-Id": "bob"}).status_code == 404
    assert client.get("/api/v1/validations", headers={"X-User-Id": "bad id!"}).status_code == 400
    assert client.delete(f"/api/v1/validations/{body['id']}", headers={"X-User-Id": "alice"}).status_code == 204
    assert client.get(f"/api/v1/validations/{body['id']}", headers={"X-User-Id": "alice"}).status_code == 404


def test_legacy_photo_upload_uses_x_user_id(client, tmp_path):
    """Ledger ski-analysis-2: the upload endpoint no longer writes a hardcoded user id."""
    from api.users import user_uuid
    p = write_sample_stills(str(tmp_path), [SkierParams(heading_deg=90, knee_angle_deg=140)])[0]
    up = lambda headers: client.post("/api/v1/videos/upload", files={"file": ("skier.png", open(p, "rb"), "image/png")}, headers=headers)
    r = up({"X-User-Id": "carol"})
    assert r.status_code == 201, r.text
    vid = r.json()["video_id"]
    assert client.get(f"/api/v1/videos/{vid}").json()["user_id"] == str(user_uuid("carol"))
    r2 = up({})                                           # still works with no header
    assert r2.status_code == 201
    assert client.get(f"/api/v1/videos/{r2.json()['video_id']}").json()["user_id"] == str(user_uuid("anonymous"))
    # legacy analysis + skeleton overlay still work on local storage
    a = client.get(f"/api/v1/analysis/{vid}")
    assert a.status_code == 200 and a.json()["overall_score"] is not None
    sk = client.get(f"/api/v1/analysis/{vid}/skeleton")
    assert sk.status_code == 200 and sk.headers["content-type"] == "image/jpeg"
