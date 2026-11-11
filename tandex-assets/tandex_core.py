import io
import json
import os
import uuid
import numpy as np
import pandas as pd
import tandex_func_02

_TEMP_UPLOADS = {
    'eqe': {},
    'trans': {}
}

# Constants
k = 1.380649e-23  # Boltzmann constant in J/K
q = 1.60217662e-19  # Electron charge in C
c = 3e8  # m/s
hc = 1240  # eV*nm


def _trapz(y, x):
    if hasattr(np, 'trapz'):
        return np.trapz(y, x)
    return np.trapezoid(y, x)


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if text in ('0', 'false', 'no', 'n', 'off', ''):
        return False
    return default


def _load_am15g(lambda_start=250, lambda_stop=1450, lambda_step=5):
    spectrum_path = os.path.join(os.path.dirname(__file__), 'data', 'AM15g_spectrum.npz')
    data = np.load(spectrum_path)
    lambda_vec = np.arange(lambda_start, lambda_stop + lambda_step, lambda_step, float)
    am15g = np.interp(lambda_vec, data['LambdaVar'], data['AM15gFlux'])
    return lambda_vec, am15g


def _load_pvk_nk_source(pvk_dataset=None):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    library_dir = os.path.join(data_dir, 'pvk_library')

    if pvk_dataset:
        safe_name = os.path.basename(pvk_dataset)
        candidate = os.path.join(library_dir, safe_name)
        if os.path.exists(candidate):
            return pd.read_csv(candidate)

    pvk_path = os.path.join(data_dir, 'CsFaPbIB_1,72_Tejada2018.csv')
    return pd.read_csv(pvk_path)


def _list_pvk_datasets():
    library_dir = os.path.join(os.path.dirname(__file__), 'data', 'pvk_library')
    if not os.path.isdir(library_dir):
        return []
    return sorted([f for f in os.listdir(library_dir) if f.lower().endswith('.csv')])


def _list_pvk_eqe_datasets():
    library_dir = os.path.join(os.path.dirname(__file__), 'data', 'pvk_library', 'eqe')
    if not os.path.isdir(library_dir):
        return []
    return sorted([f for f in os.listdir(library_dir) if f.lower().endswith('.csv')])


def _list_pvk_tx_datasets():
    library_dir = os.path.join(os.path.dirname(__file__), 'data', 'pvk_library', 'trans')
    if not os.path.isdir(library_dir):
        return []
    return sorted([f for f in os.listdir(library_dir) if f.lower().endswith('.csv')])


def _load_eqe_dataset(name):
    if not name:
        return None
    library_dir = os.path.join(os.path.dirname(__file__), 'data', 'pvk_library', 'eqe')
    path = os.path.join(library_dir, os.path.basename(name))
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    return _extract_eqe_arrays(df)


def _extract_eqe_arrays(df):
    cols = {c.lower(): c for c in df.columns}
    wl_col = cols.get('lambda_nm') or cols.get('lambda') or cols.get('wavelength') or cols.get('lambda_k') or cols.get('wl')
    eqe_col = cols.get('eqe') or cols.get('qe') or cols.get('eqe_pvk')
    if not wl_col or not eqe_col:
        raise ValueError('EQE 数据列名需包含 lambda 和 eqe')
    return df[wl_col].to_numpy(dtype=float), df[eqe_col].to_numpy(dtype=float)


def _load_tx_dataset(name):
    if not name:
        return None
    library_dir = os.path.join(os.path.dirname(__file__), 'data', 'pvk_library', 'trans')
    path = os.path.join(library_dir, os.path.basename(name))
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    return _extract_tx_arrays(df)


def _extract_tx_arrays(df):
    cols = {c.lower(): c for c in df.columns}
    wl_col = cols.get('lambda_nm') or cols.get('lambda') or cols.get('wavelength') or cols.get('lambda_k') or cols.get('wl')
    tx_col = cols.get('trans') or cols.get('tx') or cols.get('transmittance') or cols.get('t')
    if not wl_col or not tx_col:
        raise ValueError('透过率数据列名需包含 lambda 和 trans/tx')
    return df[wl_col].to_numpy(dtype=float), df[tx_col].to_numpy(dtype=float)


def _put_temp_dataset(data_type, filename, arrays):
    token = uuid.uuid4().hex
    _TEMP_UPLOADS[data_type][token] = {
        'filename': filename,
        'arrays': arrays
    }
    return token


def _get_temp_dataset(data_type, token):
    if not token:
        return None
    entry = _TEMP_UPLOADS.get(data_type, {}).get(token)
    if not entry:
        return None
    return entry['arrays']


