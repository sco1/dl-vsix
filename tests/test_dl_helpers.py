from dl_vsix.dl import Extension


def test_extension_roundtrip() -> None:
    sample_id = "ms-python.python"
    ext = Extension.from_id(sample_id)

    assert Extension.from_id(str(ext)) == ext


def test_extension_query_build_default_latest() -> None:
    sample_id = "ms-python.python"
    truth_query = "https://ms-python.gallery.vsassets.io/_apis/public/gallery/publisher/ms-python/extension/python/latest/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"

    ext = Extension.from_id(sample_id)
    assert ext.vsix_query() == truth_query


def test_extension_query_build_with_ver() -> None:
    sample_id = "ms-python.python"
    truth_query = "https://ms-python.gallery.vsassets.io/_apis/public/gallery/publisher/ms-python/extension/python/1.0.0/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"

    ext = Extension.from_id(sample_id)
    assert ext.vsix_query(version="1.0.0") == truth_query
