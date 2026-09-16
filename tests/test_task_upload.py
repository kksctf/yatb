import asyncio
import hashlib
import importlib
import io
import json
import tarfile
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import TYPE_CHECKING, BinaryIO
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from yatb.yatb.schema import Task


@pytest.fixture
def upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    # Importing the CLI also loads S3/DTC settings; no external services are used.
    for name, value in {
        "S3_HOST": "localhost",
        "S3_ACCESS": "test",
        "S3_SECRET": "test",
        "S3_HOST_KANIKO": "localhost",
        "S3_PORT_KANIKO": "9000",
        "DOCKER_REGISTRY_HOST": "localhost",
        "DOCKER_REGISTRY_PORT": "5000",
        "EXTERNAL_TO_INTERNAL_IPS_MAPPING": "{}",
        "DYNAMIC_TASKS_ETCD": "localhost",
    }.items():
        monkeypatch.setenv(name, value)

    tasks = importlib.import_module("yatb.cli.cmd.tasks")
    schema = importlib.import_module("yatb.yatb.schema")
    minio = importlib.import_module("yatb.s3.client").MinioEx
    monkeypatch.setattr(tasks.settings, "PUBLIC_FILES_DOMAIN", "https://files.example.org/")
    objects: dict[tuple[str, str], tuple[bytes, dict[str, str]]] = {}

    async def stat(bucket: str, name: str) -> SimpleNamespace:
        data, metadata = objects.get((bucket, name), (b"", {}))
        return SimpleNamespace(size=len(data), metadata=metadata)

    async def put(bucket: str, name: str, data: BinaryIO, *, length: int, metadata: dict[str, str]) -> None:
        content = data.read()
        assert len(content) == length
        objects[bucket, name] = (
            content,
            {f"x-amz-meta-{key}": value for key, value in metadata.items()},
        )

    s3 = SimpleNamespace(stat_object=AsyncMock(side_effect=stat), put_object=AsyncMock(side_effect=put))
    # Exercise the real hashing, archive creation, and cache-hit paths.
    s3.upload_directory = MethodType(minio.upload_directory, s3)
    s3.intelligent_put_object = MethodType(minio.intelligent_put_object, s3)
    user = schema.User.model_construct(username="admin")
    api = SimpleNamespace(
        s3=s3,
        create_task_full_form=AsyncMock(side_effect=lambda form: form.to_task(schema.Task, user)),
        update_task=AsyncMock(side_effect=lambda task: schema.Task.model_validate_json(task.model_dump_json())),
    )
    declaration = {
        "name": "Attachments",
        "description": "Only the challenge statement.",
        "author": "author",
        "category": "misc",
        "flag": "test_flag",
        "attachments": [
            {"type": "web", "label": "Website", "url": "https://challenge.example.org/"},
            {"type": "endpoint", "label": "TCP", "host": "::1", "port": 31337},
        ],
    }
    (tmp_path / "task.yaml").write_text(json.dumps(declaration))
    cache = {}

    def run() -> "Task | None":
        return asyncio.run(
            tasks._upload_task(y=api, state=tasks.State(), tasks_cache=cache, task_src=tmp_path),  # noqa: SLF001
        )

    return SimpleNamespace(run=run, api=api, objects=objects, schema=schema, tasks=tasks)


