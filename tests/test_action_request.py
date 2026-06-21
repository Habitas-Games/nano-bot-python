from nanobot.core.action_request import ActionRequest, ActionType


class TestFactoryMethods:
    def test_move_sets_type_and_target(self):
        a = ActionRequest.move((3, 4))
        assert a.action_type == ActionType.MOVE
        assert a.target_position == (3, 4)

    def test_collect_sets_type_and_target(self):
        a = ActionRequest.collect((1, 2))
        assert a.action_type == ActionType.COLLECT
        assert a.target_position == (1, 2)

    def test_transfer_sets_type_and_target(self):
        a = ActionRequest.transfer((5, 6))
        assert a.action_type == ActionType.TRANSFER
        assert a.target_position == (5, 6)

    def test_defend_sets_type_and_target(self):
        a = ActionRequest.defend((7, 8))
        assert a.action_type == ActionType.DEFEND
        assert a.target_position == (7, 8)

    def test_build_sets_type_target_and_bot_type(self):
        a = ActionRequest.build("NanoCollector", (1, 1))
        assert a.action_type == ActionType.BUILD
        assert a.target_position == (1, 1)
        assert a.build_type == "NanoCollector"

    def test_open_ip_sets_type_only(self):
        a = ActionRequest.open_ip()
        assert a.action_type == ActionType.OPEN_IP

    def test_stop_sets_type_only(self):
        a = ActionRequest.stop()
        assert a.action_type == ActionType.STOP

    def test_self_destruct_sets_type_only(self):
        a = ActionRequest.self_destruct()
        assert a.action_type == ActionType.SELF_DESTRUCT


class TestTypeName:
    def test_default_constructed_is_none(self):
        assert ActionRequest().type_name() == "none"

    def test_type_name_matches_each_factory(self):
        assert ActionRequest.move((0, 0)).type_name() == "move"
        assert ActionRequest.collect((0, 0)).type_name() == "collect"
        assert ActionRequest.transfer((0, 0)).type_name() == "transfer"
        assert ActionRequest.defend((0, 0)).type_name() == "defend"
        assert ActionRequest.build("X", (0, 0)).type_name() == "build"
        assert ActionRequest.open_ip().type_name() == "open_ip"
        assert ActionRequest.stop().type_name() == "stop"
        assert ActionRequest.self_destruct().type_name() == "self_destruct"
