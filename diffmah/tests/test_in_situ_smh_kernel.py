"""
"""
import pytest
import numpy as np
from astropy.cosmology import Planck15
from collections import OrderedDict
from ..in_situ_smh_kernel import _get_model_param_dictionaries
from ..in_situ_smh_kernel import in_situ_mstar_at_zobs
from ..sigmoid_mah import DEFAULT_MAH_PARAMS, _median_mah_sigmoid_params
from ..sigmoid_mah import _logtc_from_mah_percentile
from ..moster17_efficiency import DEFAULT_PARAMS as DEFAULT_SFR_PARAMS
from ..quenching_times import DEFAULT_PARAMS as DEFAULT_QTIME_PARAMS


def test_get_model_param_dictionaries():
    defaults = [OrderedDict(a=1, b=2), OrderedDict(c=3, d=4)]
    new_vals = OrderedDict(a=2)
    result = _get_model_param_dictionaries(*defaults, **new_vals)
    correct = [OrderedDict(a=2, b=2), OrderedDict(c=3, d=4)]
    assert np.all([x == y for x, y in zip(result, correct)])


def test2_get_model_param_dictionaries():
    defaults = [OrderedDict(a=1, b=2), OrderedDict(c=3, d=4)]
    new_vals = OrderedDict(c=4)
    result = _get_model_param_dictionaries(*defaults, **new_vals)
    correct = [OrderedDict(a=1, b=2), OrderedDict(c=4, d=4)]
    assert np.all([x == y for x, y in zip(result, correct)])


def test3_get_model_param_dictionaries():
    defaults = [OrderedDict(a=1, b=2), OrderedDict(c=3, d=4)]
    new_vals = OrderedDict(e=5)
    with pytest.raises(KeyError):
        _get_model_param_dictionaries(*defaults, **new_vals)


def test4_get_model_param_dictionaries():
    defaults = [OrderedDict(a=1, b=2), OrderedDict(a=3, d=4)]
    new_vals = OrderedDict(d=5)
    with pytest.raises(KeyError):
        _get_model_param_dictionaries(*defaults, **new_vals)


def test1_in_situ_stellar_mass_at_zobs_is_monotonic_in_mass():
    for z in (0, 1, 2, 5):
        mstar_ms10, mstar_q10 = in_situ_mstar_at_zobs(z, 10)
        mstar_ms12, mstar_q12 = in_situ_mstar_at_zobs(z, 12)
        mstar_ms14, mstar_q14 = in_situ_mstar_at_zobs(z, 14)
        assert mstar_ms10 < mstar_ms12 < mstar_ms14
        assert mstar_q10 < mstar_q12 < mstar_q14


def test2_in_situ_stellar_mass_at_zobs_is_monotonic_in_mass():
    logmarr = np.linspace(8, 17, 20)

    for z in (0, 1, 2, 5):
        mstar_ms_last, __ = in_situ_mstar_at_zobs(z, logmarr[0])
        for logm in logmarr[1:]:
            mstar_ms, mstar_q = in_situ_mstar_at_zobs(z, logm)
            assert mstar_ms >= mstar_q
            assert mstar_ms > mstar_ms_last
            mstar_ms_last = mstar_ms


def test_in_situ_stellar_mass_at_zobs_scales_correctly_with_mah_percentile():
    """Earlier-forming halos have greater M* today."""
    zobs = 0
    mstar_ms_1, __ = in_situ_mstar_at_zobs(zobs, 12, mah_percentile=0)
    mstar_ms_2, __ = in_situ_mstar_at_zobs(zobs, 12)
    mstar_ms_3, __ = in_situ_mstar_at_zobs(zobs, 12, mah_percentile=1)
    assert mstar_ms_1 > mstar_ms_2 > mstar_ms_3