@pytest.mark.parametrize("names", [[], ["empty.bin"], ["z.txt", "a #?%.txt"]])
def test_public_files_become_attachments(upload: SimpleNamespace, tmp_path: Path, names: list[str]):
    public = tmp_path / "public"
    public.mkdir()
    for name in names:
        (public / name).write_bytes(b"" if name == "empty.bin" else name.encode())

    task = upload.run()
    assert task.description == "Only the challenge statement."
    assert [a.type for a in task.attachments] == ["web", "endpoint", *["file" for _ in names]]
    files = task.attachments[2:]
    assert [a.name for a in files] == sorted(names)
    for attachment in files:
        content = upload.objects[upload.tasks.s3_settings.STATIC_BUCKET_NAME, f"{task.task_id}/{attachment.name}"][0]
        assert attachment.size_bytes == len(content)
        assert attachment.sha256 == hashlib.sha256(content).hexdigest()
        assert str(attachment.url).startswith(f"https://files.example.org/shared/{task.task_id}/")
        assert attachment.url.fragment is None
        assert attachment.url.query is None
    if "a #?%.txt" in names:
        assert str(files[0].url).endswith("/a%20%23%3F%25.txt")
    assert len(upload.objects) == len(names)  # No separate .sha256 object.

    # All variants survive the public API projection too.
    public_task = upload.schema.Task.public_model.model_validate_json(task.model_dump_json())
    assert public_task.attachments == task.attachments
    created_form = upload.api.create_task_full_form.call_args.args[0]
    assert (
        created_form.to_task(upload.schema.Task, upload.schema.User.model_construct()).attachments
        == task.attachments[:2]
    )

    # Re-uploading cached objects neither duplicates attachments nor uploads again.
    count = upload.api.s3.put_object.await_count
    assert upload.run().attachments == task.attachments
    assert upload.api.s3.put_object.await_count == count


@pytest.mark.parametrize("paths", [["a.txt", "b.txt", "c.txt"], ["nested/a.txt"]])
def test_archive_metadata_matches_download(upload: SimpleNamespace, tmp_path: Path, paths: list[str]):
    for name in paths:
        path = tmp_path / "public" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())

    task = upload.run()
    assert [a.type for a in task.attachments] == ["web", "endpoint", "file"]
    archive = task.attachments[-1]
    assert archive.name == "files.tar.gz"
    content = upload.objects[upload.tasks.s3_settings.STATIC_BUCKET_NAME, f"{task.task_id}/files.tar.gz"][0]
    assert archive.size_bytes == len(content)
    assert archive.sha256 == hashlib.sha256(content).hexdigest()
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
        assert sorted(member.name for member in tar if member.isfile()) == sorted(paths)
    assert task.description == "Only the challenge statement."
    assert len(upload.objects) == 1
    assert upload.run().attachments == task.attachments
    assert upload.api.s3.put_object.await_count == 1


@pytest.mark.parametrize("keep_directory", [False, True])
def test_removed_files_clear_old_attachments(upload: SimpleNamespace, tmp_path: Path, *, keep_directory: bool):
    public = tmp_path / "public"
    public.mkdir()
    file = public / "old.txt"
    file.write_text("old")
    assert [a.type for a in upload.run().attachments] == ["web", "endpoint", "file"]
    file.unlink()
    if not keep_directory:
        public.rmdir()
    assert [a.type for a in upload.run().attachments] == ["web", "endpoint"]


def test_upload_failure_does_not_publish_task(upload: SimpleNamespace, tmp_path: Path):
    upload.run()
    upload.api.update_task.reset_mock()
    public = tmp_path / "public"
    public.mkdir()
    (public / "file.txt").write_text("data")
    upload.api.s3.put_object.side_effect = RuntimeError("upload failed")
    with pytest.raises(RuntimeError, match="upload failed"):
        upload.run()
    upload.api.update_task.assert_not_awaited()


def test_invalid_declared_attachment_is_rejected(upload: SimpleNamespace, tmp_path: Path):
    path = tmp_path / "task.yaml"
    declaration = json.loads(path.read_text())
    declaration["attachments"][1]["port"] = 65536
    path.write_text(json.dumps(declaration))
    with pytest.raises(ValidationError, match="port"):
        upload.tasks.FileTask.load_yaml(path)
    assert upload.run() is None
    upload.api.create_task_full_form.assert_not_awaited()
    upload.api.update_task.assert_not_awaited()


def test_missing_archive_size_does_not_publish_task(upload: SimpleNamespace, tmp_path: Path):
    public = tmp_path / "public" / "nested"
    public.mkdir(parents=True)
    (public / "file.txt").write_text("data")
    upload.api.s3.stat_object.side_effect = None
    upload.api.s3.stat_object.return_value = SimpleNamespace(size=None, metadata={})
    with pytest.raises(ValueError, match="S3 did not return a size"):
        upload.run()
    upload.api.update_task.assert_not_awaited()
