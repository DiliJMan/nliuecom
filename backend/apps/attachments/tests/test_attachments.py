import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.attachments.models import Attachment
from apps.audit.models import AuditEvent

pytestmark = pytest.mark.django_db


def upload(client, domain, name="report.pdf", content=b"%PDF-1.7 hello", **extra):
    return client.post(
        "/api/attachments/",
        {"domain": str(domain.pk), "file": SimpleUploadedFile(name, content), **extra},
        format="multipart",
    )


def test_upload_records_checksum_and_neutral_storage_name(api, admin, tree):
    content = b"%PDF-1.7 evidence"
    response = upload(api(admin), tree["france"], "../../etc/passwd.pdf", content)
    assert response.status_code == 201, response.data
    assert response.data["sha256"] == hashlib.sha256(content).hexdigest()
    assert response.data["original_name"] == "passwd.pdf"
    stored = Attachment.objects.get()
    assert ".." not in stored.file.name and stored.file.name.startswith(str(tree["france"].pk))


@pytest.mark.parametrize("name", ["run.exe", "page.html", "script.js", "noextension", "a.svg"])
def test_unlisted_extensions_are_refused(api, admin, tree, name):
    assert upload(api(admin), tree["france"], name).status_code == 400


def test_empty_and_oversized_files_are_refused(api, admin, tree, settings):
    assert upload(api(admin), tree["france"], content=b"").status_code == 400
    settings.ATTACHMENT_MAX_BYTES = 10
    assert upload(api(admin), tree["france"], content=b"x" * 11).status_code == 400


def test_scoping_on_upload_and_download(api, make_user, tree, grant):
    contributor, outsider = make_user("c@example.com"), make_user("o@example.com")
    grant(contributor, "Contributor", tree["europe"])
    grant(outsider, "Reader", tree["asia"])
    assert upload(api(contributor), tree["asia"]).status_code == 403
    created = upload(api(contributor), tree["france"])
    assert created.status_code == 201
    url = f"/api/attachments/{created.data['id']}/"
    assert api(outsider).get(url).status_code == 404
    assert api(outsider).get(url + "download/").status_code == 404
    assert api(contributor).get(url + "download/").status_code == 200


def test_download_is_forced_and_audited(api, admin, tree):
    created = upload(api(admin), tree["france"], "note.txt", b"<script>alert(1)</script>")
    response = api(admin).get(f"/api/attachments/{created.data['id']}/download/")
    assert response["Content-Type"] == "application/octet-stream"
    assert "attachment" in response["Content-Disposition"]
    assert response["X-Content-Type-Options"] == "nosniff"
    b"".join(response.streaming_content)
    assert AuditEvent.objects.filter(action="access", object_type="attachments.attachment").exists()


def test_integrity_check_detects_modified_file(api, admin, tree):
    created = upload(api(admin), tree["france"])
    url = f"/api/attachments/{created.data['id']}/verify/"
    assert api(admin).post(url).data["intact"] is True
    stored = Attachment.objects.get()
    with stored.file.open("wb") as handle:
        handle.write(b"tampered")
    assert api(admin).post(url).data["intact"] is False


def test_link_must_point_to_an_existing_object(api, admin, tree):
    ok = upload(
        api(admin),
        tree["france"],
        linked_object_type="domains.domain",
        linked_object_id=str(tree["france"].pk),
    )
    assert ok.status_code == 201
    bad = upload(
        api(admin),
        tree["france"],
        linked_object_type="domains.domain",
        linked_object_id="00000000-0000-0000-0000-000000000000",
    )
    assert bad.status_code == 400
    half = upload(api(admin), tree["france"], linked_object_type="domains.domain")
    assert half.status_code == 400


def test_delete_removes_file_from_storage(api, admin, tree, django_capture_on_commit_callbacks):
    created = upload(api(admin), tree["france"])
    stored = Attachment.objects.get()
    name, storage = stored.file.name, stored.file.storage
    with django_capture_on_commit_callbacks(execute=True):
        assert api(admin).delete(f"/api/attachments/{created.data['id']}/").status_code == 204
    assert not storage.exists(name)