def test_in_situ_stellar_mass_at_zobs_scales_correctly_with_logtc():
    """Earlier-forming halos have greater M* today."""
    zobs = 0
    mstar_ms_1, __ = in_situ_mstar_at_zobs(zobs, 12, logtc=-0.5)
    mstar_ms_2, __ = in_situ_mstar_at_zobs(zobs, 12, logtc=0)
    mstar_ms_3, __ = in_situ_mstar_at_zobs(zobs, 12, logtc=0.5)
    assert mstar_ms_1 > mstar_ms_2 > mstar_ms_3


def test_in_situ_mstar_at_zobs_catches_bad_mah_percentile_inputs():
    zobs, logm0 = 0, 12
    with pytest.raises(ValueError):
        in_situ_mstar_at_zobs(zobs, logm0, mah_percentile=1, logtc=1)


def test_in_situ_mstar_at_zobs_sensible_quenching_behavior():
    logmarr = np.linspace(8, 17, 20)
    for z in (0, 1, 2, 5):
        for logm in logmarr:
            mstar_ms, mstar_q = in_situ_mstar_at_zobs(z, logm)
            assert mstar_ms >= mstar_q


def test_in_situ_mstar_at_zobs_sensible_qtime_behavior():
    """When qtime > today, quenching should not change present-day M*."""
    zobs, logm0 = 0, 12
    tobs = 13.8
    mstar_ms, mstar_q = in_situ_mstar_at_zobs(zobs, logm0, qtime=tobs + 1)
    assert mstar_q > mstar_ms * 0.9


def test2_in_situ_mstar_at_zobs_sensible_qtime_behavior():
    """When qtime << today, quenching should change present-day M*."""
    zobs, logm0 = 0, 12
    mstar_ms, mstar_q = in_situ_mstar_at_zobs(zobs, logm0, qtime=5)
    assert mstar_q < mstar_ms * 0.9


def test3_in_situ_mstar_at_zobs_sensible_qtime_behavior():
    """When qtime > tobs, quenching should not change M*(tobs)."""
    zobs, logm0 = 1, 12
    tobs = Planck15.age(zobs).value  # roughly 5.9 Gyr
    mstar_ms, mstar_q = in_situ_mstar_at_zobs(zobs, logm0, qtime=tobs + 2)
    assert mstar_q > mstar_ms * 0.9


def test4_in_situ_mstar_at_zobs_sensible_qtime_behavior():
    """When qtime < tobs, quenching should significantly reduce M*(tobs)."""
    zobs, logm0 = 1, 12
    tobs = Planck15.age(zobs).value  # roughly 5.9 Gyr
    mstar_ms, mstar_q = in_situ_mstar_at_zobs(zobs, logm0, qtime=tobs - 1)
    assert mstar_q < mstar_ms * 0.9


def test5_in_situ_mstar_at_zobs_sensible_qtime_behavior():
    """When qtime < tobs, quenching should significantly reduce M*(tobs)."""
    zobs = 0
    logmarr = np.linspace(10, 15, 10)
    _fid = [in_situ_mstar_at_zobs(zobs, logm, qtime=20) for logm in logmarr]
    mstar_ms = [_x[0] for _x in _fid]
    mstar_q = [_x[1] for _x in _fid]
    assert np.allclose(mstar_q, mstar_ms, rtol=0.01)


def test_in_situ_mstar_at_zobs_varies_with_MAH_params():
    """Present-day Mstar should change when each MAH param is varied."""
    logm0 = 12
    for zobs in (0, 1, 2):
        mstar_ms_fid, mstar_q_fid = in_situ_mstar_at_zobs(zobs, logm0)
        mah_params_to_vary = {
            key: value
            for key, value in DEFAULT_MAH_PARAMS.items()
            if "scatter" not in key
        }
        for key, value in mah_params_to_vary.items():
            mstar_ms_alt, mstar_q_alt = in_situ_mstar_at_zobs(
                zobs, logm0, **{key: value * 0.9 - 0.1}
            )
            pat = "parameter '{0}' has no effect on {1}"
            assert mstar_ms_alt != mstar_ms_fid, pat.format(key, "mstar_ms")
            assert mstar_q_alt != mstar_q_fid, pat.format(key, "mstar_q")


