from app import finance


def test_emi_known_value():
    # Rs 10,00,000 @ 10% for 10 years ~ Rs 13,215/month
    assert abs(finance.emi(1_000_000, 10.0, 10) - 13215) < 5


def test_emi_zero_rate_is_principal_over_months():
    assert finance.emi(1_200_000, 0, 10) == 1_200_000 / 120


def test_max_principal_inverts_emi():
    # Round-trip: principal -> EMI -> principal.
    principal = 2_500_000
    e = finance.emi(principal, 11.0, 8)
    assert abs(finance.max_principal_for_emi(e, 11.0, 8) - principal) < 1.0


def test_max_principal_zero_rate():
    assert finance.max_principal_for_emi(10_000, 0, 10) == 10_000 * 120


def test_max_principal_nonpositive_emi_is_zero():
    assert finance.max_principal_for_emi(0, 11.0, 8) == 0
    assert finance.max_principal_for_emi(-5, 11.0, 8) == 0
