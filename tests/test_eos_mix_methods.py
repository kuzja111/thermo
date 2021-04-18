# -*- coding: utf-8 -*-
'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2020, Caleb Bell <Caleb.Andrew.Bell@gmail.com>

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

import pytest
from thermo.eos import *
from thermo.eos_mix import *
from thermo.eos_alpha_functions import *
from thermo.eos_mix_methods import *
from fluids.constants import R
from fluids.numerics import jacobian, hessian, assert_close, assert_close1d, assert_close2d, assert_close3d, derivative
from math import log, exp, sqrt
import numpy as np
from thermo.eos_mix_methods import a_alpha_quadratic_terms, a_alpha_and_derivatives_quadratic_terms


def test_a_alpha_quadratic_terms():
    # useful test case for speed.
    expect = [1.018836674553355, 2.191757517626393, 2.563258602852081, 1.5598326706034975, 2.70593281974093, 3.7034025281989855, 4.539954054126808, 4.699007689627005, 5.544738410220301, 5.727506758376061, 6.747016798786708, 7.772541929210375, 8.824329534067225, 9.881609693824497, 10.818879356535186, 11.967885231615968, 13.064056888046336, 14.301191101517293, 15.549382410454996, 16.514506861687853, 17.70128879207487, 18.588871716258463, 19.587383418298344, 21.163882746233718, 22.71677093839829, 23.693174106957997, 24.84638402761533, 26.32710900857889, 27.628174407150638, 27.35173402605858, 30.078139085433158, 29.6938067153124, 30.975794852828585, 31.612211604350215, 37.346889330614765, 5.8657490543188056, 6.918460471177853, 7.885934394505012, 7.987258405203353, 9.096924819311049, 5.4186445304744675, 6.364741674932172, 6.247071329729653, 7.191150355969193]
    a_alphas = [0.0865274961332042, 0.4004331347550168, 0.5476837363175464, 0.20281544374537322, 0.610350096562494, 1.1432648066725495, 1.7180979223407897, 1.8405910620140276, 2.56275518543631, 2.734489234665559, 3.794622523842678, 5.035830969924731, 6.490952532386477, 8.139549888291587, 9.756848311930623, 11.939326501216337, 14.226600071224336, 17.048627321670082, 20.154465549725934, 22.73401890914733, 26.118893369963804, 28.803884311242584, 31.98142763556359, 37.33667941647009, 43.0168093920849, 46.79414203338489, 51.460189856771855, 57.77651478272769, 63.62816155455672, 62.36123776101297, 75.41312259487229, 73.4982082371554, 79.98156837889205, 83.30187138391334, 116.2663039720862, 2.8680845884126343, 3.9899175858237754, 5.183836756317098, 5.317903685129213, 6.898175009281366, 2.447520402314526, 3.3768094978613767, 3.2531038444204294, 4.3106398143326805]
    a_alpha_roots = [i**0.5 for i in a_alphas]
    kijs = np.zeros((44, 44)).tolist()
    zs = [9.11975115499676e-05, 9.986813065240533e-05, 0.0010137795304828892, 0.019875879000370657, 0.013528874875432457, 0.021392773691700402, 0.00845450438914824, 0.02500218071904368, 0.016114189201071587, 0.027825798446635016, 0.05583179467176313, 0.0703116540769539, 0.07830577180555454, 0.07236459223729574, 0.0774523322851419, 0.057755091407705975, 0.04030134965162674, 0.03967043780553758, 0.03514481759005302, 0.03175471055284055, 0.025411123554079325, 0.029291866298718154, 0.012084986551713202, 0.01641114551124426, 0.01572454598093482, 0.012145363820829673, 0.01103585282423499, 0.010654818322680342, 0.008777712911254239, 0.008732073853067238, 0.007445155260036595, 0.006402875549212365, 0.0052908087849774296, 0.0048199150683177075, 0.015943943854195963, 0.004452253754752775, 0.01711981267072777, 0.0024032720444511282, 0.032178399403544646, 0.0018219517069058137, 0.003403378548794345, 0.01127516775495176, 0.015133143423489698, 0.029483213283483682]

    a_alpha, a_alpha_j_rows = a_alpha_quadratic_terms(a_alphas, a_alpha_roots, 299.0, zs, kijs)
    assert_close1d(expect, a_alpha_j_rows, rtol=1e-14)
    assert_close(a_alpha, 11.996512274167202, rtol=1e-14)

    # Small case but with constant kijs
    kijs = [[0,.083],[0.083,0]]
    zs = [0.1164203, 0.8835797]
    a_alphas = [0.2491099357671155, 0.6486495863528039]
    a_alpha_roots = [i**0.5 for i in a_alphas]

    a_alpha, a_alpha_j_rows = a_alpha_quadratic_terms(a_alphas, a_alpha_roots, 299.0, zs, kijs)
    assert_close1d([0.35469988173420947, 0.6160475723779467], a_alpha_j_rows, rtol=1e-14)
    assert_close(a_alpha, 0.5856213958288955, rtol=1e-14)


