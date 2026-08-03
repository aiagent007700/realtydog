"""SEL-002 tests: the pure motivation score + buckets. No DB."""
from app.score.motivation import bucket, score_prospect


def test_buckets():
    assert bucket(60) == "hot"
    assert bucket(59) == "warm"
    assert bucket(30) == "warm"
    assert bucket(29) == "cold"
    assert bucket(0) == "cold"


def test_owner_attribute_signals():
    total, bd = score_prospect(
        absentee=True, out_of_state=False, tenure_years=25, owner_type="estate", signal_types=[]
    )
    assert bd == {"estate_owner": 25, "absentee": 15, "long_tenure": 10}
    assert total == 50  # owner attrs alone (no out-of-state) -> Warm, not Hot


def test_distress_signal_dominates():
    total, bd = score_prospect(
        absentee=False, out_of_state=False, tenure_years=3, owner_type="entity",
        signal_types=["tax_sale"],
    )
    assert total == 40
    assert bd == {"tax_sale": 40}


def test_out_of_state_estate_can_reach_hot():
    total, _ = score_prospect(
        absentee=True, out_of_state=True, tenure_years=30, owner_type="estate", signal_types=[]
    )
    assert total == 60  # estate 25 + absentee 15 + out_of_state 10 + tenure 10
    assert bucket(total) == "hot"


def test_estate_owner_not_double_counted_with_probate():
    total, bd = score_prospect(
        absentee=False, out_of_state=False, tenure_years=1, owner_type="estate",
        signal_types=["probate"],
    )
    assert "estate_owner" not in bd  # probate already captures the estate situation
    assert bd == {"probate": 25}
    assert total == 25


def test_missing_data_contributes_nothing():
    total, bd = score_prospect(
        absentee=None, out_of_state=False, tenure_years=None, owner_type=None, signal_types=None
    )
    assert total == 0
    assert bd == {}
