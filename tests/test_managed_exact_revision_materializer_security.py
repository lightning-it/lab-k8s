"""Security regressions for the protected exact-revision materializer."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts/materialize-exact-revision-review.py"
REVIEW_WORKFLOW = ROOT / ".github/workflows/release-bot-exact-head-review.yml"
RERUN_WORKFLOW = ROOT / ".github/workflows/current-revision-rerun.yml"


def load_materializer() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "materialize_exact_revision_review",
        MATERIALIZER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the exact-revision materializer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExactRevisionMaterializerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_materializer()

    def test_protected_review_dependency_closure_is_installed(self) -> None:
        for path in (MATERIALIZER, REVIEW_WORKFLOW, RERUN_WORKFLOW):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
        review = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        rerun = RERUN_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "actions/workflows/current-revision-rerun.yml/dispatches",
            review,
        )
        self.assertIn("workflow_dispatch:", rerun)
        self.assertIn("rerun-protected-verifier:", rerun)
        self.assertIn(
            "github.ref == format('refs/heads/{0}', "
            "github.event.repository.default_branch)",
            rerun,
        )
        self.assertIn(
            'test "${GITHUB_REF}" = "refs/heads/${EVENT_DEFAULT_BRANCH}"',
            rerun,
        )
        self.assertNotIn(
            "github.ref == format('refs/heads/{0}', "
            "github.event.pull_request.base.ref)",
            rerun,
        )
        self.assertNotIn(
            'test "${GITHUB_REF}" = "refs/heads/${EVENT_PR_BASE_REF}"',
            rerun,
        )

    def test_invalid_runner_temp_does_not_create_review_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root / "review"
            missing_runner_temp = root / "missing-runner-temp"
            with (
                mock.patch.object(self.module, "validate_inputs"),
                mock.patch.dict(
                    os.environ,
                    {"RUNNER_TEMP": str(missing_runner_temp)},
                ),
                self.assertRaisesRegex(
                    self.module.MaterializationError,
                    "RUNNER_TEMP must identify an existing directory",
                ),
            ):
                self.module.materialize(types.SimpleNamespace(), output)
            self.assertFalse(output.exists())

    def test_external_commands_are_bounded(self) -> None:
        with (
            mock.patch.object(
                self.module.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["gh", "api"], 120),
            ),
            self.assertRaisesRegex(
                self.module.MaterializationError,
                "timed out after 120 seconds",
            ),
        ):
            self.module.run(["gh", "api"], environment={})

    def test_diff_reverification_uses_protected_reads(self) -> None:
        source = MATERIALIZER.read_text(encoding="utf-8")
        self.assertNotIn("patch.read_bytes()", source)
        self.assertNotIn('(regenerated / "change.patch").read_bytes()', source)
        self.assertIn('patch, "review diff"', source)
        self.assertIn(
            'regenerated / "change.patch", "regenerated diff"',
            source,
        )

    def test_unfinished_reservation_is_always_failed_closed(self) -> None:
        workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Fail-close an unfinished protected reservation", workflow)
        self.assertIn("always() &&", workflow)
        self.assertIn("steps.dedupe.outputs.check_id != ''", workflow)
        self.assertIn("Protected Exact-Revision Codex review failed closed", workflow)
        self.assertLess(
            workflow.index('echo "check_id=${check_id}"'),
            workflow.index('-f "details_url=${check_url}"'),
        )

    def test_pr_number_is_validated_before_protected_review_work(self) -> None:
        workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
        validation = '[[ "${PR_NUMBER}" =~ ^[1-9][0-9]*$ ]]'
        protected_use = '--pull-request "${PR_NUMBER}"'
        evidence_use = '--argjson pr_number "${PR_NUMBER}"'
        self.assertIn(validation, workflow)
        self.assertIn(protected_use, workflow)
        self.assertIn(evidence_use, workflow)
        self.assertLess(workflow.index(validation), workflow.index(protected_use))
        self.assertLess(workflow.index(validation), workflow.index(evidence_use))

    def test_protected_reader_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / "target"
            target.write_text("{}\n", encoding="utf-8")
            link = Path(temporary).resolve() / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(
                self.module.MaterializationError,
                "unavailable",
            ):
                self.module.protected_asset_bytes(link, "test asset")

    def test_protected_reader_rejects_hardlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / "target"
            target.write_text("protected\n", encoding="utf-8")
            link = Path(temporary).resolve() / "link"
            os.link(target, link)
            with self.assertRaisesRegex(
                self.module.MaterializationError,
                "one regular non-symlink file",
            ):
                self.module.protected_asset_bytes(link, "test asset")

    def test_protected_io_rejects_group_or_world_writable_parent(self) -> None:
        for mode in (0o720, 0o702, 0o722):
            for operation in ("read", "write"):
                with (
                    self.subTest(mode=oct(mode), operation=operation),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    parent = Path(temporary).resolve() / "unsafe-parent"
                    parent.mkdir(mode=0o700)
                    asset = parent / "asset"
                    asset.write_bytes(b"unchanged")
                    parent.chmod(mode)
                    with self.assertRaisesRegex(
                        self.module.MaterializationError,
                        "must not be group- or world-writable",
                    ):
                        if operation == "read":
                            self.module.protected_asset_bytes(asset, "test asset")
                        else:
                            self.module.write_owned_regular_file(
                                asset,
                                b"replacement",
                                "test asset",
                            )
                    self.assertEqual(b"unchanged", asset.read_bytes())

    def test_protected_io_rejects_group_or_world_writable_file(self) -> None:
        for mode in (0o620, 0o602, 0o622):
            for operation in ("read", "write"):
                with (
                    self.subTest(mode=oct(mode), operation=operation),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    asset = Path(temporary).resolve() / "unsafe-asset"
                    asset.write_bytes(b"unchanged")
                    asset.chmod(mode)
                    with self.assertRaisesRegex(
                        self.module.MaterializationError,
                        "must not be group- or world-writable",
                    ):
                        if operation == "read":
                            self.module.protected_asset_bytes(asset, "test asset")
                        else:
                            self.module.write_owned_regular_file(
                                asset,
                                b"replacement",
                                "test asset",
                            )
                    self.assertEqual(b"unchanged", asset.read_bytes())

    def test_protected_writer_rejects_replacement_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / "target"
            target.write_text("unchanged", encoding="utf-8")
            link = Path(temporary).resolve() / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(
                self.module.MaterializationError,
                "cannot be opened safely",
            ):
                self.module.write_owned_regular_file(link, b"replacement", "test")
            self.assertEqual("unchanged", target.read_text(encoding="utf-8"))

    def test_protected_writer_rejects_hardlink_without_truncating_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / "target"
            target.write_text("unchanged", encoding="utf-8")
            link = Path(temporary).resolve() / "link"
            os.link(target, link)
            with self.assertRaisesRegex(
                self.module.MaterializationError,
                "one regular non-symlink file",
            ):
                self.module.write_owned_regular_file(link, b"replacement", "test")
            self.assertEqual("unchanged", target.read_text(encoding="utf-8"))

    def test_protected_writer_overrides_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "asset"
            previous = os.umask(0o777)
            try:
                self.module.write_owned_regular_file(path, b"protected", "test")
            finally:
                os.umask(previous)
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual(b"protected", path.read_bytes())

    def test_ambiguous_close_never_touches_a_reused_descriptor(self) -> None:
        descriptor = os.dup(1)
        replacement_source = os.dup(1)
        real_close = self.module.os.close
        real_close(descriptor)
        os.dup2(replacement_source, descriptor)
        try:
            with (
                mock.patch.object(self.module.os, "close") as close_mock,
                mock.patch.object(self.module.os, "fstat") as fstat_mock,
            ):
                errors = self.module.close_descriptor_after_error(
                    descriptor,
                    "test descriptor",
                    first_error=OSError("simulated ambiguous close failure"),
                )
            close_mock.assert_not_called()
            fstat_mock.assert_not_called()
            self.assertEqual(
                ["test descriptor close failed: simulated ambiguous close failure"],
                errors,
            )
            self.module.os.fstat(descriptor)
        finally:
            real_close(descriptor)
            real_close(replacement_source)

    def test_protected_writer_cleanup_does_not_mask_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protected = Path(temporary).resolve() / "protected"
            protected.write_bytes(b"unchanged")
            with (
                mock.patch.object(
                    self.module.os,
                    "fsync",
                    side_effect=OSError("simulated write failure"),
                ),
                mock.patch.object(
                    self.module.os,
                    "unlink",
                    side_effect=OSError("simulated cleanup failure"),
                ),
                self.assertRaisesRegex(
                    self.module.MaterializationError,
                    "simulated write failure",
                ) as raised,
            ):
                self.module.write_owned_regular_file(
                    protected,
                    b"replacement",
                    "test",
                )
            notes = getattr(raised.exception, "__notes__", ())
            if hasattr(raised.exception, "add_note"):
                self.assertTrue(
                    any("simulated cleanup failure" in note for note in notes)
                )
            self.assertEqual(b"unchanged", protected.read_bytes())

    def test_protected_writer_close_does_not_mask_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protected = Path(temporary).resolve() / "protected"
            protected.write_bytes(b"unchanged")
            opened_parent = self.module.open_owned_parent_directory(
                protected,
                "test",
                "Protected file writing",
            )
            real_close = self.module.os.close
            close_calls = 0

            def close_then_report_failure(descriptor: int) -> None:
                nonlocal close_calls
                close_calls += 1
                real_close(descriptor)
                if close_calls == 2:
                    raise OSError("simulated close failure")

            with (
                mock.patch.object(
                    self.module.os,
                    "fsync",
                    side_effect=OSError("simulated write failure"),
                ),
                mock.patch.object(
                    self.module,
                    "open_owned_parent_directory",
                    return_value=opened_parent,
                ),
                mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=close_then_report_failure,
                ),
                self.assertRaisesRegex(
                    self.module.MaterializationError,
                    "simulated write failure",
                ) as raised,
            ):
                self.module.write_owned_regular_file(
                    protected,
                    b"replacement",
                    "test",
                )
            notes = getattr(raised.exception, "__notes__", ())
            if hasattr(raised.exception, "add_note"):
                self.assertTrue(
                    any("simulated close failure" in note for note in notes)
                )
            self.assertEqual(b"unchanged", protected.read_bytes())

    def test_protected_writer_directory_close_failure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protected = Path(temporary).resolve() / "protected"
            protected.write_bytes(b"unchanged")
            opened_parent = self.module.open_owned_parent_directory(
                protected,
                "test",
                "Protected file writing",
            )
            real_close = self.module.os.close
            close_calls = 0

            def close_then_report_failure(descriptor: int) -> None:
                nonlocal close_calls
                close_calls += 1
                real_close(descriptor)
                if close_calls == 3:
                    raise OSError("simulated directory close failure")

            with (
                mock.patch.object(
                    self.module,
                    "open_owned_parent_directory",
                    return_value=opened_parent,
                ),
                mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=close_then_report_failure,
                ),
                self.assertRaisesRegex(
                    self.module.MaterializationError,
                    "cleanup failed closed",
                ) as raised,
            ):
                self.module.write_owned_regular_file(
                    protected,
                    b"replacement",
                    "test",
                )
            notes = getattr(raised.exception, "__notes__", ())
            if hasattr(raised.exception, "add_note"):
                self.assertTrue(
                    any("simulated directory close failure" in note for note in notes)
                )
            self.assertEqual(b"replacement", protected.read_bytes())

    def test_protected_writer_preserves_existing_close_note_when_fstat_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protected = Path(temporary).resolve() / "protected"
            protected.write_bytes(b"unchanged")
            opened_parent = self.module.open_owned_parent_directory(
                protected,
                "test",
                "Protected file writing",
            )
            real_close = self.module.os.close
            close_attempts: list[int] = []

            def close_then_report_first_failure(descriptor: int) -> None:
                close_attempts.append(descriptor)
                real_close(descriptor)
                if len(close_attempts) == 1:
                    raise OSError("simulated existing close failure")

            with (
                mock.patch.object(
                    self.module,
                    "open_owned_parent_directory",
                    return_value=opened_parent,
                ),
                mock.patch.object(
                    self.module.os,
                    "fstat",
                    side_effect=OSError("simulated fstat failure"),
                ),
                mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=close_then_report_first_failure,
                ),
                self.assertRaisesRegex(
                    self.module.MaterializationError,
                    "simulated fstat failure",
                ) as raised,
            ):
                self.module.write_owned_regular_file(
                    protected,
                    b"replacement",
                    "test",
                )
            notes = getattr(raised.exception, "__notes__", ())
            if hasattr(raised.exception, "add_note"):
                self.assertTrue(
                    any("simulated existing close failure" in note for note in notes)
                )
            self.assertEqual(1, close_attempts.count(close_attempts[0]))
            self.assertEqual(b"unchanged", protected.read_bytes())

    def test_protected_writer_directory_close_does_not_mask_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protected = Path(temporary).resolve() / "protected"
            protected.write_bytes(b"unchanged")
            opened_parent = self.module.open_owned_parent_directory(
                protected,
                "test",
                "Protected file writing",
            )
            real_close = self.module.os.close
            close_calls = 0

            def close_then_report_failure(descriptor: int) -> None:
                nonlocal close_calls
                close_calls += 1
                real_close(descriptor)
                if close_calls == 3:
                    raise OSError("simulated directory close failure")

            with (
                mock.patch.object(
                    self.module.os,
                    "fsync",
                    side_effect=OSError("simulated write failure"),
                ),
                mock.patch.object(
                    self.module,
                    "open_owned_parent_directory",
                    return_value=opened_parent,
                ),
                mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=close_then_report_failure,
                ),
                self.assertRaisesRegex(
                    self.module.MaterializationError,
                    "simulated write failure",
                ) as raised,
            ):
                self.module.write_owned_regular_file(
                    protected,
                    b"replacement",
                    "test",
                )
            notes = getattr(raised.exception, "__notes__", ())
            if hasattr(raised.exception, "add_note"):
                self.assertTrue(
                    any("simulated directory close failure" in note for note in notes)
                )
            self.assertEqual(b"unchanged", protected.read_bytes())

    def test_metadata_binding_rejects_non_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            review = Path(temporary).resolve()
            (review / "review-metadata.json").write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.MaterializationError,
                "must be a JSON object",
            ):
                self.module.bind_assets(review, {})


if __name__ == "__main__":
    unittest.main()
