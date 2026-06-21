"""NanoBotData's __init__ pulls per-type stats out of a plain dict (from
bot_types.json via BotTypeRegistry) — these tests catch the case where a
stat key is renamed in the data file but not in the reader, or vice
versa, since that would fail silently (dict.get with a default) rather
than raising."""

from nanobot.core.nanobot_data import NanoBotData


class TestStatsFromDict:
    def test_hp_and_max_hp_set_from_stats(self):
        bot = NanoBotData(1, 0, "NanoCollector", (0, 0), {"hp": 50})
        assert bot.hp == 50
        assert bot.max_hp == 50

    def test_missing_hp_defaults_to_20(self):
        bot = NanoBotData(1, 0, "Unknown", (0, 0), {})
        assert bot.hp == 20

    def test_stationary_flag_from_stats(self):
        bot = NanoBotData(1, 0, "NanoNeedle", (0, 0), {"stationary": True})
        assert bot.is_stationary is True

    def test_stationary_defaults_to_false(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {})
        assert bot.is_stationary is False

    def test_density_immune_flag_from_stats(self):
        bot = NanoBotData(1, 0, "NanoExplorer", (0, 0), {"density_immune": True})
        assert bot.density_immune is True

    def test_traversal_penalty_from_stats(self):
        bot = NanoBotData(1, 0, "NanoBlocker", (0, 0), {"traversal_penalty": 6})
        assert bot.traversal_penalty == 6

    def test_traversal_penalty_defaults_to_zero(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {})
        assert bot.traversal_penalty == 0

    def test_auto_destruct_turns_sets_countdown(self):
        bot = NanoBotData(1, 0, "NanoWall", (0, 0), {"auto_destruct_turns": 50})
        assert bot.auto_destruct_countdown == 50

    def test_no_auto_destruct_turns_means_disabled(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {})
        assert bot.auto_destruct_countdown == -1

    def test_initial_state_is_alive_with_no_azn(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 20})
        assert bot.is_alive is True
        assert bot.azn_carried == 0
        assert bot.pending_action is None


class TestTakeDamage:
    def test_damage_reduces_hp(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 20})
        bot.take_damage(5)
        assert bot.hp == 15
        assert bot.is_alive is True

    def test_lethal_damage_kills_bot(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 20})
        bot.take_damage(20)
        assert bot.hp == 0
        assert bot.is_alive is False

    def test_overkill_damage_clamps_hp_to_zero_not_negative(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 20})
        bot.take_damage(999)
        assert bot.hp == 0
        assert bot.is_alive is False

    def test_zero_damage_does_not_kill(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 20})
        bot.take_damage(0)
        assert bot.hp == 20
        assert bot.is_alive is True

    def test_damage_after_death_stays_dead_and_hp_stays_zero(self):
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 10})
        bot.take_damage(10)
        bot.take_damage(5)  # already dead — must not go negative or "revive"
        assert bot.hp == 0
        assert bot.is_alive is False


class TestLogDict:
    def test_to_log_dict_has_expected_shape(self):
        bot = NanoBotData(7, 1, "NanoCollector", (3, 4), {"hp": 50})
        d = bot.to_log_dict()
        assert d == {
            "id": 7, "owner": 1, "type": "NanoCollector", "pos": [3, 4],
            "hp": 50, "azn": 0, "alive": True, "action": "none",
        }

    def test_to_log_dict_reflects_pending_action_name(self):
        from nanobot.core.action_request import ActionRequest
        bot = NanoBotData(1, 0, "NanoAI", (0, 0), {"hp": 20})
        bot.pending_action = ActionRequest.move((5, 5))
        assert bot.to_log_dict()["action"] == "move"
