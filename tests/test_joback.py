# -*- coding: utf-8 -*-
'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2017, Caleb Bell <Caleb.Andrew.Bell@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

import os
import pytest
from fluids.numerics import assert_close, assert_close1d
from thermo.group_contribution.joback import *
from thermo.group_contribution.joback import J_BIGGS_JOBACK_SMARTS_id_dict

from chemicals.identifiers import pubchem_db

folder = os.path.join(os.path.dirname(__file__), 'Data')

try:
    import rdkit
    from rdkit import Chem
except:
    rdkit = None
from thermo import Chemical

@pytest.mark.rdkit
@pytest.mark.skipif(rdkit is None, reason="requires rdkit")
def test_Joback_acetone():
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    from rdkit.Chem import AllChem
    from rdkit.Chem import rdMolDescriptors
    for i in [Chem.MolFromSmiles('CC(=O)C'), 'CC(=O)C']:
        ex = Joback(i) # Acetone example
        assert_close(ex.Tb(ex.counts), 322.11)
        assert_close(ex.Tm(ex.counts), 173.5)
        assert_close(ex.Tc(ex.counts), 500.5590049525365)
        assert_close(ex.Tc(ex.counts, 322.11), 500.5590049525365)
        assert_close(ex.Pc(ex.counts, ex.atom_count), 4802499.604994407)
        assert_close(ex.Vc(ex.counts), 0.0002095)
        assert_close(ex.Hf(ex.counts), -217830)
        assert_close(ex.Gf(ex.counts), -154540)
        assert_close(ex.Hfus(ex.counts), 5125)
        assert_close(ex.Hvap(ex.counts), 29018)
        assert_close1d(ex.Cpig_coeffs(ex.counts),[7.52, 0.26084, -0.0001207, 1.546e-08] )
        assert_close(ex.Cpig(300.0), 75.32642000000001)
        assert_close1d(ex.mul_coeffs(ex.counts), [839.11, -14.99])
        assert_close(ex.mul(300.0), 0.0002940378347162687)

    with pytest.raises(ValueError):
        # Raise an error if there are no groups matched
        obj = Joback('[Fe]')
        obj.estimate()

    # Test we can handle missing groups
    nitrobenzene = 'C1=CC=C(C=C1)[N+](=O)[O-]'
    obj = Joback(nitrobenzene)
    res = obj.estimate()
    assert res['mul_coeffs'] is None


@pytest.mark.fuzz
@pytest.mark.slow
@pytest.mark.rdkit
@pytest.mark.skipif(rdkit is None, reason="requires rdkit")
def test_Joback_database():
    pubchem_db.autoload_main_db()

    f = open(os.path.join(folder, 'joback_log.txt'), 'w')
    from rdkit import Chem
    catalog = unifac_smarts = {i: Chem.MolFromSmarts(j) for i, j in J_BIGGS_JOBACK_SMARTS_id_dict.items()}
    lines = []
    for key in sorted(pubchem_db.CAS_index):
        chem_info = pubchem_db.CAS_index[key]
        try:
            mol = Chem.MolFromSmiles(chem_info.smiles)
            parsed = smarts_fragment(rdkitmol=mol, catalog=catalog, deduplicate=False)
            line = '%s\t%s\t%s\t%s\n' %(parsed[2], chem_info.CASs, chem_info.smiles, parsed[0])
        except Exception as e:
            line = '%s\t%s\t%s\n' %(chem_info.CASs, chem_info.smiles, e)
        lines.append(line)

    [f.write(line) for line in sorted(lines)]
    f.close()

# Maybe use this again if more work is done on Joback
del test_Joback_database


