from app.shared.geo import NEIGHBOURS, STATES


def test_borders_are_mutual_and_cover_every_state_with_a_neighbour():
    for state, around in NEIGHBOURS.items():
        assert state not in around
        assert all(state in NEIGHBOURS[n] for n in around), state
    assert set(STATES.values()) - set(NEIGHBOURS) == {"Alaska", "Hawaii"}
    assert NEIGHBOURS["California"] == {"Oregon", "Nevada", "Arizona"}