def test_a_alpha_and_derivatives_quadratic_terms():
    expect = [1.018836674553355, 2.191757517626393, 2.563258602852081, 1.5598326706034975, 2.70593281974093, 3.7034025281989855, 4.539954054126808, 4.699007689627005, 5.544738410220301, 5.727506758376061, 6.747016798786708, 7.772541929210375, 8.824329534067225, 9.881609693824497, 10.818879356535186, 11.967885231615968, 13.064056888046336, 14.301191101517293, 15.549382410454996, 16.514506861687853, 17.70128879207487, 18.588871716258463, 19.587383418298344, 21.163882746233718, 22.71677093839829, 23.693174106957997, 24.84638402761533, 26.32710900857889, 27.628174407150638, 27.35173402605858, 30.078139085433158, 29.6938067153124, 30.975794852828585, 31.612211604350215, 37.346889330614765, 5.8657490543188056, 6.918460471177853, 7.885934394505012, 7.987258405203353, 9.096924819311049, 5.4186445304744675, 6.364741674932172, 6.247071329729653, 7.191150355969193]
    a_alphas = [0.0865274961332042, 0.4004331347550168, 0.5476837363175464, 0.20281544374537322, 0.610350096562494, 1.1432648066725495, 1.7180979223407897, 1.8405910620140276, 2.56275518543631, 2.734489234665559, 3.794622523842678, 5.035830969924731, 6.490952532386477, 8.139549888291587, 9.756848311930623, 11.939326501216337, 14.226600071224336, 17.048627321670082, 20.154465549725934, 22.73401890914733, 26.118893369963804, 28.803884311242584, 31.98142763556359, 37.33667941647009, 43.0168093920849, 46.79414203338489, 51.460189856771855, 57.77651478272769, 63.62816155455672, 62.36123776101297, 75.41312259487229, 73.4982082371554, 79.98156837889205, 83.30187138391334, 116.2663039720862, 2.8680845884126343, 3.9899175858237754, 5.183836756317098, 5.317903685129213, 6.898175009281366, 2.447520402314526, 3.3768094978613767, 3.2531038444204294, 4.3106398143326805]
    a_alpha_roots = [i**0.5 for i in a_alphas]
    a_alpha_i_root_invs = [1.0/i for i in a_alphas]
    da_alpha_dTs = [-0.00025377859043732546, -0.000934247068461214, -0.000816789460173304, -0.0003641243787874678, -0.0010503058450047169, -0.0019521746900983052, -0.0028718927680108602, -0.0030862530923667516, -0.0043109072968568855, -0.004719357153237089, -0.006631042744989444, -0.008954841106859145, -0.01175296124567969, -0.015014798912202318, -0.018394836388991746, -0.02261696126764091, -0.02691416109598246, -0.03306276569415665, -0.03972067690500332, -0.04434234645435802, -0.05166183446540069, -0.05661884581837739, -0.06384511544740731, -0.07534567027524366, -0.08688546863889157, -0.09454104531596857, -0.1047355386575357, -0.12085503194237243, -0.13251190497391216, -0.13109044690165458, -0.1584965979082082, -0.15738400415699616, -0.1706975126112625, -0.17869250096210298, -0.24786999267933035, -0.0040612961454164305, -0.005861031978967661, -0.007870669654243058, -0.00806706054424201, -0.011089166549563573, -0.0035751401389282128, -0.005057878813908274, -0.004795418755334288, -0.0063951285412122945]
    d2a_alpha_dT2s = [7.951210065548482e-07, 2.6469203076280187e-06, 1.970376231974855e-06, 9.337390218103036e-07, 2.654206140072756e-06, 4.920336341685227e-06, 7.186749294919237e-06, 7.73122782691325e-06, 1.0810615491775454e-05, 1.1938080101460763e-05, 1.6845558981373303e-05, 2.288659685773046e-05, 3.022862525081902e-05, 3.887335363056251e-05, 4.799818908733702e-05, 5.9116869795960396e-05, 7.031530412634311e-05, 8.71642719698682e-05, 0.00010534213565791343, 0.00011714843555809333, 0.00013719528984525276, 0.00015001164237180505, 0.00017013611809931108, 0.0002016001519076944, 0.00023255486736407165, 0.0002530719148656703, 0.0002811419418128126, 0.00032782536312720063, 0.000358837713019585, 0.00035626762677964024, 0.00043071802720069994, 0.0004308123103893313, 0.0004666480764343225, 0.0004894792537071127, 0.0006773356550351481, 9.64428714604626e-06, 1.4073199340092461e-05, 1.9092839815989808e-05, 1.956381512959782e-05, 2.739514336342284e-05, 8.569704889318595e-06, 1.2217713526317966e-05, 1.1526841531601815e-05, 1.5402352528062937e-05]

    da_alpha_dT_j_rows_expect = [-0.0024659779471849236, -0.0046475548895564215, -0.004356514353727929, -0.002888183050970737, -0.0049094724710971645, -0.0066946247849404734, -0.008125158529797675, -0.008422079528590325, -0.009952764932789312, -0.010406054570834938, -0.012331292438012833, -0.014325077425132872, -0.01640670440194842, -0.01854046658049185, -0.02051894196830183, -0.022751981036326308, -0.02481953443659406, -0.027509548756389217, -0.030155386331164644, -0.031859224259789314, -0.03439180249090889, -0.036002133443470065, -0.0382361992513997, -0.0415431605007282, -0.04461176649968248, -0.046535861707927346, -0.04898614541953604, -0.05264915066454394, -0.055124368695664686, -0.05483970527179004, -0.06030003256343941, -0.06011776608310644, -0.06260298333060192, -0.0640616331561035, -0.07543630216258783, -0.009748518366766266, -0.011681157292387554, -0.013509225924011457, -0.013677421745325026, -0.015989657410498563, -0.009126533178948, -0.010838121814247793, -0.010563651638562304, -0.01219409084892938]

    kijs = np.zeros((44, 44)).tolist()
    zs = [9.11975115499676e-05, 9.986813065240533e-05, 0.0010137795304828892, 0.019875879000370657, 0.013528874875432457, 0.021392773691700402, 0.00845450438914824, 0.02500218071904368, 0.016114189201071587, 0.027825798446635016, 0.05583179467176313, 0.0703116540769539, 0.07830577180555454, 0.07236459223729574, 0.0774523322851419, 0.057755091407705975, 0.04030134965162674, 0.03967043780553758, 0.03514481759005302, 0.03175471055284055, 0.025411123554079325, 0.029291866298718154, 0.012084986551713202, 0.01641114551124426, 0.01572454598093482, 0.012145363820829673, 0.01103585282423499, 0.010654818322680342, 0.008777712911254239, 0.008732073853067238, 0.007445155260036595, 0.006402875549212365, 0.0052908087849774296, 0.0048199150683177075, 0.015943943854195963, 0.004452253754752775, 0.01711981267072777, 0.0024032720444511282, 0.032178399403544646, 0.0018219517069058137, 0.003403378548794345, 0.01127516775495176, 0.015133143423489698, 0.029483213283483682]

    a_alpha, da_alpha_dT, d2a_alpha_dT2, a_alpha_j_rows, da_alpha_dT_j_rows = a_alpha_and_derivatives_quadratic_terms(a_alphas, a_alpha_roots, da_alpha_dTs, d2a_alpha_dT2s, 299.0, zs, kijs)
    assert_close1d(expect, a_alpha_j_rows, rtol=1e-14)
    assert_close(a_alpha, 11.996512274167202, rtol=1e-14)
    assert_close(da_alpha_dT, -0.0228875173310534, rtol=1e-14)
    assert_close(d2a_alpha_dT2, 5.9978809895526926e-05, rtol=1e-14)
    assert_close1d(da_alpha_dT_j_rows_expect, da_alpha_dT_j_rows, rtol=1e-14)


    kijs = [[0,.083],[0.083,0]]
    zs = [0.1164203, 0.8835797]
    # eos = PRMIX(T=190.0, P=40.53e5, Tcs=[190.63, 373.55], Pcs=[46.17E5, 90.07E5], omegas=[0.01, 0.1], zs=zs, kijs=kijs)
    a_alphas = [0.2491099357671155, 0.6486495863528039]
    da_alpha_dTs = [-0.0005102028006086241, -0.0011131153520304886]
    d2a_alpha_dT2s = [1.8651128859234162e-06, 3.884331923127011e-06]
    a_alpha_roots = [i**0.5 for i in a_alphas]

    a_alpha, da_alpha_dT, d2a_alpha_dT2, a_alpha_j_rows, da_alpha_dT_j_rows = a_alpha_and_derivatives_quadratic_terms(a_alphas, a_alpha_roots, da_alpha_dTs, d2a_alpha_dT2s, 299.0, zs, kijs)


    assert_close(a_alpha, 0.5856213958288957, rtol=1e-14)
    assert_close(da_alpha_dT, -0.001018667672891354, rtol=1e-14)
    assert_close(d2a_alpha_dT2, 3.5666981785619988e-06, rtol=1e-14)
    assert_close1d(a_alpha_j_rows, [0.35469988173420947, 0.6160475723779467], rtol=1e-14)
    assert_close1d(da_alpha_dT_j_rows, [-0.0006723873746135188, -0.0010642935017889568], rtol=1e-14)