@pytest.mark.rdkit
@pytest.mark.skipif(rdkit is None, reason="requires rdkit")
def test_Fedors():
    Vc, status, _, _, _ = Fedors('CCC(C)O')
    assert_close(Vc, 0.000274024)
    assert status == 'OK'

    Vc, status, _, _, _ = Fedors('C1=CC=C2C(=C1)C=CC3=CC4=C(C=CC5=CC=CC=C54)C=C32')
    assert_close(Vc, 0.00089246)
    assert status == 'OK'

    Vc, status, _, _, _ = Fedors('C1=CC=C(C=C1)O')
    assert_close(Vc, 0.00026668)
    assert status == 'OK'

    Vc, status, _, _, _ = Fedors('C12=C3C4=C5C6=C1C7=C8C9=C1C%10=C%11C(=C29)C3=C2C3=C4C4=C5C5=C9C6=C7C6=C7C8=C1C1=C8C%10=C%10C%11=C2C2=C3C3=C4C4=C5C5=C%11C%12=C(C6=C95)C7=C1C1=C%12C5=C%11C4=C3C3=C5C(=C81)C%10=C23')
    assert_close(Vc, 0.001969256)
    assert status == 'OK'

    Vc, status, _, _, _ = Fedors('C12C3C4C1C5C2C3C45')
    assert_close(Vc, 0.000485046)
    assert status == 'OK'

    Vc, status, _, _, _ = Fedors('O=[U](=O)=O')
    assert status != 'OK'

@pytest.mark.rdkit
@pytest.mark.skipif(rdkit is None, reason="requires rdkit")
def test_Wilson_Jasperson():
    # Two points in Poling et al.
    Tc, Pc, _, _ = Wilson_Jasperson('CCC1=CC=CC=C1O', Tb=477.67, second_order=True)
    assert_close(Tc, 693.5671723593391)
    assert_close(Pc, 3743819.6667063655)    
    
    Tc, Pc, _, _ = Wilson_Jasperson('CCC1=CC=CC=C1O', Tb=477.67, second_order=False)
    
    assert_close(Tc, 702.8831365703206)
    assert_close(Pc, 3794106.4902720796)
    
    # Had a bug identifying an amine group here
    c = Chemical('aniline')
    Tc, Pc, _, _ = Wilson_Jasperson(c.rdkitmol, Tb=457.4)
    assert_close(Tc, 705.7480487320958)
    assert_close(Pc, 5247025.774965471)
    
    c = Chemical('tetramethylthiuram disulfide')
    Tc, Pc, _, _ = Wilson_Jasperson(c.rdkitmol, Tb=580.6)
    assert_close(Tc, 807.2810024378236)
    assert_close(Pc, 2555268.114365961)


    # Can't make it match no matter what I do, but nothing looks like an issue
    # c = Chemical('acetic acid')
    # Wilson_Jasperson_first_order(c.rdkitmol, Tb=391.2),584.6 
    
    # c = Chemical('2-nonanone')
    # Wilson_Jasperson_first_order(c.rdkitmol, Tb=467.7),651.8

