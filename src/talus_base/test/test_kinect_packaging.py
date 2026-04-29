import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SETUP_PY = PACKAGE_ROOT / "setup.py"


def load_setup_call() -> tuple[str, ast.Call, dict[str, object]]:
    source = SETUP_PY.read_text()
    module = ast.parse(source)
    names: dict[str, object] = {}
    setup_call = None

    for node in module.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant):
                names[node.targets[0].id] = node.value.value
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "setup":
                setup_call = call

    if setup_call is None:
        raise AssertionError("setup() call not found in setup.py")

    return source, setup_call, names


def keyword_value(call: ast.Call, name: str) -> ast.AST:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    raise AssertionError(f"setup() missing '{name}' keyword")


def resolve_string(node: ast.AST, names: dict[str, object]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in names and isinstance(names[node.id], str):
        return names[node.id]
    raise AssertionError(f"unsupported string node: {ast.dump(node)}")


def packages_config_includes_subpackage(packages_node: ast.AST, names: dict[str, object]) -> bool:
    if isinstance(packages_node, (ast.List, ast.Tuple, ast.Set)):
        package_names = {resolve_string(element, names) for element in packages_node.elts}
        return "talus_base.kinect_validation" in package_names

    if isinstance(packages_node, ast.Call) and isinstance(packages_node.func, ast.Name) and packages_node.func.id == "find_packages":
        include_keyword = next((keyword for keyword in packages_node.keywords if keyword.arg == "include"), None)
        if include_keyword is None:
            return True
        include_node = include_keyword.value
        if not isinstance(include_node, (ast.List, ast.Tuple, ast.Set)):
            raise AssertionError("find_packages(include=...) must use a literal collection")
        include_values = {resolve_string(element, names) for element in include_node.elts}
        return any(value in {"talus_base", "talus_base.*", "talus_base.kinect_validation", "talus_base.kinect_validation.*"} for value in include_values)

    return False


def parse_console_scripts(call: ast.Call, names: dict[str, object]) -> dict[str, str]:
    entry_points = keyword_value(call, "entry_points")
    if not isinstance(entry_points, ast.Dict):
        raise AssertionError("entry_points must be a dict literal")

    for key_node, value_node in zip(entry_points.keys, entry_points.values):
        if resolve_string(key_node, names) != "console_scripts":
            continue
        if not isinstance(value_node, (ast.List, ast.Tuple)):
            raise AssertionError("console_scripts must be a list literal")

        scripts: dict[str, str] = {}
        for element in value_node.elts:
            script = resolve_string(element, names)
            name, target = [part.strip() for part in script.split("=", 1)]
            scripts[name] = target
        return scripts

    raise AssertionError("console_scripts entry point group not found")


def test_setup_packages_include_kinect_validation_subpackage():
    _, setup_call, names = load_setup_call()
    packages_node = keyword_value(setup_call, "packages")
    assert packages_config_includes_subpackage(packages_node, names), (
        "setup.py packages must include talus_base.kinect_validation so the Kinect validation CLI modules install with the package"
    )


def test_console_scripts_point_to_kinect_validation_modules_that_exist_in_repo():
    _, setup_call, names = load_setup_call()
    scripts = parse_console_scripts(setup_call, names)

    expected = {
        "talus_kinect_validate": "talus_base.kinect_validation.runner:main",
        "talus_kinect_sample_image": "talus_base.kinect_validation.sampler:main",
    }
    for script_name, target in expected.items():
        assert scripts.get(script_name) == target
        module_name, _, function_name = target.partition(":")
        module_path = PACKAGE_ROOT.joinpath(*module_name.split(".")).with_suffix(".py")
        assert module_path.is_file(), f"module file for {script_name} must exist at {module_path}"
        assert function_name == "main"
