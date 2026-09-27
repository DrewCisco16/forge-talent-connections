"""Reference test for the toy importer; runnable with plain python3 so no test runner is needed."""
import importer


def test_rejects_ragged():
    acc, rej = importer.import_rows([["a", "b", "c"], ["a"]], ["x", "y", "z"])
    assert len(acc) == 1 and len(rej) == 1


if __name__ == "__main__":
    test_rejects_ragged()
    print("1 test passed")