def _ito_tx_thickness_factor(lambda_vec, tce_thick_cm, ref_thick_cm=40e-7):
    excel_path = os.path.join(os.path.dirname(__file__), 'data', 'Optical_Properties.xlsx')
    df_nk_excel = pd.read_excel(excel_path, header=0, sheet_name=0)
    nk_ito = np.array(tandex_func_02.get_ntotal_from_excel('ITO3', lambda_vec, df_nk_excel))
    k_ito = np.clip(nk_ito.imag, 0, None)
    alpha_ito = (4 * np.pi * k_ito) / (lambda_vec * 1e-7)
    delta_t = float(tce_thick_cm) - float(ref_thick_cm)
    factor = np.exp(-alpha_ito * delta_t)
    return np.clip(factor, 0, 1)


def _interp_pvk_nk(lambda_vec, df_pvk):
    cols = {c.lower(): c for c in df_pvk.columns}
    lambda_n_col = cols.get('lambda_n') or cols.get('lambda') or cols.get('wavelength')
    n_col = cols.get('n')
    lambda_k_col = cols.get('lambda_k') or cols.get('lambda') or cols.get('wavelength')
    k_col = cols.get('k')

    if not lambda_n_col or not n_col or not lambda_k_col or not k_col:
        raise ValueError('钙钛矿 nk 数据需包含 lambda_n/n 与 lambda_k/k 列')

    n_interp = np.interp(lambda_vec, df_pvk[lambda_n_col].to_numpy(dtype=float), df_pvk[n_col].to_numpy(dtype=float))
    k_interp = np.interp(lambda_vec, df_pvk[lambda_k_col].to_numpy(dtype=float), df_pvk[k_col].to_numpy(dtype=float))
    return np.array([complex(n, k) for n, k in zip(n_interp, k_interp)])


def _parse_full_params(data):
    egap_p = float(data.get('EgapP', 1.7))
    pvk_thick = float(data.get('pvk_thick', 850e-7))  # cm
    pvk_eqe_thick_ref = float(data.get('pvk_eqe_thick_ref', pvk_thick))
    si_waf_thick = float(data.get('Si_Waf_thick', 0.019))  # cm
    tce_thick = float(data.get('TCE_thick', 40e-7))  # cm
    tce_top_thick = float(data.get('TCE_top_thick', 40e-7))  # cm
    tce_bottom_thick = float(data.get('TCE_bottom_thick', 40e-7))  # cm
    tce_rho = float(data.get('TCE_rho', 0.42e-3))  # ohm*cm
    tce_top_rsheet = float(data.get('TCE_top_rsheet', 0.0))  # ohm/sq
    tce_bottom_rsheet = float(data.get('TCE_bottom_rsheet', 0.0))  # ohm/sq

    rsh_pvk = float(data.get('Rsh_pvk', 200e3))
    j01d_pvk = float(data.get('J01d_pvk', 8e-24))
    j02_pvk = float(data.get('J02_pvk', 2.1e-13))
    j02_eg_beta = float(data.get('J02_eg_beta', 0.72))
    j0def_pvk = float(data.get('J0def_pvk', 3e-23))
    rdef_pvk = float(data.get('Rdef_pvk', 12))

    rsh_si = float(data.get('Rsh_Si', 50e3))
    ni = float(data.get('ni', 9.65e9))
    n_def = float(data.get('n_def', 1))
    j0n_si = float(data.get('J0n_Si', 2e-15))

    w = float(data.get('w', 0.2))
    d = float(data.get('d', 20e-4))
    l_min = float(data.get('l_min', 0.02))
    l_max = float(data.get('l_max', 0.8))
    l_points = int(data.get('l_points', 100))

    v_min = float(data.get('v_min', -0.05))
    v_max = float(data.get('v_max', 2.2))
    v_points = int(data.get('v_points', 100))

    lambda_start = float(data.get('lambda_start', 250))
    lambda_stop = float(data.get('lambda_stop', 1450))
    lambda_step = float(data.get('lambda_step', 5))
    x_step = float(data.get('x_step', 1))

    rser_int = float(data.get('RserInt', 1.5 + 4.7e-3))
    include_rser = _parse_bool(data.get('include_rser'), True)

    return {
        'EgapP': egap_p,
        'pvk_thick': pvk_thick,
        'pvk_eqe_thick_ref': pvk_eqe_thick_ref,
        'Si_Waf_thick': si_waf_thick,
        'TCE_thick': tce_thick,
        'TCE_top_thick': tce_top_thick,
        'TCE_bottom_thick': tce_bottom_thick,
        'TCE_rho': tce_rho,
        'TCE_top_rsheet': tce_top_rsheet,
        'TCE_bottom_rsheet': tce_bottom_rsheet,
        'Rsh_pvk': rsh_pvk,
        'J01d_pvk': j01d_pvk,
        'J02_pvk': j02_pvk,
        'J02_eg_beta': j02_eg_beta,
        'J0def_pvk': j0def_pvk,
        'Rdef_pvk': rdef_pvk,
        'Rsh_Si': rsh_si,
        'ni': ni,
        'n_def': n_def,
        'J0n_Si': j0n_si,
        'w': w,
        'd': d,
        'l_min': l_min,
        'l_max': l_max,
        'l_points': l_points,
        'v_min': v_min,
        'v_max': v_max,
        'v_points': v_points,
        'lambda_start': lambda_start,
        'lambda_stop': lambda_stop,
        'lambda_step': lambda_step,
        'x_step': x_step,
        'RserInt': rser_int,
        'include_rser': include_rser,
        'pvk_dataset': data.get('pvk_dataset') or None,
        'pvk_eqe_dataset': data.get('pvk_eqe_dataset') or None,
        'pvk_eqe_token': data.get('pvk_eqe_token') or None,
        'pvk_tx_dataset': data.get('pvk_tx_dataset') or None,
        'pvk_tx_top_dataset': data.get('pvk_tx_top_dataset') or None,
        'pvk_tx_mid_dataset': data.get('pvk_tx_mid_dataset') or None,
        'pvk_tx_bottom_dataset': data.get('pvk_tx_bottom_dataset') or None,
        'pvk_tx_token': data.get('pvk_tx_token') or None,
        'pvk_tx_top_token': data.get('pvk_tx_top_token') or None,
        'pvk_tx_mid_token': data.get('pvk_tx_mid_token') or None,
        'pvk_tx_bottom_token': data.get('pvk_tx_bottom_token') or None,
    }


