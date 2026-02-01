"""
Tests for Server Spoofing Guard WASM Component.

These tests validate:
1. WASM component structure and validity
2. Component can be loaded by wasmtime
3. WIT interface compliance

Note: Guard logic is tested in the pure Python version at:
  ../server-spoofing-guard/tests/test_guard.py (14 tests)

Full end-to-end WASM runtime testing requires a host that implements
both WASI Preview 2 and the custom mcp:security-guard/host interface.
The AgentGateway Rust runtime provides this.
"""

import os
import pytest
from pathlib import Path

# Get paths
WASM_DIR = Path(__file__).parent.parent
WASM_FILE = WASM_DIR / "server_spoofing_guard.wasm"
WIT_FILE = WASM_DIR / "wit" / "guard.wit"
APP_FILE = WASM_DIR / "app.py"


class TestWasmStructure:
    """Tests for WASM file structure and validity."""

    def test_wasm_file_exists(self):
        """WASM file should exist after build."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built. Run ./build.sh first")
        assert WASM_FILE.exists()

    def test_wasm_file_has_correct_magic(self):
        """WASM file should have correct magic bytes."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        with open(WASM_FILE, "rb") as f:
            magic = f.read(4)

        # WASM magic: \0asm
        assert magic == b"\x00asm", f"Invalid WASM magic: {magic}"

    def test_wasm_file_reasonable_size(self):
        """WASM file should be reasonable size (10MB - 100MB for Python component)."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        size_mb = WASM_FILE.stat().st_size / (1024 * 1024)
        assert 10 < size_mb < 100, f"Unexpected size: {size_mb:.1f}MB"


class TestWasmLoading:
    """Tests for WASM component loading with wasmtime."""

    @pytest.fixture
    def engine(self):
        """Create wasmtime engine with component model enabled."""
        try:
            from wasmtime import Engine, Config
            config = Config()
            config.wasm_component_model = True
            return Engine(config)
        except ImportError:
            pytest.skip("wasmtime not installed")

    def test_component_loads(self, engine):
        """Component should load successfully."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        from wasmtime.component import Component
        component = Component.from_file(engine, str(WASM_FILE))
        assert component is not None

    def test_component_has_guard_export(self, engine):
        """Component should export the guard interface."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        from wasmtime.component import Component
        component = Component.from_file(engine, str(WASM_FILE))
        comp_type = component.type

        exports = [str(e) for e in comp_type.exports(engine)]
        assert "mcp:security-guard/guard@0.1.0" in exports, f"Exports: {exports}"

    def test_component_imports_host_interface(self, engine):
        """Component should import our custom host interface."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        from wasmtime.component import Component
        component = Component.from_file(engine, str(WASM_FILE))
        comp_type = component.type

        imports = [str(i) for i in comp_type.imports(engine)]
        assert "mcp:security-guard/host@0.1.0" in imports, f"Imports: {imports}"

    def test_component_imports_wasi(self, engine):
        """Component should import WASI interfaces."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        from wasmtime.component import Component
        component = Component.from_file(engine, str(WASM_FILE))
        comp_type = component.type

        imports = [str(i) for i in comp_type.imports(engine)]
        wasi_imports = [i for i in imports if i.startswith("wasi:")]
        assert len(wasi_imports) > 0, "Should have WASI imports"

    def test_component_instantiates_with_wasi(self, engine):
        """Component should instantiate when WASI and host are provided."""
        if not WASM_FILE.exists():
            pytest.skip("WASM file not built")

        from wasmtime import Store
        from wasmtime.component import Component, Linker

        store = Store(engine)
        linker = Linker(engine)
        linker.add_wasip2()

        # Add our custom host interface
        host_instance = linker.root().add_instance("mcp:security-guard/host@0.1.0")
        host_instance.add_func("log", lambda level, msg: None)
        host_instance.add_func("get-time", lambda: 0)
        host_instance.add_func("get-config", lambda key: "")
        del host_instance

        component = Component.from_file(engine, str(WASM_FILE))
        instance = linker.instantiate(store, component)
        assert instance is not None


class TestWitInterface:
    """Tests for WIT interface definition."""

    def test_wit_file_exists(self):
        """WIT interface file should exist."""
        assert WIT_FILE.exists()

    def test_wit_defines_guard_interface(self):
        """WIT should define guard interface with required functions."""
        content = WIT_FILE.read_text()

        assert "interface guard" in content
        assert "evaluate-server-connection" in content
        assert "evaluate-tools-list" in content

    def test_wit_defines_required_types(self):
        """WIT should define all required types."""
        content = WIT_FILE.read_text()

        assert "record tool" in content
        assert "record guard-context" in content
        assert "variant decision" in content
        assert "record deny-reason" in content

    def test_wit_defines_host_interface(self):
        """WIT should define host interface with required functions."""
        content = WIT_FILE.read_text()

        assert "interface host" in content
        assert "log:" in content
        assert "get-time:" in content
        assert "get-config:" in content

    def test_wit_defines_world(self):
        """WIT should define the security-guard world."""
        content = WIT_FILE.read_text()

        assert "world security-guard" in content
        assert "export guard" in content
        assert "import host" in content


class TestBuildArtifacts:
    """Tests for build artifacts and source files."""

    def test_build_script_exists(self):
        """Build script should exist and be executable."""
        build_script = WASM_DIR / "build.sh"
        assert build_script.exists()
        assert os.access(build_script, os.X_OK)

    def test_app_py_exists(self):
        """Main application file should exist."""
        assert APP_FILE.exists()

    def test_app_py_defines_guard_class(self):
        """app.py should define Guard class with required methods."""
        content = APP_FILE.read_text()

        assert "class Guard:" in content
        assert "def evaluate_server_connection" in content
        assert "def evaluate_tools_list" in content

    def test_app_py_implements_detection_algorithms(self):
        """app.py should implement the core detection algorithms."""
        content = APP_FILE.read_text()

        # Levenshtein for typosquat detection
        assert "levenshtein_ratio" in content

        # Homoglyph detection
        assert "homoglyph" in content.lower() or "'0'" in content  # 0 for o

        # Tool fingerprinting
        assert "fingerprint" in content.lower()
        assert "sha256" in content

    def test_gitignore_excludes_generated_files(self):
        """Gitignore should exclude generated files."""
        gitignore = WASM_DIR / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert "wit_world/" in content or "*.wasm" in content