def test_a_alpha_aijs_composition_independent():
    kijs = [[0,.083],[0.083,0]]
    a_alphas = [0.2491099357671155, 0.6486495863528039]
    a_alpha_ijs, a_alpha_roots, a_alpha_ij_roots_inv = a_alpha_aijs_composition_independent(a_alphas, kijs)

    assert_close2d(a_alpha_ijs, [[0.2491099357671155, 0.3686123937424334], [0.3686123937424334, 0.6486495863528038]], rtol=1e-13)
    assert_close1d(a_alpha_roots, [0.4991091421393877, 0.8053878484015039], rtol=1e-13)
    assert_close1d(a_alpha_ij_roots_inv,  [[4.014291910599931, 2.4877079977965977], [2.4877079977965977, 1.5416644379945614]], rtol=1e-13)


def test_PR_lnphis_fastest():
    kwargs = dict(Tcs=[190.56400000000002, 305.32, 369.83, 126.2],
                  Pcs=[4599000.0, 4872000.0, 4248000.0, 3394387.5],
                  omegas=[0.008, 0.098, 0.152, 0.04],
                  zs=[.1, .2, .3, .4],
                  kijs=[[0.0, -0.0059, 0.0119, 0.0289], [-0.0059, 0.0, 0.0011, 0.0533], [0.0119, 0.0011, 0.0, 0.0878], [0.0289, 0.0533, 0.0878, 0.0]])
    eos = PRMIX(T=200, P=1e5, **kwargs)
    expect = eos.lnphis_l
    calc = PR_lnphis_fastest(eos.zs, eos.T, eos.P, 4, eos.kijs, True, False, eos.bs, eos.a_alphas, eos.a_alpha_roots)
    assert_close1d(expect, calc, rtol=1e-14)

    expect = eos.lnphis_g
    calc = PR_lnphis_fastest(eos.zs, eos.T, eos.P, 4, eos.kijs, False, True, eos.bs, eos.a_alphas, eos.a_alpha_roots)
    assert_close1d(expect, calc, rtol=1e-14)