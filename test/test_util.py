import mplug.util
import pytest


@pytest.mark.parametrize("os", ["Windows", "Linux", "Darwin"])
@pytest.mark.parametrize("arch,short_arch", [("x86_64", "x64"), ("x86_32", "x32")])
def test_resolve_templates_windows(os, arch, short_arch, mocker):
    mocker.patch("platform.system", return_value=os)
    mocker.patch("platform.machine", return_value=arch)
    os = os.lower()
    tests = {
        "": "",
        "filename": "filename",
        "{{os}}-filename": f"{os}-filename",
        "{{os}}-{{os}}-filename": f"{os}-{os}-filename",
        "{{arch}}-filename": f"{arch}-filename",
        "{{arch-short}}-filename": f"{short_arch}-filename",
        "download/{{arch}}/{{os}}/test-{{os}}-{{arch-short}}-filename": f"download/{arch}/{os}/test-{os}-{short_arch}-filename",
    }
    if os == "windows":
        tests.update(
            {
                "filename.{{shared-lib-ext}}": "filename.dll",
                "filename.{{executable-ext}}": "filename.exe",
                "filename-{{executable-ext}}.{{executable-ext}}": "filename-exe.exe",
                "filename-{{executable-ext}}": "filename-exe",
            }
        )
    else:
        tests.update(
            {
                "filename.{{shared-lib-ext}}": "filename.so",
                "filename.{{executable-ext}}": "filename",
                "filename.{{executable-ext}}.{{executable-ext}}": "filename",
                "filename-{{executable-ext}}": "filename-",
            }
        )
    for test_input, tests_output in tests.items():
        assert mplug.util.resolve_templates(test_input) == tests_output