def test_in_situ_mstar_at_zobs_varies_with_SFR_efficiency_params():
    """Present-day Mstar should change when each model param is varied."""
    logm0 = 12
    for zobs in (0, 1, 2):
        mstar_ms_fid, mstar_q_fid = in_situ_mstar_at_zobs(zobs, logm0)
        for key, value in DEFAULT_SFR_PARAMS.items():
            mstar_ms_alt, mstar_q_alt = in_situ_mstar_at_zobs(
                zobs, logm0, **{key: value * 0.9 - 0.1}
            )
            pat = "parameter '{0}' has no effect on {1}"
            assert mstar_ms_alt != mstar_ms_fid, pat.format(key, "mstar_ms")
            assert mstar_q_alt != mstar_q_fid, pat.format(key, "mstar_q")


def test_in_situ_mstar_at_zobs_varies_with_qtime_params():
    """Present-day Mstar should change when each model param is varied."""
    logm0 = 13
    for zobs in (0, 1, 2):
        mstar_ms_fid, mstar_q_fid = in_situ_mstar_at_zobs(zobs, logm0)
        params_to_vary = {
            key: value
            for key, value in DEFAULT_QTIME_PARAMS.items()
            if "scatter" not in key
        }
        for key, value in params_to_vary.items():
            mstar_ms_alt, mstar_q_alt = in_situ_mstar_at_zobs(
                zobs, logm0, **{key: value * 0.9 - 0.1}
            )
            pat = "parameter '{0}' has an effect on {1}, which should not be so"
            pat2 = "parameter '{0}' has no effect on {1}"
            assert mstar_ms_alt == mstar_ms_fid, pat.format(key, "mstar_ms")
            assert mstar_q_alt != mstar_q_fid, pat2.format(key, "mstar_q")


def test_in_situ_mstar_at_zobs_return_mah_feature():
    zobs = 0
    for logm0 in [10, 11, 12, 13, 14, 15]:
        mstar_ms_fid, mstar_q_fid = in_situ_mstar_at_zobs(zobs, logm0)
        mstar_ms_fid2, mstar_q_fid2, mah = in_situ_mstar_at_zobs(
            zobs, logm0, return_mah=True
        )
        assert np.allclose(mstar_ms_fid, mstar_ms_fid2)
        assert np.allclose(mstar_q_fid, mstar_q_fid2)
        assert np.allclose(mah[-1], 10 ** logm0, rtol=0.001)
        assert np.all(np.diff(mah) > 0)


def test2_in_situ_mstar_at_zobs_return_mah_feature():
    zobs, logm0 = 0, 12

    mstar_ms_fid, mstar_q_fid, mah_fid = in_situ_mstar_at_zobs(
        zobs, logm0, return_mah=True
    )

    mah_params_to_vary = {
        key: value for key, value in DEFAULT_MAH_PARAMS.items() if "scatter" not in key
    }

    for key, default_value in mah_params_to_vary.items():
        mstar_ms_alt, mstar_q_alt, mah_alt = in_situ_mstar_at_zobs(
            zobs, logm0, **{key: 0.9 * default_value - 0.1}, return_mah=True
        )
        assert not np.allclose(mah_alt, mah_fid, rtol=1e-3)


def test1_in_situ_mstar_at_zobs_correctly_infers_mah_percentile_from_logtc():
    """
    """
    mah_params = dict()
    zobs, logm0 = 0, 12
    logtc_med, logtk_med, dlogm_height_med = _median_mah_sigmoid_params(
        logm0, **mah_params
    )
    mstar_ms1, __, mah1 = in_situ_mstar_at_zobs(
        zobs, logm0, return_mah=True, logtc=logtc_med
    )
    mstar_ms2, __, mah2 = in_situ_mstar_at_zobs(
        zobs, logm0, return_mah=True, mah_percentile=0.5
    )
    assert np.allclose(mstar_ms1, mstar_ms2)
    assert np.allclose(mah1, mah2)


