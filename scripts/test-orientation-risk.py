import importlib.util
from pathlib import Path
import unittest
s = importlib.util.spec_from_file_location('risk', Path(__file__).with_name('orientation-risk.py'))
r = importlib.util.module_from_spec(s); s.loader.exec_module(r)

def change(old, new, line=10):
    return f'@@ -{line},1 +{line},1 @@\n-{old}\n+{new}\n'

class RiskTests(unittest.TestCase):
    def test_soft_changes_reach_objective_gates(self):
        for path, old, new in [('androidApp/build.gradle.kts','isMinifyEnabled = true','isMinifyEnabled = releaseMinifyEnabled'),('.github/workflows/mobile-release.yml','runs-on: ubuntu-22.04','runs-on: ubuntu-latest'),('gradle/libs.versions.toml','compose = "1.0"','compose = "1.1"'),('features/settings/SettingsScreen.kt','buildIndex()','lazyIndex()'),('features/profiles/Profile.kt','theme = old','theme = new'),('features/player/Artwork.kt','alpha = 1f','alpha = .8f')]:
            self.assertEqual('soft',r.classify(path,change(old,new))['risk'],path)
    def test_actual_contract_changes_block(self):
        for path, old, new in [('Player.kt','requestedOrientation = old','requestedOrientation = new'),('NewOrientation.kt','','val x = SCREEN_ORIENTATION_SENSOR'),('androidApp/build.gradle.kts','applicationId = "com.nuvio.media"','applicationId = "wrong"'),('androidApp/build.gradle.kts','signingConfig = release','signingConfig = debug'),('features/player/Player.kt','LaunchedEffect(contentId)','LaunchedEffect(sourceId)'),('features/updater/AppUpdater.kt','url = "releases/orientation"','url = "releases/upstream"')]:
            self.assertEqual('hard',r.classify(path,change(old,new))['risk'],path)
    def test_hunk_overlap_and_non_overlap(self):
        canonical=change('a','b',20)
        self.assertEqual('soft',r.classify('Settings.kt',change('x','y',3),canonical)['risk'])
        self.assertEqual('hard',r.classify('Settings.kt',change('x','y',20),canonical)['risk'])
    def test_low_and_comment_changes(self):
        for p in ['README.md','app/baseline-prof.txt','composeApp/src/commonMain/composeResources/values/strings.xml','composeApp/src/commonTest/UnrelatedTest.kt']:
            self.assertEqual('low',r.classify(p,change('SCREEN_ORIENTATION_USER','SCREEN_ORIENTATION_SENSOR'))['risk'])
        self.assertEqual('low',r.classify('Player.kt',change('// requestedOrientation old','// requestedOrientation new'))['risk'])
if __name__ == '__main__': unittest.main()
