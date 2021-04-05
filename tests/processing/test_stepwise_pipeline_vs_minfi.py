#PATH = '/Volumes/LEGX/Barnes/44668_MURMETVEP/204617710009'
#PATH = '/Volumes/LEGX/Barnes/48230_MURMETVEP/361821/204879580038'
#PATH =  '../../docs/example_data/mouse/'
# PATH = 'docs/example_data/mouse' # --- future
#PATH =  '/Volumes/LEGX/Barnes/mouse_test'
# PATH =  '../../docs/example_data/GSE69852/minfi/' #--- for testing in console
PATH = 'docs/example_data/minfi/'
IDAT_SOURCE = 'docs/example_data/GSE69852'
import methylprep
import pandas as pd
import numpy as np
from pathlib import Path
import shutil

def test_noob_df_same_size_as_minfi():
    ID = '9247377085_R04C02'
    print('* loading mouse manifest')
    manifest = methylprep.files.Manifest(methylprep.models.ArrayType('450k'))
    print('* loading one idat pair of files')
    green_filepath = Path(PATH, f'{ID}_Grn.idat') #'204879580038_R06C02_Grn.idat')
    red_filepath = Path(PATH, f'{ID}_Red.idat') #'204879580038_R06C02_Red.idat')
    print(f"* GREEN --> {green_filepath.name}")
    print(f"* RED --> {red_filepath.name}")
    if not green_filepath.exists():
        shutil.copy(Path(IDAT_SOURCE, f'{ID}_Grn.idat'), green_filepath)
    if not red_filepath.exists():
        shutil.copy(Path(IDAT_SOURCE, f'{ID}_Red.idat'), red_filepath)

    green_idat = methylprep.files.IdatDataset(green_filepath, channel=methylprep.models.Channel.GREEN)
    red_idat = methylprep.files.IdatDataset(red_filepath, channel=methylprep.models.Channel.RED)
    sample = 1
    print('* raw_dataset')
    raw_dataset = methylprep.models.raw_dataset.RawDataset(sample, green_idat, red_idat)

    print('* meth_dataset.unmethylated')
    unmethylated = methylprep.models.MethylationDataset.unmethylated(raw_dataset, manifest)

    print('* meth_dataset.methylated')
    methylated = methylprep.models.MethylationDataset.methylated(raw_dataset, manifest)

    m_minfi = pd.read_csv(Path(PATH, 'minfi_raw_meth.csv')).rename(columns={'Unnamed: 0':'IlmnID'}).set_index('IlmnID')
    u_minfi = pd.read_csv(Path(PATH, 'minfi_raw_unmeth.csv')).rename(columns={'Unnamed: 0':'IlmnID'}).set_index('IlmnID')
    m1 = methylated.data_frame.sort_index()[['mean_value']].rename(columns={'mean_value': ID})
    m2 = m_minfi[[ID]]
    mean_diff_m = (m1 - m2).mean()
    u1 = unmethylated.data_frame.sort_index()[['mean_value']].rename(columns={'mean_value': ID})
    u2 = u_minfi[[ID]]
    mean_diff_u = (u1 - u2).mean()
    print(f"total difference, meth: {mean_diff_m}, unmeth: {mean_diff_u}")
    if float(mean_diff_m.sum()) != 0 or float(mean_diff_u.sum()) != 0:
        raise AssertionError(f"raw meth/unmeth values don't match between methylprep and minfi METH: {float(mean_diff_m.sum())}, UNMETH: {float(mean_diff_u.sum())}")

    nm_minfi = pd.read_csv(Path(PATH, 'minfi_noob_meth.csv')).rename(columns={'Unnamed: 0':'IlmnID'}).set_index('IlmnID').sort_index()
    nu_minfi = pd.read_csv(Path(PATH, 'minfi_noob_unmeth.csv')).rename(columns={'Unnamed: 0':'IlmnID'}).set_index('IlmnID').sort_index()
    b_minfi = pd.read_csv(Path(PATH, 'minfi_noob_betas.csv')).rename(columns={'Unnamed: 0':'IlmnID'}).set_index('IlmnID').sort_index()

    container = methylprep.processing.SampleDataContainer(raw_dataset, manifest,
        retain_uncorrected_probe_intensities=True,
        pval=False,
        do_noob=True,
        quality_mask=False,
        switch_probes=False,
        correct_dye_bias=False,
        debug=False,
        sesame=False,
        )
    data_frame = container.preprocess()
    data_frame = container.process_beta_value(data_frame)
    #container._postprocess(input_dataframe, calculate_beta_value, 'beta_value', offset)
    #beta_df = self.process_beta_value(containers[0]data_frame)
    #pre_noob_meth = container.methylated.data_frame[['bg_corrected']].sort_index()
    #pre_noob_unmeth = container.unmethylated.data_frame[['bg_corrected']].sort_index()

    noob_meth_match = all(np.isclose(nm_minfi['9247377085_R04C02'].round(0), data_frame['noob_meth'].sort_index(), atol=1.0))
    noob_unmeth_match = all(np.isclose(nu_minfi['9247377085_R04C02'].round(0), data_frame['noob_unmeth'].sort_index(), atol=1.0))
    print(f"minfi NOOB matches for METH: {noob_meth_match}, UNMETH: {noob_unmeth_match}")
    if noob_meth_match is False or noob_unmeth_match is False:
        raise AssertionError("noob meth or unmeth values don't match between minfi and methylprep (expect 100% match)")

    noob_betas_match = sum(np.isclose(b_minfi['9247377085_R04C02'], data_frame['beta_value'].sort_index(), atol=0.03))/len(data_frame)
    noob_betas_loose_match = sum(np.isclose(b_minfi['9247377085_R04C02'], data_frame['beta_value'].sort_index(), atol=0.1))/len(data_frame)
    print(f"minfi betas match (+/- 0.03): {noob_betas_match} or +/- 0.1: {noob_betas_loose_match}")

    # this overwrites data, so copying it
    alt_frame = container._postprocess(data_frame.copy(), methylprep.processing.postprocess.calculate_beta_value, 'beta_value', offset=0)
    noob_betas_match = sum(np.isclose(b_minfi['9247377085_R04C02'], alt_frame['beta_value'].sort_index(), atol=0.001))/len(data_frame)
    noob_betas_loose_match = sum(np.isclose(b_minfi['9247377085_R04C02'], alt_frame['beta_value'].sort_index(), atol=0.01))/len(data_frame)
    print(f"minfi betas match (+/- 0.001): {noob_betas_match} or +/- 0.01: {noob_betas_loose_match}")
    if noob_betas_match < 0.999:
        raise AssertionError("noob betas don't match between minfi and methylprep (expecte 99.9% of betas for probes to be +/- 0.001)")

    Path(PATH, f'{ID}_Grn.idat').unlink()
    Path(PATH, f'{ID}_Red.idat').unlink()
    return {'mf_meth': nm_minfi, 'mf_unmeth': nu_minfi, 'mf_beta': b_minfi,
        'df': data_frame.sort_index(), 'test': alt_frame}

#grn, red = test_noob_df_same_size()

def shrink_csv(filename):
    # use on minfi output, but on betas use round
    PATH = 'docs/example_data/minfi/'
    # minfi_raw_betas.csv
    x = pd.read_csv(Path(PATH, filename))
    if 'meth' in filename or 'unmeth' in filename:
        x['9247377085_R04C02'] = x['9247377085_R04C02'].astype(int)
    elif 'betas' in filename:
        x['9247377085_R04C02'] = x['9247377085_R04C02'].round(3)
    x.to_csv(Path(PATH, filename), index=False)
    test = pd.read_csv(Path(PATH, filename)).rename(columns={'Unnamed: 0':'IlmnID'}).set_index('IlmnID').sort_index()
    return test