def test2_in_situ_mstar_at_zobs_correctly_infers_mah_percentile_from_logtc():
    """
    """
    zobs, logm0 = 0, 12
    mah_params = dict()
    mah_percentile = 0.25

    logtc = _logtc_from_mah_percentile(logm0, mah_percentile, **mah_params)

    mstar_ms1, __, mah1 = in_situ_mstar_at_zobs(
        zobs, logm0, return_mah=True, logtc=logtc
    )

    mstar_ms2, __, mah2 = in_situ_mstar_at_zobs(
        zobs, logm0, return_mah=True, mah_percentile=mah_percentile
    )

    assert np.allclose(mstar_ms1, mstar_ms2, rtol=1e-3)
    assert np.allclose(mah1, mah2, rtol=1e-3)


def test_self_consistent_logtc_vs_mah_percentile_args():
    """Passing in the median logtc vs. passing in mah_percentile=0.5
    should give identical results.
    """
    zobs, logm0 = 0, 12
    logtc_med, __, __ = _median_mah_sigmoid_params(logm0)
    __, mstar_q0 = in_situ_mstar_at_zobs(zobs, logm0, logtc=logtc_med)
    __, mstar_q1 = in_situ_mstar_at_zobs(zobs, logm0, mah_percentile=0.5)
    assert np.allclose(mstar_q0, mstar_q1, rtol=0.001)


def test_in_situ_mstar_at_zobs_logtc_scatter_behavior():
    """Stellar mass should be sensitive to logtc scatter parameters
    """
    zobs, logm0 = 0, 12
    logtc_med, __, __ = _median_mah_sigmoid_params(logm0)

    params = dict(logtc_scatter_dwarfs=0.1)

    mstar_ms1, mstar_q1 = in_situ_mstar_at_zobs(
        zobs, logm0, logtc=logtc_med + 1, **params
    )
    mstar_ms2, mstar_q2 = in_situ_mstar_at_zobs(
        zobs, logm0, logtc=logtc_med - 1, **params
    )
    assert not np.allclose(mstar_ms1 / mstar_q1, mstar_ms2 / mstar_q2, rtol=0.01)


def test2_in_situ_mstar_at_zobs_logtc_scatter_behavior():
    """Stellar mass should not be sensitive to logtc scatter parameters
    for median growth histories
    """
    zobs, logm0 = 0, 12
    logtc_med, __, __ = _median_mah_sigmoid_params(logm0)

    params = dict(logtc_scatter_dwarfs=0.1)
    params2 = dict(logtc_scatter_dwarfs=0.3)
    mstar_ms1, mstar_q1 = in_situ_mstar_at_zobs(
        zobs, logm0, mah_percentile=0.5, **params
    )
    mstar_ms2, mstar_q2 = in_situ_mstar_at_zobs(
        zobs, logm0, mah_percentile=0.5, **params2
    )
    assert np.allclose(mstar_ms1, mstar_ms2)
    assert np.allclose(mstar_q1, mstar_q2)

    mstar_ms1, mstar_q1 = in_situ_mstar_at_zobs(
        zobs, logm0, mah_percentile=0.25, **params
    )
    mstar_ms2, mstar_q2 = in_situ_mstar_at_zobs(
        zobs, logm0, mah_percentile=0.25, **params2
    )
    assert not np.allclose(mstar_ms1, mstar_ms2)
    assert not np.allclose(mstar_q1, mstar_q2)

    mstar_ms1, mstar_q1 = in_situ_mstar_at_zobs(
        zobs, logm0, mah_percentile=0.25, **params
    )
    mstar_ms2, mstar_q2 = in_situ_mstar_at_zobs(
        zobs, logm0, mah_percentile=0.75, **params2
    )
    assert not np.allclose(mstar_ms1, mstar_ms2)
    assert not np.allclose(mstar_q1, mstar_q2)
