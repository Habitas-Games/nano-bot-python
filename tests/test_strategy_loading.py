"""_load_strategy_instance() loads a participant's .py file via importlib
and picks out its NanoStrategy subclass. A GDScript file structurally
*is* exactly one class, so the Godot original never had to solve "which
class is the strategy" — this ambiguity is specific to Python allowing
multiple classes per file, and is worth covering directly since a wrong
guess here would be silent and very confusing for whoever hits it
(their strategy "doesn't work" for no apparent reason)."""

import textwrap

import pytest

from nanobot.core.simulation_core import _load_strategy_instance


def write_strategy(tmp_path, filename, source):
    path = tmp_path / filename
    path.write_text(textwrap.dedent(source))
    return str(path)


class TestNormalLoading:
    def test_loads_the_single_subclass(self, tmp_path):
        path = write_strategy(tmp_path, "s.py", """
            from nanobot.api.nano_strategy import NanoStrategy
            class MyStrategy(NanoStrategy):
                def choose_injection_point(self, map_info):
                    return (1, 1)
                def what_to_do_next(self, map_info, my_bots):
                    pass
        """)
        instance = _load_strategy_instance(path)
        assert type(instance).__name__ == "MyStrategy"

    def test_empty_path_returns_none(self):
        assert _load_strategy_instance("") is None

    def test_nonexistent_path_returns_none(self):
        assert _load_strategy_instance("/nonexistent/strategy.py") is None


class TestNoSubclassFound:
    def test_file_with_no_nanostrategy_subclass_returns_none(self, tmp_path):
        path = write_strategy(tmp_path, "s.py", """
            def helper():
                pass
        """)
        assert _load_strategy_instance(path) is None

    def test_syntax_error_returns_none_not_raises(self, tmp_path):
        path = write_strategy(tmp_path, "s.py", """
            class Broken(NanoStrategy)
                pass
        """)
        assert _load_strategy_instance(path) is None  # must not propagate the SyntaxError


class TestAmbiguousMultipleSubclasses:
    def test_two_subclasses_in_one_file_is_rejected_not_guessed(self, tmp_path):
        # This is the scenario that exposed the bug: dir(module) returns
        # names in sorted order, not definition order, so picking "the
        # first one found" would silently prefer whichever class name
        # happens to sort first alphabetically regardless of which one the
        # participant actually intends to run.
        path = write_strategy(tmp_path, "s.py", """
            from nanobot.api.nano_strategy import NanoStrategy

            class ZetaStrategy(NanoStrategy):
                def choose_injection_point(self, map_info):
                    return (9, 9)
                def what_to_do_next(self, map_info, my_bots):
                    pass

            class AlphaStrategy(NanoStrategy):
                def choose_injection_point(self, map_info):
                    return (1, 1)
                def what_to_do_next(self, map_info, my_bots):
                    pass
        """)
        assert _load_strategy_instance(path) is None

    def test_importing_a_subclass_from_elsewhere_is_not_a_second_candidate(self, tmp_path):
        # dir(module) includes names merely visible via import, not just
        # ones defined in the file — a strategy that imports a shared
        # helper base class (itself a NanoStrategy subclass) must not be
        # treated as ambiguous because of that import.
        write_strategy(tmp_path, "shared_base.py", """
            from nanobot.api.nano_strategy import NanoStrategy
            class SharedBase(NanoStrategy):
                def choose_injection_point(self, map_info):
                    return (0, 0)
                def what_to_do_next(self, map_info, my_bots):
                    pass
        """)
        path = write_strategy(tmp_path, "real_strategy.py", f"""
            import sys
            sys.path.insert(0, {str(tmp_path)!r})
            from shared_base import SharedBase
            from nanobot.api.nano_strategy import NanoStrategy

            class MyRealStrategy(NanoStrategy):
                def choose_injection_point(self, map_info):
                    return (3, 3)
                def what_to_do_next(self, map_info, my_bots):
                    pass
        """)
        instance = _load_strategy_instance(path)
        assert type(instance).__name__ == "MyRealStrategy"
