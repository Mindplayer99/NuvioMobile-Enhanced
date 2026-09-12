#!/usr/bin/env python3
"""Exercise release rejection paths without credentials or GitHub mutations."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("release", Path(__file__).with_name("orientation-release.py"))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "build-tools/37.0.0").mkdir(parents=True)
        self.apk = self.root / "candidate.apk"
        self.native_apk()
        self.signer = release.CERT
        self.package = "com.nuvio.media"
        self.dirty = ""
        self.version = "0.4.15"
        self.debuggable = False
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, ANDROID_HOME=str(self.root), GITHUB_REPOSITORY=release.REPO).start()
        patch.object(release, "run", side_effect=self.command).start()

    def native_apk(self, abi="arm64-v8a", full=True):
        with zipfile.ZipFile(self.apk, "w") as archive:
            libraries = ["libmpv.so", "libnuvio_engine.so", "libass.so"]
            if full:
                libraries.append("libquickjs.so")
            for name in libraries:
                archive.writestr(f"lib/{abi}/{name}", b"test native payload")

    def command(self, *args, **kwargs):
        if args[:2] == ("git", "rev-parse"):
            return release.BUILDS["0.4.15"][0]
        if args[:2] == ("git", "status"):
            return self.dirty
        if args[0].endswith("apksigner"):
            return "Signer #1 certificate SHA-256 digest: " + self.signer
        if args[0].endswith("aapt2"):
            return f"package: name='{self.package}' versionCode='120' versionName='{self.version}'\n" + (
                "application-debuggable" if self.debuggable else "")
        self.fail("Unexpected external command")

    def verify(self):
        return release.verify(self.root, "0.4.15", self.apk)

    def test_accepts_expected_identity(self):
        self.assertEqual(self.verify()["signer_sha256"], release.CERT)

    def test_wrong_signer_rejected(self):
        self.signer = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "signer"):
            self.verify()

    def test_wrong_package_rejected(self):
        self.package = "com.nuviodebug.com"
        with self.assertRaisesRegex(RuntimeError, "package"):
            self.verify()

    def test_wrong_version_rejected(self):
        self.version = "0.4.16"
        with self.assertRaisesRegex(RuntimeError, "version"):
            self.verify()

    def test_debuggable_rejected(self):
        self.debuggable = True
        with self.assertRaisesRegex(RuntimeError, "Debuggable"):
            self.verify()

    def test_wrong_abi_rejected(self):
        self.native_apk(abi="x86_64")
        with self.assertRaisesRegex(RuntimeError, "ARM64"):
            self.verify()

    def test_missing_full_library_rejected(self):
        self.native_apk(full=False)
        with self.assertRaisesRegex(RuntimeError, "Full native"):
            self.verify()

    def test_dirty_source_rejected(self):
        self.dirty = " M player.kt"
        with self.assertRaisesRegex(RuntimeError, "modified"):
            self.verify()

    def test_failure_prevents_all_github_mutations(self):
        self.signer = "0" * 64
        with patch.object(release, "api") as github:
            with self.assertRaises(RuntimeError):
                release.publish(self.root, "0.4.15", self.apk)
            github.assert_not_called()

    def test_remote_byte_mismatch_leaves_draft_unpublished(self):
        commit = release.BUILDS['0.4.15'][0]
        name = 'Nuvio-Enhanced-0.4.15-Orientation-Full-arm64-v8a.apk'
        calls = []
        def api(path, *args, **kwargs):
            calls.append((path,args))
            if path.startswith('git/ref'): return {'object':{'type':'commit','sha':commit}}
            if path.startswith('releases/tags'): return {'id':1,'draft':True}
            if path == 'releases/1': return {'id':1,'draft':True,'assets':[{'name':name,'state':'uploaded','size':self.apk.stat().st_size}]}
            self.fail('Unexpected publication mutation')
        original = self.command
        def command(*args, **kwargs):
            if args[:3] == ('gh','release','upload'): return ''
            if args[:3] == ('gh','release','download'):
                (Path(args[-1])/name).write_bytes(b'wrong remote bytes'); return ''
            return original(*args,**kwargs)
        with patch.object(release,'api',side_effect=api), patch.object(release,'run',side_effect=command):
            with self.assertRaisesRegex(RuntimeError,'digest mismatch'): release.publish(self.root,'0.4.15',self.apk)
        self.assertFalse(any('draft=false' in args for _,args in calls))

    def test_existing_source_tag_cannot_be_moved(self):
        with patch.object(release, "api", return_value={"object": {"type": "commit", "sha": "wrong"}}) as github:
            with self.assertRaisesRegex(RuntimeError, "Existing tag"):
                release.publish(self.root, "0.4.15", self.apk)
            self.assertEqual(github.call_count, 1)
            self.assertEqual(github.call_args.args, ("git/ref/tags/0.4.15-orientation",))


if __name__ == "__main__":
    unittest.main()