@pytest.mark.rdkit
@pytest.mark.skipif(rdkit is None, reason="requires rdkit")
def test_Wilson_Jasperson_paper():

    chemical_names = ["ethane", "cyclopropane", "propane", "2-methylpropane", "butane", "cyclopentane", "2,2-dimethylpropane", "pentane", "2-methylbutane", "cyclohexane", "methylcyclopentane", "2,3-dimethylbutane", "3-methylpentane", "2,2-dimethylbutane", "2-methylpentane", "hexane", "ethylcyclopentane", "methylcyclohexane", "cycloheptane", "3,3-dimethylpentane", "2,4-dimethylpentane", "2,2-dimethylpentane", "heptane", "2-methylhexane", "3-ethylpentane", "2,3-dimethylpentane", "3-methylhexane", "2,2,3-trimethylbutane", "cyclooctane", "1,trans-4-dimethylcyclohexane", "2-methyl-3-ethylpentane", "3-ethylhexane", "3-ethyl-3-methylpentane", "2,3,3-trimethylpentane", "3,3-dimethylhexane", "2,2,3-trimethylpentane", "2,3,4-trimethylpentane", "octane", "4-methylheptane", "2,2,4-trimethylpentane", "2-methylheptane", "2,5-dimethylhexane", "2,2-dimethylhexane", "3-methylheptane", "3,4-dimethylhexane", "2,3-dimethylhexane", "2,4-dimethylhexane", "1,3,5-Trimethylcyclohexane", "2,2,3,3-tetramethylpentane", "2,3,3,4-tetramethylpentane", "2-methyloctane", "2,2,5-trimethylhexane", "2,2,3,4-tetramethylpentane", "2,2-dimethylheptane", "2,2,4,4-tetramethylpentane", "nonane", "cis-decalin", "trans-decalin", "2,2,3,3-tetramethylhexane", "decane", "3,3,5-trimethylheptane", "2,2,5,5-tetramethylhexane", "undecane", "dodecane", "tridecane", "tetradecane", "pentadecane", "hexadecane", "heptadecane", "octadecane", "ethene", "1,2-propadiene", "propene", "1,3-butadiene", "trans-2-butene", "cis-2-butene", "2-methylpropene", "1-butene", "cyclopentene", "cis-2-pentene", "2-methyl-2-butene", "1-pentene", "benzene", "cyclohexene", "1-hexene", "toluene", "1-heptene", "styrene", "1,2-dimethylbenzene", "1,3-dimethylbenzene", "ethylbenzene", "1,4-dimethylbenzene", "1-octene", "indan", "1-ethyl-4-methylbenzene", "propylbenzene", "1,2,3-trimethylbenzene", "1,3,5-trimethylbenzene", "1,2,4-trimethylbenzene", "isopropylbenzene", "1-nonene", "naphthalene", "tetralin", "1,2,4,5-tetramethylbenzene", "p-cymene", "isobutylbenzene", "butylbenzene", "1,4-diethylbenzene", "4,7,7-trimethyl-3-norcarene", "(1S)-(-)-.alpha.-pinene", "(R)-(+)-limonene", "1-decene", "2-methylnaphthalene", "1-methylnaphthalene", "1,1'-biphenyl", "2,7-dimethylnaphthalene", "hexamethylbenzene", "1-dodecene", "1,1':2',1''-terphenyl", "ethyne", "1-propyne", "bromotrifluoromethane", "chlorotrifluoromethane", "dichlorodifluoromethane", "trichlorofluoromethane", "carbon tetrachloride", "bromodifluoromethane", "chlorodifluoromethane", "dichlorofluoromethane", "chloroform", "trifluoromethane", "dichloromethane", "difluoromethane", "chloromethane", "fluoromethane", "chlorotrifluoroethene", "chloropentafluoroethane", "1,1,2-trichlorotrifluoroethane", "tetrafluoroethene", "hexafluoroethane", "1-chloro-2,2-difluoroethene", "1-chloro-1,2,2,2-tetrafluoroethane", "1,1-dichloro-2,2,2-trifluoroethane", "1,2-dichloro-1,1,2-trifluoroethane", "pentafluoroethane", "1-chloro-2,2,2-trifluoroethane", "1,1,2,2-tetrafluoroethane", "1,1,1,2-tetrafluoroethane", "1-chloro-1,1-difluoroethane", "1,1-dichloro-1-fluoroethane", "1,1,1-trifluoroethane", "1,2-dichloroethane", "1,1-dichloroethane", "1,1-difluoroethane", "bromoethane", "chloroethane", "fluoroethane", "1,2-dichlorohexafluoropropane", "octafluoropropane", "2H-perfluoropropane", "1,1,1,2,3,3-hexafluoropropane", "1,1,1,2,2-pentafluoropropane", "1,3-dichloropropane", "1,2-dichloropropane", "1-bromopropane", "1-chloropropane", "2-chloropropane", "octafluorocyclobutane", "perfluorobutane", "1,1,1,2,2,3,3,4-octafluorobutane", "2-chlorobutane", "1-chlorobutane", "perfluoropentane", "1-chloropentane", "tert-pentyl chloride", "perfluorobenzene", "perfluorohexane", "pentafluorobenzene", "1,2,4,5-tetrafluorobenzene", "1,3-dichlorobenzene", "1,3-difluorobenzene", "1,4-difluorobenzene", "1,2-difluorobenzene", "chlorobenzene", "fluorobenzene", "1-chlorohexane", "octafluorotoluene", "perfluoromethylcyclohexane", "perfluoroheptane", "4-fluorotoluene", "octadecafluorooctane", "1-chlorooctane", "methanol", "ethanol", "2-propenol", "2-propanol", "1-propanol", "1,2-propanediol", "2-methoxyethanol", "1-butanol", "2-methyl-1-propanol", "2-methyl-2-propanol", "2-butanol", "1,4-butanediol", "cyclopentanol", "1-pentanol", "2-methyl-2-butanol", "2-pentanol", "3-methyl-1-butanol", "2-methyl-1-butanol", "3-pentanol", "3-methyl-2-butanol", "2-propoxyethanol", "2-(2-methoxyethoxy)ethanol", "phenol", "cyclohexanol", "3-hexanol", "4-methyl-2-pentanol", "1-hexanol", "2-methyl-2-pentanol", "3-methyl-3-pentanol", "2-hexanol", "4-methyl-1-pentanol", "2-methyl-1-pentanol", "2-methyl-3-pentanol", "2-butoxyethanol", "3,6-dioxa-1-octanol", "2-methylphenol", "3-methylphenol", "4-methylphenol", "1-heptanol", "3-heptanol", "2-heptanol", "4-heptanol", "1-butoxy-2-propanol", "propyl carbitol", "2-ethylphenol", "3-ethylphenol", "1-phenylethanol", "2,6-xylenol", "4-ethylphenol", "2,4-dimethylphenol", "2,3-xylenol", "3,5-dimethylphenol", "3,4-xylenol", "2,5-xylenol", "2-octanol", "4-methyl-3-heptanol", "2-ethyl-1-hexanol", "1-octanol", "5-methyl-3-heptanol", "2-(2-butoxyethoxy)ethanol", "1-nonanol", "4-nonanol", "2-nonanol", "1-decanol", "2-decanol", "1-undecanol", "1-dodecanol", "oxirane", "methoxymethane", "epoxypropane", "methoxyethane", "dimethoxymethane", "furan", "ethyl vinyl ether", "tetrahydrofuran", "1,4-dioxane", "1-methoxypropane", "diethyl ether", "2-methoxypropane", "1,2-dimethoxyethane", "2-methylfuran", "3,4-dihydro-2H-pyran", "2-methyltetrahydrofuran", "tetrahydropyran", "methyl tert-butyl ether", "1-ethoxypropane", "butyl methyl ether", "butyl vinyl ether", "tert-amyl methyl ether", "tert-butyl ethyl ether", "isopropyl ether", "dipropyl ether", "methyl pentyl ether", "1,1-diethoxyethane", "methoxybenzene", "dibutyl ether", "dibenzofuran", "diphenyl ether", "propanone", "butanone", "cyclopentanone", "3-methyl-2-butanone", "2-pentanone", "3-pentanone", "cyclohexanone", "mesityl oxide", "2-hexanone", "3-hexanone", "4-methyl-2-pentanone", "4-heptanone", "3-heptanone", "2-heptanone", "acetophenone", "3-octanone", "4-octanone", "2-octanone", "2-nonanone", "5-nonanone", "4-nonanone", "3-nonanone", "5-decanone", "4-decanone", "2-decanone", "3-decanone", "6-undecanone", "2-undecanone", "3-undecanone", "2-dodecanone", "benzophenone", "ethanal", "propanal", "butanal", "pentanal", "hexanal", "heptanal", "octanal", "decanal", "acetic acid", "propanoic acid", "2-methylpropanoic acid", "butanoic acid", "pentanoic acid", "3-methylbutanoic acid", "hexanoic acid", "heptanoic acid", "octanoic acid", "2-ethylhexanoic acid", "nonanoic acid", "decanoic acid", "methyl methanoate", "methyl ethanoate", "ethyl methanoate", "dimethyl carbonate", "vinyl acetate", "gamma-butyrolactone", "methyl propanoate", "ethyl ethanoate", "propyl methanoate", "ethyl propanoate", "isopropyl ethanoate", "methyl butanoate", "propyl ethanoate", "methyl isobutyrate", "isobutyl ethanoate", "ethyl butanoate", "butyl ethanoate", "propyl propanoate", "cellosolve acetate", "1-methoxy-2-propyl acetate", "propyl butanoate", "propyl isobutyrate", "pentyl ethanoate", "ethyl isovalerate", "isobutyl propanoate", "ethyl pentanoate", "isoamyl acetate", "2-butoxyethyl acetate", "ethyl octanoate", "ethyl nonanoate", "methylamine", "ethylamine", "dimethylamine", "1,2-ethanediamine", "N,N-dimethylformamide", "propylamine", "trimethylamine", "isopropylamine", "pyrrole", "pyrrolidine", "2-butanamine", "diethylamine", "tert-butylamine", "butylamine", "piperidine", "aniline", "diisopropylamine", "dipropylamine", "triethylamine", "N,N-dimethylaniline", "diisobutylamine", "dibutylamine", "N,N,2-trimethylaniline", "pyridine", "3-methylpyridine", "2-methylpyridine", "4-methylpyridine", "2,6-dimethylpyridine", "3,5-dimethylpyridine", "2,3-dimethylpyridine", "3,4-dimethylpyridine", "2,4-dimethylpyridine", "2,5-dimethylpyridine", "acetonitrile", "propenenitrile", "propanenitrile", "butanenitrile", "pentanenitrile", "hexanenitrile", "benzonitrile", "octanenitrile", "methanethiol", "2-thiapropane", "ethanethiol", "1-propanethiol", "thiophene", "ethyl thiolacetate", "tetrahydrothiophene", "3-thiapentane", "1-butanethiol", "thianaphthene", "dibenzothiophene", "pentafluorodimethyl ether", "2,2,2-trifluoroethanol", "trifluoromethoxymethane", "hexafluorooxetane", "perfluoro(dimethoxymethane)", "1,1,2,2-tetrafluoroethyl trifluoromethyl ether", "1-chloro-2,2,2-trifluoro difluoromethyl ether", "1,2,2,2-tetrafluoroethyl difluoromethyl ether", "methyl pentafluoroethyl ether", "1,2,2,3-tetrafluoro-1-propanol", "methyl 2,2,2-trifluoroethyl ether", "perfluorotetrahydrofuran", "heptafluoropropyl trifluoromethyl ether", "4,4,5,5-tetrafluoro-2-(trifluoromethyl)- 1,3-dioxolane", "heptafluoro-1,4-dioxane", "1,1-bis(difluoromethoxy)tetrafluoroethane", "3,3,4,4,4-pentafluoro-2-butanone", "methyl perfluoroisopropyl ether", "heptafluoropropyl methyl ether", "ethyl pentafluoroethyl ether", "perfluorovaleric acid", "methyl perfluoroisopropyl ketone", "tert-perfluorobutyl methyl ether", "1,5,5-trihydrooctafluoropentanol", "1,7,7-trihydrododecafluoroheptanol"]
    NBPs = [184.6, 240.3, 231, 261.4, 272.6, 322.4, 282.6, 309.2, 301.1, 353.9, 345, 331.2, 336.4, 322.9, 333.4, 341.9, 376.6, 374.1, 392, 359.2, 353.7, 352.4, 371.6, 363.2, 366.6, 363, 365, 354.1, 424, 392.5, 388.8, 391.7, 391.5, 387.8, 385.1, 383, 386.6, 398.8, 390.8, 372.4, 390.8, 382.3, 380, 392.1, 390.9, 388.8, 382.6, 413.7, 413.4, 414.6, 416.4, 397.1, 406.2, 405.9, 395.4, 423.9, 468.8, 460.2, 432.5, 447.3, 428.8, 410.2, 468.5, 489.5, 507.5, 526.4, 544, 560, 576, 590, 169.3, 238.7, 225.5, 268.7, 274.1, 276.8, 266.6, 266.8, 317.4, 310, 311.6, 303.3, 353.3, 356.1, 336.7, 383.8, 366.6, 418.6, 417.6, 412.3, 409.4, 411.5, 394.5, 450.7, 435.1, 432.5, 449.2, 437.8, 442.5, 425.5, 419.6, 491.15, 480.5, 469.6, 450.2, 445.9, 456.4, 456.8, 445, 430, 450.1, 444.3, 514.2, 517.6, 528.3, 538, 536.9, 486.5, 609, 189.5, 249.9, 215.3, 191.8, 243.4, 296.8, 349.9, 257.8, 232.3, 282, 334.4, 191, 313, 221.5, 249.3, 194.7, 244.6, 234, 320, 198, 195.1, 254.5, 261.2, 301, 302, 225.2, 279.3, 250.2, 247.1, 263.6, 305.1, 226.3, 356.6, 330.5, 249.1, 311.6, 286.1, 235.7, 310, 236.2, 256, 279.7, 254.8, 393.5, 369.4, 343.7, 319.7, 308, 267.2, 271.2, 300.5, 341, 351.6, 302.1, 381, 358.2, 353.4, 330.3, 358.9, 363.4, 446.2, 356.2, 362, 367.1, 404.9, 357.9, 408.2, 377.8, 349.5, 355.1, 389.8, 379, 456.4, 337.8, 351.5, 370.2, 355.5, 370.3, 460.3, 397.5, 390.8, 380.9, 355.6, 372.6, 502.9, 414, 411, 375.1, 392.3, 404.5, 401.8, 388.6, 385.2, 424.5, 466, 455, 434, 407.6, 404, 430, 395, 395.1, 412.4, 425, 421, 399.7, 444.3, 468, 464.2, 475.4, 475.1, 449, 429.5, 432.5, 428, 443.3, 488, 479.5, 490.6, 475.7, 474.2, 492, 483.2, 491.1, 493.4, 499.5, 483.6, 453, 428.2, 456, 468.1, 427, 504.5, 486.4, 465.6, 471, 504.2, 482, 517, 538, 283.7, 248.6, 307.5, 280.4, 315.4, 304.7, 308.8, 339, 374.5, 311.8, 307.8, 304, 358, 337, 358.8, 353, 361, 328.2, 336.3, 343.3, 367.1, 359.5, 346, 341.4, 363.3, 372.4, 376.2, 426.9, 415, 559, 531.5, 329.3, 352.7, 403.6, 367.1, 375.2, 375, 428.6, 402.8, 400.3, 396.5, 389.1, 416.8, 420.4, 423.8, 475.2, 438.6, 438.7, 446, 467.7, 461, 460.7, 461, 476.7, 478.7, 485.5, 478, 499, 504, 500, 519.7, 579, 294, 321.5, 347.8, 375.7, 401.6, 427, 442, 480, 391.2, 414.2, 427.3, 436.1, 459.2, 449.2, 477.5, 496, 510.7, 500.7, 527.2, 541.2, 304.9, 330.1, 327.3, 363.5, 345.7, 478, 352.7, 350.3, 354.1, 372.2, 361.8, 375.7, 374.7, 365.4, 390.2, 393.8, 399.2, 396, 429.7, 420, 416.2, 407, 421.7, 408.5, 410.1, 417.6, 414.7, 466, 480, 500.2, 266.7, 290, 280.4, 390.7, 426, 322.2, 276.4, 305.5, 403.1, 359.5, 336.2, 328.5, 317.3, 350.7, 379.2, 457.4, 357, 382.5, 362.2, 466.8, 412, 432.8, 458.5, 388.5, 417, 402.5, 418.3, 417.2, 445, 434.3, 452.2, 431.4, 430, 354.8, 350.4, 370.5, 390.9, 414, 436, 464.1, 475.5, 279.1, 310.3, 308.2, 340.9, 357.3, 386.9, 394.5, 365.2, 371, 494, 604.6, 238.6, 347.1, 239.3, 244.6, 263.3, 272.4, 322.5, 296.5, 278.7, 386.1, 304.8, 272.7, 280, 305, 312.7, 320, 314.4, 302.6, 307.4, 301.3, 414, 328.8, 326.5, 414, 444.2, ]
    expect_Tcs = [304.3, 408.1, 368.9, 406.2, 423.6, 512, 428.7, 469.1, 456.8, 547.2, 533.4, 491.8, 499.5, 479.4, 495, 507.7, 568.8, 565, 592, 523.1, 515.1, 513.2, 541.1, 528.9, 533.9, 528.6, 531.5, 515.7, 627, 580.5, 556.3, 560.4, 560.1, 554.8, 551, 548, 553.1, 570.6, 559.1, 532.8, 559.1, 547, 543.7, 561, 559.3, 556.3, 547.4, 600.3, 581.9, 583.6, 586.2, 559, 571.8, 571.4, 556.6, 596.7, 690.6, 677.9, 599.7, 620.3, 594.6, 568.8, 640.6, 660.7, 676.6, 693.8, 709.2, 722.5, 735.9, 746.7, 283.1, 390.8, 364.5, 426.6, 430.4, 434.7, 418.6, 418.9, 509.9, 474.6, 477.1, 464.4, 564, 556.2, 504.1, 596.3, 537.9, 640.7, 633.4, 625.3, 620.9, 624.1, 568.3, 696.7, 645.9, 642, 666.9, 649.9, 656.9, 631.6, 594.4, 755.3, 725.5, 683.7, 655.5, 649.2, 664.5, 665.1, 660.7, 638.4, 650.6, 619.7, 772.9, 778, 784.1, 792.2, 755.6, 660, 856.8, 321.7, 409.1, 342.8, 306.2, 386.8, 469.4, 550.9, 415.8, 375.7, 453.8, 535.4, 310.5, 510.4, 365.3, 414.9, 326, 384, 356.1, 483.3, 312.2, 298, 404.2, 401.5, 460.9, 462.4, 347.6, 433.9, 390.4, 385.5, 414.1, 477.2, 357.1, 564.3, 523, 397.9, 500.3, 460.6, 381.4, 452.4, 346.9, 379.1, 417.9, 384.2, 606.5, 569.4, 536.5, 500.3, 482, 398.8, 385.4, 433.3, 520.5, 536.7, 417.4, 568.8, 534.8, 527.9, 445.2, 541, 553.1, 687.6, 553.5, 562.5, 570.4, 633.4, 562.4, 597.4, 544.6, 478.7, 483.6, 597.2, 489.9, 645.2, 513.4, 522.7, 544, 518.5, 540.1, 654.6, 570.4, 559.9, 545.7, 509.5, 533.8, 704, 623.2, 596.9, 544.8, 569.7, 587.5, 583.5, 564.4, 559.4, 606.7, 656.3, 687.8, 639.9, 581.7, 576.6, 613.7, 563.7, 563.9, 588.6, 606.5, 600.8, 570.4, 624.9, 649.3, 687, 703.6, 703.1, 630.6, 603.2, 607.4, 601.1, 614.2, 667.6, 696.2, 712.3, 690.7, 688.5, 714.4, 701.6, 713.1, 716.4, 725.3, 702.2, 626.8, 592.5, 631, 647.7, 590.8, 681.2, 663.8, 635.4, 642.8, 679.2, 649.3, 688.1, 707.9, 483.6, 398.1, 505.1, 436.8, 480.5, 497.1, 473.8, 539.7, 581.7, 474, 467.9, 462.1, 533.5, 533.4, 561.8, 547.1, 559.5, 488.2, 500.3, 510.7, 539.5, 524.4, 504.7, 498, 530, 543.2, 539.9, 648.8, 585, 845.5, 775, 516.4, 539.4, 629.6, 549, 561.1, 560.8, 652.4, 595, 586.7, 581.2, 570.3, 599.9, 605.1, 609.9, 710.5, 620.8, 620.9, 631.3, 651.8, 642.5, 642.1, 642.5, 654.9, 657.7, 667, 656.7, 676.5, 683.2, 677.8, 695.8, 833, 469, 499, 527.1, 557.3, 584.4, 610.5, 621.8, 656, 584.6, 606.7, 614.6, 627.3, 649.6, 635.4, 665.2, 681.1, 692, 678.5, 705.5, 715.8, 474.4, 507.6, 497, 547.4, 519.6, 750.2, 530.1, 526.5, 526.3, 548, 532.7, 553.1, 551.7, 538, 563.9, 569.1, 576.9, 572.3, 611.4, 597.6, 591.3, 578.2, 599.1, 580.4, 582.6, 593.3, 589.2, 643.1, 652.7, 671.6, 435.7, 459.6, 444.3, 599, 641.7, 497.3, 426.6, 471.5, 650, 566.6, 506.9, 495.3, 478.4, 528.8, 582.4, 705.7, 517.3, 554.3, 524.8, 689.2, 577.5, 606.7, 664.2, 610.6, 639, 616.8, 641, 625.1, 666.7, 650.7, 677.5, 646.3, 644.2, 551.8, 536.9, 562.5, 580.8, 603.2, 624.1, 689.4, 659.7, 468.2, 503, 499.6, 536.6, 590.7, 584.7, 635.5, 560.3, 569.2, 781.6, 922.8, 360.5, 502.4, 368.8, 372.7, 374.4, 396.4, 471.6, 435, 412.3, 545.5, 459, 399.7, 392.3, 443, 454.2, 447.9, 458.5, 425.7, 439.6, 437.3, 554.2, 464.4, 453.5, 568.4, 582.8, ]
    missed = 0
    wrong = 0
    
    for name, Tb, expect in zip(chemical_names, NBPs, expect_Tcs):
        try:
            c = Chemical(name)
        except:
            missed += 1
            continue
        Tc, Pc, miss_Tc, miss_Pc = Wilson_Jasperson(c.rdkitmol, Tb)
        assert not miss_Tc
        assert not miss_Pc