def _tandem_core(params):
    lambda_vec, am15g = _load_am15g(params['lambda_start'], params['lambda_stop'], params['lambda_step'])
    df_pvk0 = _load_pvk_nk_source(params.get('pvk_dataset'))

    T = 300
    Vt = (k * T) / q
    bb300k = (2 * np.pi * c / ((lambda_vec * 1e-9) * lambda_vec * (lambda_vec * 1e-7) ** 2)) * \
             (1.0 / (np.exp(hc / (lambda_vec * Vt)) - 1))

    layers = ['Air', 'MgF2_1', 'ITO3', 'SnO2_1', 'C60_1', 'CsFaPbIB_1,72', 'ITO3', 'Si_']
    thicknesses = np.array([0, 115, params['TCE_thick'] * 1e7, 20, 10, params['pvk_thick'] * 1e7, 2, 5000])
    pvk_layer_id = 5
    front_layers = np.arange(0, 6)

    r_tco_mid = params['TCE_rho'] / params['TCE_thick']
    r_tco_effective = (params['TCE_top_rsheet'] + r_tco_mid + params['TCE_bottom_rsheet']) if params.get('include_rser') else 0.0
    c_aug = 2.945e-30
    j0aug_si = q * c_aug * params['ni']**3 * params['Si_Waf_thick']

    # PVK 非辐射暗电流随带隙变化：默认参数以 ~1.72 eV 体系为参考，
    # 宽带隙时若不缩放会显著低估 Voc。
    eg_ref = 1.72
    delta_eg = float(params['EgapP']) - eg_ref
    exp_n1 = np.exp(np.clip(-delta_eg / Vt, -120, 120))
    # n=2 支路在宽带隙下仍可能主导 Voc 损失；
    # 通过 beta (>1) 增强其随 Eg 的衰减，默认 1.3 用于匹配高 Eg 体系。
    j02_eg_beta = max(float(params.get('J02_eg_beta', 0.72)), 0.1)
    exp_n2 = np.exp(np.clip(-j02_eg_beta * delta_eg / (2 * Vt), -120, 120))
    j01d_pvk_eff = params['J01d_pvk'] * exp_n1
    j0def_pvk_eff = params['J0def_pvk'] * exp_n1
    j02_pvk_eff = params['J02_pvk'] * exp_n2

    top_cell_density = np.array([0, params['Rsh_pvk'], j01d_pvk_eff, j0def_pvk_eff, params['Rdef_pvk'], j02_pvk_eff])
    bottom_cell_density = np.array([0, params['Rsh_Si'], 0, j0aug_si, params['J0n_Si'], params['n_def']])

    l_values = np.linspace(params['l_min'], params['l_max'], params['l_points'])
    vcell = np.linspace(params['v_min'], params['v_max'], params['v_points'])

    eqe_override = _get_temp_dataset('eqe', params.get('pvk_eqe_token'))
    if eqe_override is None:
        eqe_override = _load_eqe_dataset(params.get('pvk_eqe_dataset'))

    tx_top_override = _get_temp_dataset('trans', params.get('pvk_tx_top_token') or params.get('pvk_tx_token'))
    if tx_top_override is None:
        tx_top_override = _load_tx_dataset(params.get('pvk_tx_top_dataset') or params.get('pvk_tx_dataset'))

    tx_mid_override = _get_temp_dataset('trans', params.get('pvk_tx_mid_token') or params.get('pvk_tx_token'))
    if tx_mid_override is None:
        tx_mid_override = _load_tx_dataset(params.get('pvk_tx_mid_dataset'))

    tx_bottom_override = _get_temp_dataset('trans', params.get('pvk_tx_bottom_token') or params.get('pvk_tx_token'))
    if tx_bottom_override is None:
        tx_bottom_override = _load_tx_dataset(params.get('pvk_tx_bottom_dataset'))

    def _interp_tx(tx_data):
        if not tx_data:
            return np.ones_like(lambda_vec)
        wl_tx, tx_vals = tx_data
        return np.clip(np.interp(lambda_vec, wl_tx, tx_vals), 0, 1)

    tx_top = _interp_tx(tx_top_override)
    tx_mid = _interp_tx(tx_mid_override)
    tx_bottom = _interp_tx(tx_bottom_override)

    tx_top_eff = np.clip(tx_top * _ito_tx_thickness_factor(lambda_vec, params['TCE_top_thick'], ref_thick_cm=40e-7), 0, 1)
    tx_mid_eff = np.clip(tx_mid * _ito_tx_thickness_factor(lambda_vec, params['TCE_thick'], ref_thick_cm=40e-7), 0, 1)
    tx_bottom_eff = np.clip(tx_bottom * _ito_tx_thickness_factor(lambda_vec, params['TCE_bottom_thick'], ref_thick_cm=40e-7), 0, 1)
    # 底部透明电极不参与光谱传输，只参与电学（硅侧）路径。
    tx_for_wat = tx_top_eff * tx_mid_eff

    if eqe_override:
        wl_eqe, eqe_vals = eqe_override
        eqe_raw = np.interp(lambda_vec, wl_eqe, eqe_vals)
        eqe_raw = np.clip(eqe_raw, 0, 1)

        # EQE 数据常含长波噪声尾巴；按 Eg 截止可避免 J0 被非物理尾巴抬高。
        lambda_g = hc / max(params['EgapP'], 1e-6)  # nm
        eqe_raw = np.where(lambda_vec <= lambda_g, eqe_raw, 0.0)

        ref_thick = max(params['pvk_eqe_thick_ref'], 1e-12)
        alpha_est = -np.log(np.clip(1 - eqe_raw, 1e-12, 1)) / ref_thick
        eqe_pvk_abs = 1 - np.exp(-alpha_est * params['pvk_thick'])
        eqe_pvk_abs = np.clip(eqe_pvk_abs, 0, 1)

        tx_front = tx_top_eff
        tx_front = np.clip(tx_front, 0, 1)
        tx_to_bottom = np.clip(tx_front * tx_mid_eff, 0, 1)
        tx_for_wat = tx_to_bottom

        # PVK 入射光谱 = AM1.5G × 顶部透明电极透过率
        # Si 入射光谱 = AM1.5G × 顶部 × 中间 × 底部透过率 × (1 - PVK吸收)
        eqe_pvk = np.clip(tx_front * eqe_pvk_abs, 0, 1)
        total_tx = np.clip(tx_to_bottom * (1 - eqe_pvk_abs), 0, 1)
        reflection = np.clip(1 - eqe_pvk - total_tx, 0, 1)

        absorption = np.zeros((len(layers), len(lambda_vec)))
        # 吸收矩阵中的 PVK 吸收保持为吸收层本征吸收，
        # 便于下游 WAT 使用 (1 - PVK吸收) × Tx_front 的定义。
        absorption[pvk_layer_id, :] = eqe_pvk_abs
    else:
        # Optical modeling (TMM)
        excel_path = os.path.join(os.path.dirname(__file__), 'data', 'Optical_Properties.xlsx')
        df_nk_excel = pd.read_excel(excel_path, header=0, sheet_name=0)
        n_k = np.zeros((len(layers), len(lambda_vec)), dtype=complex)
        for i, l in enumerate(layers):
            ni = np.array(tandex_func_02.get_ntotal_from_excel(l, lambda_vec, df_nk_excel))
            n_k[i, :] = ni

        # PVK 层优先使用当前选中的 nk 数据集，而不是固定 Excel 材料条目。
        n_k[pvk_layer_id, :] = _interp_pvk_nk(lambda_vec, df_pvk0)

        df_pvk_tmm = pd.DataFrame(columns=df_pvk0.columns)
        df_pvk_tmm['lambda_k'] = lambda_vec
        df_pvk_tmm['alpha'] = (4 * np.pi * n_k[pvk_layer_id, :].imag) / (lambda_vec * 1e-7)
        lambda_shift = tandex_func_02.get_lambda_shift(params['EgapP'], lambda_vec, df_pvk_tmm)
        int_n = np.interp(lambda_vec, lambda_vec + lambda_shift, n_k[pvk_layer_id, :].real)
        int_k = np.interp(lambda_vec, lambda_vec + lambda_shift, n_k[pvk_layer_id, :].imag)
        n_k[pvk_layer_id, :] = np.array([complex(n, k) for n, k in zip(int_n, int_k)])

        total_tx, absorption, reflection, *_ = tandex_func_02.TMM_Tx_Ax(
            layers, thicknesses, lambda_vec, params['x_step'], front_layers, n_k
        )

        eqe_pvk = absorption[pvk_layer_id, :]

    jsc_pvk = q * _trapz(am15g * eqe_pvk, lambda_vec)
    filtered_am15g = am15g * total_tx
    jsc_si, ax_si = tandex_func_02.Jsc_Si_fun(params['Si_Waf_thick'], lambda_vec, filtered_am15g)
    eqe_si = filtered_am15g * ax_si / am15g

    # 4T 参考：Si 单独在同等入射条件（不含 PVK 吸收损失）下的电流。
    si_alone_am15g = am15g * tx_for_wat
    jsc_si_alone, _ = tandex_func_02.Jsc_Si_fun(params['Si_Waf_thick'], lambda_vec, si_alone_am15g)
    eqe_si_alone = si_alone_am15g * ax_si / am15g

    j0_pvk = q * _trapz(bb300k * eqe_pvk, lambda_vec)
    j0_si = q * _trapz(bb300k * eqe_si, lambda_vec)
    j0_si_alone = q * _trapz(bb300k * eqe_si_alone, lambda_vec)
    voc_pvk_rad = Vt * np.log(max(jsc_pvk, 1e-30) / max(j0_pvk, 1e-60))

    aaf = 1 - params['d'] / l_values
    l_opt, app_voc, app_eff, app_ff, app_jsc = tandex_func_02.find_optimal_pitch(
        j0_si, params['J0n_Si'], j0aug_si, params['Rsh_Si'], jsc_si, l_values, r_tco_effective, aaf
    )

    aaf = 1 - params['d'] / l_opt
    iscpvk = -aaf * params['w'] * (l_opt / 2) * jsc_pvk
    i0_pvk = params['w'] * (l_opt / 2) * j0_pvk
    i01d_pvk = params['w'] * (l_opt / 2) * j01d_pvk_eff

    iscs = -aaf * params['w'] * (l_opt / 2) * jsc_si
    i01_si = params['w'] * (l_opt / 2) * j0_si

    rser = (r_tco_effective * (l_opt**2 / 12) + params['RserInt']) if params.get('include_rser') else 0.0

    top_cell = [
        iscpvk,
        params['Rsh_pvk'] / (params['w'] * (l_opt / 2)),
        i0_pvk + i01d_pvk,
        j0def_pvk_eff * params['w'] * (l_opt / 2),
        params['Rdef_pvk'] / (params['w'] * (l_opt / 2)),
        j02_pvk_eff * params['w'] * (l_opt / 2)
    ]
    bottom_cell = [
        iscs,
        params['Rsh_Si'] / (params['w'] * (l_opt / 2)),
        i01_si,
        j0aug_si * params['w'] * (l_opt / 2),
        params['J0n_Si'] * params['w'] * (l_opt / 2),
        params['n_def']
    ]

    voltages, currents = tandex_func_02.simulate_circuit(top_cell, bottom_cell, rser, params['w'], l_opt, vcell)
    eff, jsc, voc, ff = tandex_func_02.calculate_efficiency(voltages, currents, False)

    mode = '2T' if params.get('include_rser') else '4T'
    component = None
    if mode == '4T':
        def _component_vgrid(voc_est):
            vmin = params['v_min']
            vmax_cfg = params['v_max']
            if np.isfinite(voc_est):
                vmax = min(vmax_cfg, max(0.8, float(voc_est) * 1.25))
            else:
                vmax = min(vmax_cfg, 1.2)
            if vmax <= vmin:
                vmax = vmin + 1.0
            npts = max(80, params['v_points'])
            return np.linspace(vmin, vmax, npts)

        # 4T: 输出 PVK、底层 Si 以及 Si 单独同光照三条单结 JV。
        v_pvk0, j_pvk0 = tandex_func_02.simulate_pvk_sj(top_cell, 0.0, params['w'], l_opt, vcell)
        _, _, voc_pvk0, _ = tandex_func_02.calculate_efficiency(v_pvk0, j_pvk0, False)
        vgrid_pvk = _component_vgrid(voc_pvk0)
        v_pvk, j_pvk = tandex_func_02.simulate_pvk_sj(top_cell, 0.0, params['w'], l_opt, vgrid_pvk)
        eff_pvk, jsc_pvk_sj, voc_pvk, ff_pvk = tandex_func_02.calculate_efficiency(v_pvk, j_pvk, False)

        v_si0, j_si0 = tandex_func_02.simulate_Si_sj(bottom_cell, 0.0, params['w'], l_opt, vcell)
        _, _, voc_si0, _ = tandex_func_02.calculate_efficiency(v_si0, j_si0, False)
        vgrid_si = _component_vgrid(voc_si0)
        v_si, j_si = tandex_func_02.simulate_Si_sj(bottom_cell, 0.0, params['w'], l_opt, vgrid_si)
        eff_si, jsc_si_sj, voc_si, ff_si = tandex_func_02.calculate_efficiency(v_si, j_si, False)

        # Si-alone 使用独立的光生电流与独立最优电极间距。
        aaf_scan = 1 - params['d'] / l_values
        l_opt_alone, *_ = tandex_func_02.find_optimal_pitch(
            j0_si_alone, params['J0n_Si'], j0aug_si, params['Rsh_Si'],
            jsc_si_alone, l_values, 0.0, aaf_scan
        )
        aaf_alone = 1 - params['d'] / l_opt_alone
        i01_si_alone = params['w'] * (l_opt_alone / 2) * j0_si_alone

        bottom_cell_alone = [
            -aaf_alone * params['w'] * (l_opt_alone / 2) * jsc_si_alone,
            params['Rsh_Si'] / (params['w'] * (l_opt_alone / 2)),
            i01_si_alone,
            j0aug_si * params['w'] * (l_opt_alone / 2),
            params['J0n_Si'] * params['w'] * (l_opt_alone / 2),
            params['n_def']
        ]
        v_si_alone0, j_si_alone0 = tandex_func_02.simulate_Si_sj(bottom_cell_alone, 0.0, params['w'], l_opt_alone, vcell)
        _, _, voc_si_alone0, _ = tandex_func_02.calculate_efficiency(v_si_alone0, j_si_alone0, False)
        vgrid_si_alone = _component_vgrid(voc_si_alone0)
        v_si_alone, j_si_alone = tandex_func_02.simulate_Si_sj(bottom_cell_alone, 0.0, params['w'], l_opt_alone, vgrid_si_alone)
        eff_si_alone, jsc_si_alone_sj, voc_si_alone, ff_si_alone = tandex_func_02.calculate_efficiency(v_si_alone, j_si_alone, False)

        component = {
            'pvk': {
                'voltages': v_pvk,
                'currents': j_pvk,
                'eff': eff_pvk,
                'jsc': jsc_pvk_sj,
                'voc': voc_pvk,
                'ff': ff_pvk
            },
            'si_bottom': {
                'voltages': v_si,
                'currents': j_si,
                'eff': eff_si,
                'jsc': jsc_si_sj,
                'voc': voc_si,
                'ff': ff_si
            },
            'si_alone': {
                'voltages': v_si_alone,
                'currents': j_si_alone,
                'eff': eff_si_alone,
                'jsc': jsc_si_alone_sj,
                'voc': voc_si_alone,
                'ff': ff_si_alone,
                'l_opt': l_opt_alone
            }
        }

    return {
        'mode': mode,
        'eff': eff,
        'jsc': jsc,
        'voc': voc,
        'ff': ff,
        'voltages': voltages,
        'currents': currents,
        'l_opt': l_opt,
        'app_voc': app_voc,
        'app_eff': app_eff,
        'app_ff': app_ff,
        'app_jsc': app_jsc,
        'total_tx': total_tx,
        'tx_for_wat': tx_for_wat,
        'tx_top': tx_top_eff,
        'tx_mid': tx_mid_eff,
        'tx_bottom': tx_bottom_eff,
        'jsc_pvk': jsc_pvk,
        'j0_pvk': j0_pvk,
        'voc_pvk_rad': voc_pvk_rad,
        'j01d_pvk_eff': j01d_pvk_eff,
        'j0def_pvk_eff': j0def_pvk_eff,
        'j02_pvk_eff': j02_pvk_eff,
        'absorption': absorption,
        'reflection': reflection,
        'am15g': am15g,
        'pvk_layer_id': pvk_layer_id,
        'component': component
    }


