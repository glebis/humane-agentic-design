# Make `from dtokens import …` work no matter where pytest is invoked from.
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
