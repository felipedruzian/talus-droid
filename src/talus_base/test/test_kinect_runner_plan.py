from talus_base.kinect_validation.runner import build_matrix_plan, build_preflight_plan


def test_matrix_plan_has_approved_groups_and_round_counts():
    plan = build_matrix_plan(default_rounds=10, settle_rounds=5)
    assert [(item.group, item.settle_secs, item.rounds) for item in plan] == [
        ("isolated-default", 0, 10),
        ("settle-10s", 10, 5),
        ("settle-30s", 30, 5),
        ("settle-60s", 60, 5),
    ]


def test_preflight_plan_is_single_round_group():
    plan = build_preflight_plan()
    assert len(plan) == 1
    assert plan[0].group == "preflight"
    assert plan[0].rounds == 1