def calc_rs(data):
    try:
        r_sheet = float(data['R_sheet_TCE'])
        l = float(data['l'])
        w = float(data['w'])
        if w == 0:
            return jsonify({'error': 'w 不能为 0'}), 400
        rs = r_sheet * l / (6 * w)
        return jsonify({'rs': rs})
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': '参数无效或缺失'}), 400

def pvk_datasets():
    return jsonify({
        'datasets': _list_pvk_datasets(),
        'default': 'CsFaPbIB_1,72_Tejada2018.csv'
    })

def pvk_eqe_datasets():
    return jsonify({
        'datasets': _list_pvk_eqe_datasets()
    })

def pvk_tx_datasets():
    return jsonify({
        'datasets': _list_pvk_tx_datasets()
    })

def si_lifetime(data):
    try:
        ndop = float(data['Ndop'])
        delta_n = float(data['Delta_n'])
        wafer_t = float(data['waferT'])
        ni = float(data['ni'])
        temp = float(data['Temp'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': '参数无效或缺失'}), 400

    result = tandex_func_02.Si_bulk_lifetime(ndop, delta_n, wafer_t, ni, temp)
    return jsonify({'result': [float(x) for x in result]})

def tandem_full(data):

    try:
        params = _parse_full_params(data)
    except (TypeError, ValueError):
        return jsonify({'error': '参数无效'}), 400

    try:
        result = _tandem_core(params)
        wat_tx = result.get('tx_for_wat')
        if wat_tx is not None:
            pvk_abs_vec = result['absorption'][result['pvk_layer_id'], :]
            wat_vec = np.clip(1 - pvk_abs_vec, 0, 1) * wat_tx
        else:
            wat_vec = result['total_tx']
        wat = float(np.dot(result['am15g'], wat_vec) / np.sum(result['am15g']))
        tx_top_wat = float(np.dot(result['am15g'], result['tx_top']) / np.sum(result['am15g']))
        tx_mid_wat = float(np.dot(result['am15g'], result['tx_mid']) / np.sum(result['am15g']))
        tx_bottom_wat = float(np.dot(result['am15g'], result['tx_bottom']) / np.sum(result['am15g']))
        pvk_abs = float(np.sum(result['am15g'] * result['absorption'][result['pvk_layer_id'], :]) / np.sum(result['am15g']))
        refl = float(np.sum(result['am15g'] * result['reflection']) / np.sum(result['am15g']))

        response = {
            'mode': result['mode'],
            'efficiency': float(result['eff']),
            'Jsc': float(result['jsc']),
            'Voc': float(result['voc']),
            'FF': float(result['ff']),
            'WAT': wat,
            'Tx_top': tx_top_wat,
            'Tx_mid': tx_mid_wat,
            'Tx_bottom': tx_bottom_wat,
            'Absorption_PVK': pvk_abs,
            'Reflection': refl,
            'l_opt': float(result['l_opt']),
            'Jsc_pvk': float(result['jsc_pvk']),
            'J0_pvk': float(result['j0_pvk']),
            'Voc_pvk_rad': float(result['voc_pvk_rad']),
            'J01d_pvk_eff': float(result['j01d_pvk_eff']),
            'J0def_pvk_eff': float(result['j0def_pvk_eff']),
            'J02_pvk_eff': float(result['j02_pvk_eff'])
        }

        if result['mode'] == '4T' and result.get('component'):
            comp = result['component']
            response['pvk'] = {
                'efficiency': float(comp['pvk']['eff']),
                'Jsc': float(comp['pvk']['jsc']),
                'Voc': float(comp['pvk']['voc']),
                'FF': float(comp['pvk']['ff'])
            }
            response['si_bottom'] = {
                'efficiency': float(comp['si_bottom']['eff']),
                'Jsc': float(comp['si_bottom']['jsc']),
                'Voc': float(comp['si_bottom']['voc']),
                'FF': float(comp['si_bottom']['ff'])
            }
            response['si_alone'] = {
                'efficiency': float(comp['si_alone']['eff']),
                'Jsc': float(comp['si_alone']['jsc']),
                'Voc': float(comp['si_alone']['voc']),
                'FF': float(comp['si_alone']['ff'])
            }
            response['efficiency_total'] = float(comp['pvk']['eff'] + comp['si_bottom']['eff'])

        return jsonify(response)
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500
    except Exception as exc:
        return jsonify({'error': f'计算失败: {exc}'}), 500

def tandem_jv(data):
    try:
        params = _parse_full_params(data)
    except (TypeError, ValueError):
        return jsonify({'error': '参数无效'}), 400

    try:
        result = _tandem_core(params)
        response = {
            'mode': result['mode'],
            'voltages': result['voltages'].tolist(),
            'currents': (result['currents'] * 1e3).tolist(),
            'l_opt': float(result['l_opt']),
            'efficiency': float(result['eff']),
            'Jsc': float(result['jsc']),
            'Voc': float(result['voc']),
            'FF': float(result['ff'])
        }

        if result['mode'] == '4T' and result.get('component'):
            comp = result['component']
            response['curves'] = {
                'pvk': {
                    'voltages': comp['pvk']['voltages'].tolist(),
                    'currents': (comp['pvk']['currents'] * 1e3).tolist()
                },
                'si_bottom': {
                    'voltages': comp['si_bottom']['voltages'].tolist(),
                    'currents': (comp['si_bottom']['currents'] * 1e3).tolist()
                },
                'si_alone': {
                    'voltages': comp['si_alone']['voltages'].tolist(),
                    'currents': (comp['si_alone']['currents'] * 1e3).tolist()
                }
            }
            response['pvk'] = {
                'efficiency': float(comp['pvk']['eff']),
                'Jsc': float(comp['pvk']['jsc']),
                'Voc': float(comp['pvk']['voc']),
                'FF': float(comp['pvk']['ff'])
            }
            response['si_bottom'] = {
                'efficiency': float(comp['si_bottom']['eff']),
                'Jsc': float(comp['si_bottom']['jsc']),
                'Voc': float(comp['si_bottom']['voc']),
                'FF': float(comp['si_bottom']['ff'])
            }
            response['si_alone'] = {
                'efficiency': float(comp['si_alone']['eff']),
                'Jsc': float(comp['si_alone']['jsc']),
                'Voc': float(comp['si_alone']['voc']),
                'FF': float(comp['si_alone']['ff'])
            }
            response['efficiency_total'] = float(comp['pvk']['eff'] + comp['si_bottom']['eff'])

        return jsonify(response)
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500
    except Exception as exc:
        return jsonify({'error': f'计算失败: {exc}'}), 500

def jsonify(data):
    return data


def _import_csv(payload, kind):
    name = payload['filename']
    if not name.lower().endswith('.csv'):
        raise ValueError('仅支持 CSV 文件')
    table = pd.read_csv(io.StringIO(payload['text']))
    extract = _extract_eqe_arrays if kind == 'eqe' else _extract_tx_arrays
    arrays = extract(table)
    if len(arrays[0]) < 2 or not all(np.all(np.isfinite(a)) for a in arrays):
        raise ValueError('CSV 需要至少两行有效的数值数据')
    return {'token': _put_temp_dataset(kind, name, arrays), 'filename': name, 'saved': False}


def _validate_sweep(data):
    params = _parse_full_params(data)
    for key, value in params.items():
        if isinstance(value, (int, float)) and not np.isfinite(value):
            raise ValueError(f'{key} 必须为有限数值')
    for key in ('w', 'l_min', 'TCE_thick', 'pvk_thick', 'Si_Waf_thick', 'Rsh_pvk', 'Rsh_Si',
                'n_def', 'lambda_start', 'lambda_step', 'x_step'):
        if params[key] <= 0:
            raise ValueError(f'{key} 必须大于零')
    if not params['l_min'] <= params['l_max'] or not params['v_min'] < params['v_max'] or params['v_max'] <= 0:
        raise ValueError('请检查电极间距和电压的扫描范围')
    if not params['lambda_start'] < params['lambda_stop']:
        raise ValueError('波长终止值必须大于起始值')
    if not 2 <= params['l_points'] <= 5000 or not 2 <= params['v_points'] <= 5000:
        raise ValueError('电极间距和电压的采样点数应在 2 至 5000 之间')
    wavelengths = (params['lambda_stop'] - params['lambda_start']) / params['lambda_step'] + 2
    if wavelengths > 5000:
        raise ValueError('波长采样点过多，请增大波长步长')
    if not (params['pvk_eqe_dataset'] or params['pvk_eqe_token']):
        positions = (5147 + 1e7 * (params['pvk_thick'] + params['TCE_thick'])) / params['x_step']
        if wavelengths * positions > 8000000:
            raise ValueError('光学网格超出浏览器计算范围，请增大波长步长或横向网格步长')


def calculate(operation, payload_json):
    """Run one calculator operation inside the browser worker."""
    data = json.loads(payload_json)
    try:
        if operation == 'upload_eqe':
            response = _import_csv(data, 'eqe')
        elif operation == 'upload_tx':
            response = _import_csv(data, 'trans')
        elif operation in ('pvk_datasets', 'pvk_eqe_datasets', 'pvk_tx_datasets'):
            response = {'pvk_datasets': pvk_datasets, 'pvk_eqe_datasets': pvk_eqe_datasets,
                        'pvk_tx_datasets': pvk_tx_datasets}[operation]()
        else:
            if operation in ('tandem_full', 'tandem_jv'):
                _validate_sweep(data)
            response = {'rs': calc_rs, 'si_lifetime': si_lifetime,
                        'tandem_full': tandem_full, 'tandem_jv': tandem_jv}[operation](data)
        if isinstance(response, tuple):
            response = response[0]
        return json.dumps(response, allow_nan=False)
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        return json.dumps({'error': str(error)})
