################################################################################
#
# Copyright (c) 2009 The MadGraph5_aMC@NLO Development team and Contributors
#
# This file is a part of the MadGraph5_aMC@NLO project, an application which 
# automatically generates Feynman diagrams and matrix elements for arbitrary
# high-energy processes in the Standard Model and beyond.
#
# It is subject to the MadGraph5_aMC@NLO license which should accompany this 
# distribution.
#
# For more information, visit madgraph.phys.ucl.ac.be and amcatnlo.web.cern.ch
#
################################################################################
from __future__ import division
from __future__ import absolute_import
import subprocess
import unittest
import os
import re
import shutil
import sys
import logging
import tempfile
import time
import math
from io import StringIO
from madgraph.various import lhe_parser

logger = logging.getLogger('test_cmd')

import tests.unit_tests.iolibs.test_file_writers as test_file_writers
from tests.parallel_tests.test_aloha import set_global
import tests.IOTests as IOTests

import madgraph
import madgraph.interface.master_interface as MGCmd
import madgraph.interface.amcatnlo_run_interface as NLOCmd
import madgraph.interface.launch_ext_program as launch_ext
import madgraph.iolibs.files as files
import madgraph.various.misc as misc
import madgraph.various.banner as banner


_file_path = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
_pickle_path =os.path.join(_file_path, 'input_files')

from madgraph import MG4DIR, MG5DIR, MadGraph5Error, InvalidCmd
from tests.acceptance_tests.test_cmd_madevent import check_html_page

pjoin = os.path.join

#===============================================================================
# TestCmd
#===============================================================================
class MECmdShell(IOTests.IOTestManager):
    """this treats all the command not related to MG_ME"""
    
    loadtime = time.time()
    
    def setUp(self):
        self.debugging = unittest.debug
    
        if not self.debugging:
            self.tmpdir = tempfile.mkdtemp(prefix='amc')
            #if os.path.exists(self.tmpdir):
            #    shutil.rmtree(self.tmpdir)
            #os.mkdir(self.tmpdir)
            self.path = pjoin(self.tmpdir,'MGProcess')
        else:
            if os.path.exists(pjoin(MG5DIR, 'TEST_AMC')):
                shutil.rmtree(pjoin(MG5DIR, 'TEST_AMC'))
            os.mkdir(pjoin(MG5DIR, 'TEST_AMC'))
            self.tmpdir = pjoin(MG5DIR, 'TEST_AMC')
            self.path = pjoin(self.tmpdir,'MGProcess')
        
    def tearDown(self):
        if not self.debugging:
            shutil.rmtree(self.tmpdir)
    
    
    def generate(self, process, model, multiparticles=[]):
        """Create a process"""

        def run_cmd(cmd):
            interface.exec_cmd(cmd, errorhandling=False, printcmd=False, 
                               precmd=True, postcmd=True)
            

        try:
            shutil.rmtree(self.path)
        except Exception as error:
            pass

        interface = MGCmd.MasterCmd()
        interface.no_notification()
        
        run_cmd('import model %s' % model)
        for multi in multiparticles:
            run_cmd('define %s' % multi)
        if isinstance(process, str):
            run_cmd('generate %s' % process)
        else:
            for p in process:
                run_cmd('add process %s' % p)
        if logging.getLogger('madgraph').level <= 20:
            stdout=None
            stderr=None
        #else:
        #    devnull =open(os.devnull,'w')
        #    stdout=devnull
        #    stderr=devnull

        interface.onecmd('output %s -f' % self.path)
        proc_card = open('%s/Cards/proc_card_mg5.dat' % self.path).read()
        self.assertTrue('generate' in proc_card or 'add process' in proc_card)
        run_cmd('set automatic_html_opening False --no_save')
        self.cmd_line = NLOCmd.aMCatNLOCmdShell(me_dir= '%s' % self.path)
        self.cmd_line.no_notification()
        self.cmd_line.run_cmd('set automatic_html_opening False --no_save')
        self.assertFalse(self.cmd_line.options['automatic_html_opening'])

    @staticmethod
    def join_path(*path):
        """join path and treat spaces"""     
        combine = os.path.join(*path)
        return combine.replace(' ',r'\ ')        
    
    def do(self, line):
        """ exec a line in the cmd under test """        
        self.cmd_line.exec_cmd(line, errorhandling=False,precmd=True)


    @set_global()
    def test_check_singletop_fastjet(self):
        cmd = os.getcwd()
        self.generate(['p p > t j QED^2=4 QCD^2=0 [real=QCD]'], 'sm-no_b_mass', multiparticles=['p = p b b~', 'j = j b b~'])

        card = open('%s/Cards/run_card_default.dat' % self.path).read()
        self.assertIn('10000 = nevents', card)
        card = card.replace('10000 = nevents', '100 = nevents')
        open('%s/Cards/run_card_default.dat' % self.path, 'w').write(card)
        os.system('cp  %s/Cards/run_card_default.dat %s/Cards/run_card.dat' % (self.path, self.path))

        card = open('%s/Cards/param_card_default.dat' % self.path).read()
        self.assertTrue( 'DECAY   6 1.491500e+00 # WT' in card)
        card = card.replace('DECAY   6 1.491500e+00 # WT', 'DECAY   6 0.0e+00 # WT')
        open('%s/Cards/param_card_default.dat' % self.path, 'w').write(card)
        os.system('cp  %s/Cards/param_card_default.dat %s/Cards/param_card.dat' % (self.path, self.path))

        card = open('%s/Cards/shower_card_default.dat' % self.path).read()
        self.assertIn('ANALYSE      =', card)
        card = card.replace('ANALYSE      =', 'ANALYSE     = mcatnlo_hwan_pp_tj.o myfastjetfortran.o mcatnlo_hbook_gfortran8.o')
        self.assertIn('EXTRALIBS    = stdhep Fmcfio', card)
        card = card.replace('EXTRALIBS    = stdhep Fmcfio', 'EXTRALIBS   = fastjet')
        open('%s/Cards/shower_card_default.dat' % self.path, 'w').write(card)
        os.system('cp  %s/Cards/shower_card_default.dat %s/Cards/shower_card.dat'% (self.path, self.path))

        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)
        self.do('generate_events -f')
        # test the lhe event file and plots exist
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/plot_HERWIG6_1_0.top' % self.path))

    #@IOTests.createIOTest()
    def test_check_html_long_process_strings(self):
        """ target: info.html
        """
        #check that the info.html file correctly lists all the subprocesses,
        #even when the process string has to be split on more lines (for length 
        #reasons)
        
        cmd = os.getcwd()
        self.generate(['p p > h w+ > ta+ ta- e+ ve QED^2=8 QCD^2=0 [QCD]'], 'sm')
        self.assertEqual(cmd, os.getcwd())

        #info_html_target = open(os.path.join(cmd, 'tests', 'input_files',
        #       'info_pp_to_hw_to_lvtata_nloqcd.html')).read()
        info_html_this = open(os.path.join(self.path, 'HTML', 'info.html')).read()
        #self.assertEqual(info_html_target, info_html_this)
        #open(pjoin(self.IOpath, "info.html"),"w").write(info_html_this)
        self.assertEqual(info_html_this.count('<TD> born </TD>'), 2)
        self.assertEqual(info_html_this.count('<TD> virt </TD>'), 2)
        self.assertEqual(info_html_this.count('<TD> real </TD>'), 6)
        self.assertEqual(info_html_this.count('<TR class=first>'), 2)
        self.assertEqual(info_html_this.count('<TR class=second>'), 8)


    def test_raise_invalid_path_hwpp(self):
        """test that an exception is raised when trying to shower with hwpp without
        having set the corresponding pahts"""
        cmd = os.getcwd()
        self.generate(['p p > e+ ve QED^2=4 QCD^2=0 [QCD] '], 'sm')
        card = open('%s/Cards/run_card_default.dat' % self.path).read()
        self.assertIn('HERWIG6   = parton_shower', card)
        card = card.replace('HERWIG6   = parton_shower', 'HERWIGPP   = parton_shower')
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card)
        self.cmd_line.exec_cmd('set  cluster_temp_path /tmp/ --no_save')
        self.do('generate_events -pf')
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))

        #no shower the file
        self.assertRaises(NLOCmd.aMCatNLOError, self.do, 'shower run_01 -f')


    def test_raise_invalid_path_py8(self):
        """test that an exception is raised when trying to shower with py8 without
        having set the corresponding pahts"""
        cmd = os.getcwd()
        self.generate(['p p > e+ ve QED^2=4 QCD^2=0 [QCD] '], 'sm')
        card = open('%s/Cards/run_card_default.dat' % self.path).read()
        self.assertIn('HERWIG6   = parton_shower', card)
        card = card.replace('HERWIG6   = parton_shower', 'PYTHIA8   = parton_shower')
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card)
        self.cmd_line.exec_cmd('set  cluster_temp_path /tmp/ --no_save')
        self.cmd_line.exec_cmd('set  pythia8_path None')
        self.do('generate_events -pf')
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))

        #no shower the file
        self.assertRaises(NLOCmd.aMCatNLOError, self.do, 'shower run_01 -f')




    def test_split_evt_gen(self):
        """test that the event generation splitting works"""
        cmd = os.getcwd()
        self.generate(['p p > e+ ve QED^2=4 QCD^2=0 [QCD] '], 'sm')
        card = open('%s/Cards/run_card_default.dat' % self.path).read()
        self.assertIn(' -1 = nevt_job', card)
        card = card.replace(' -1 = nevt_job', '500 = nevt_job')
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card)
        self.cmd_line.exec_cmd('set  cluster_temp_path /tmp/ --no_save')
        self.do('generate_events -pf')
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))


    def test_gen_evt_onlygen(self):
        """test that the event generation splitting works"""
        cmd = os.getcwd()
        self.generate(['p p > e+ ve [QCD]'], 'sm')
        card = open('%s/Cards/run_card_default.dat' % self.path).read()
        self.assertTrue( '10000 = nevents' in card)
        card = card.replace('10000 = nevents', '100 = nevents')
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card)
        self.cmd_line.exec_cmd('set  cluster_temp_path /tmp/ --no_save')
        self.do('generate_events -f')
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))

        # now re-generate with -o
        self.do('generate_events -of')
        self.assertTrue(os.path.exists('%s/Events/run_02/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/run_02_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/alllogs_2.html' % self.path))



    def test_madspin_ON_and_onshell_atNLO(self):

        nevents =20
        text = """
        set crash_on_error True --no_save
        generate p p > t t~ [QCD]
        output %s
        launch
        madspin=ON
        shower=OFF
        set nevents %s
        set mt 174
        set wt = 1.5
        decay t > w+ b
        decay t~ > w- b~
        launch -i
        decay_events run_01
        add madspin --replace_line="set spinmode.*" --after_line=banner set spinmode=onshell 
        """ % (self.path,nevents)
        
        interface = MGCmd.MasterCmd()
        interface.no_notification()
        
        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))
        
        # perform some basic check
        orig_lhe = pjoin(self.path,'Events','run_01','events.lhe.gz')
        lhe_on = pjoin(self.path,'Events','run_01_decayed_1','events.lhe.gz')
        lhe_onshell= pjoin(self.path,'Events','run_01_decayed_2','events.lhe.gz')
        
        self.assertTrue(lhe_on)
        mt =174
        wt = 1.5
        
        # check that original event has top onshell
        nb_event = 0
        for event in lhe_parser.EventFile(orig_lhe):
            nb_event +=1
            nb_final = 0
            m_inv_t = 0
            m_inv_tbar = 0
            for p in event:
                if p.status == -1:
                    continue
                elif p.status == 1:
                    nb_final += 1
                    if p.pdg == 6:
                        #if m_inv_t != 0:
                        #    self.assertTrue(False, 'two top decaying')
                        m_inv_t = p.mass
                        self.assertTrue( mt - 0.1*wt < m_inv_t < mt + 0.1*wt)
                    elif p.pdg == -6:
                        #if m_inv_t != 0:
                        #    self.assertTrue(False, 'two antitop decaying')
                        m_inv_tbar = p.mass
                        self.assertTrue( mt - 0.1*wt < m_inv_tbar < mt + 0.1*wt)
                    #else:
                    #    self.assertTrue(False, 'not top-antitop decaying')
            self.assertIn(nb_final, [2,3])
        self.assertEqual(nb_event, nevents)        
        
        
        # check that each events has the decay ON mode
        nb_event = 0
        for event in lhe_parser.EventFile(lhe_on):
            nb_event +=1
            nb_final = 0
            m_inv_t = 0
            m_inv_tbar = 0
            for p in event:
                if p.status == -1:
                    continue
                elif p.status == 1:
                    nb_final += 1
                else:
                    if p.pdg == 6:
                        #if m_inv_t != 0:
                        #    self.assertTrue(False, 'two top decaying')
                        m_inv_t = p.mass
                        self.assertTrue( mt - 15*wt < m_inv_t < mt + 15*wt)
                    elif p.pdg == -6:
                        #if m_inv_t != 0:
                        #    self.assertTrue(False, 'two antitop decaying')
                        m_inv_tbar = p.mass
                        self.assertTrue( mt - 15*wt < m_inv_tbar < mt + 15*wt)
                    else:
                        self.assertTrue(False, 'not top-antitop decaying')
            self.assertIn(nb_final, [4,5])
        self.assertEqual(nb_event, nevents)

        # check that each events has the decay ON mode
        nb_event = 0
        for event in lhe_parser.EventFile(lhe_onshell):
            nb_event +=1
            nb_final = 0
            m_inv_t = 0
            m_inv_tbar = 0
            for p in event:
                if p.status == -1:
                    continue
                elif p.status == 1:
                    nb_final += 1
                else:
                    if p.pdg == 6:
                        #if m_inv_t != 0:
                        #    self.assertTrue(False, 'two top decaying')
                        m_inv_t = p.mass
                        self.assertTrue( mt - 1 < m_inv_t < mt + 1)
                    elif p.pdg == -6:
                        #if m_inv_t != 0:
                        #    self.assertTrue(False, 'two antitop decaying')
                        m_inv_tbar = p.mass
                        self.assertTrue( mt - 1 < m_inv_tbar < mt + 1)
                    else:
                        self.assertTrue(False, 'not top-antitop decaying')
            self.assertIn(nb_final, [4,5])
        self.assertEqual(nb_event, nevents)        

        
    def test_madspin_LOonly(self):
        
        text = """
        set crash_on_error True --no_save
        generate p p > w+ [LOonly]
        output %s
        launch
        madspin=ON
        set nevents 10
        decay w+ > e+ ve
        launch -i
        decay_events run_01
        add madspin --replace_line="set spinmode.*" --after_line="banner" set spinmode=onshell 
        """ % self.path
        
        interface = MGCmd.MasterCmd()
        interface.no_notification()
        
        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))
        
     # perform some basic check
        lhe_on = pjoin(self.path,'Events','run_01_decayed_1','events.lhe.gz')
        lhe_onshell= pjoin(self.path,'Events','run_01_decayed_2','events.lhe.gz')
        
        self.assertTrue(lhe_on)        
        # check that each events has the decay ON mode
        nb_event = 0
        for event in lhe_parser.EventFile(lhe_on):
            nb_event +=1
            nb_final = 0
            m_inv_w = 0
            for p in event:
                if p.status == -1:
                    continue
                elif p.status == 1:
                    nb_final += 1
                else:
                    if p.pdg == 24:
                        if m_inv_w != 0:
                            self.assertTrue(False, 'two W')
                        m_inv_w = p.mass
                        self.assertTrue( 30 < m_inv_w < 150)
                    else:
                        misc.sprint(p.pdg, p.status)
                        self.assertTrue(False, 'not W decaying')
            self.assertIn(nb_final, [2])
        self.assertEqual(nb_event, 10)      
        
        self.assertTrue(lhe_onshell)        
        # check that each events has the decay ON mode
        nb_event = 0
        for event in lhe_parser.EventFile(lhe_onshell):
            nb_event +=1
            nb_final = 0
            m_inv_w = 0
            for p in event:
                if p.status == -1:
                    continue
                elif p.status == 1:
                    nb_final += 1
                else:
                    if p.pdg == 24:
                        if m_inv_w != 0:
                            self.assertTrue(False, 'two W')
                        m_inv_w = p.mass
                        self.assertTrue( 80 < m_inv_w < 81)
                    else:
                        self.assertTrue(False, 'not W decaying')
            self.assertIn(nb_final, [2])
        self.assertEqual(nb_event, 10)  
          

    def generate_production(self):
        """production"""
        
        if os.path.exists('%s/Cards/proc_card_mg5.dat' % self.path):
            proc_path = '%s/Cards/proc_card_mg5.dat' % self.path
            if 'p p > e+ ve QED^2=4 QCD^2=0 [QCD]' in open(proc_path).read():
                if files.is_uptodate(proc_path, min_time=self.loadtime):
                    if hasattr(self, 'cmd_line'):
                        self.cmd_line.exec_cmd('quit')
                    os.system('rm -rf %s/RunWeb' % self.path)
                    os.system('rm -rf %s/Events/run_01' % self.path)
                    os.system('rm -rf %s/Events/run_01_LO' % self.path)                        
                    self.cmd_line = NLOCmd.aMCatNLOCmdShell(me_dir= '%s' % self.path)
                    self.cmd_line.run_cmd('set automatic_html_opening False --no_save')

                    card = open('%s/Cards/run_card_default.dat' % self.path).read()
                    self.assertIn('10000 = nevents', card)
                    card = card.replace('10000 = nevents', '100 = nevents')
                    open('%s/Cards/run_card_default.dat' % self.path, 'w').write(card)
                    os.system('cp  %s/Cards/run_card_default.dat %s/Cards/run_card.dat'% (self.path, self.path))
                    os.system('cp  %s/Cards/shower_card_default.dat %s/Cards/shower_card.dat'% (self.path, self.path))
                    
                    return

        cmd = os.getcwd()
        self.generate(['p p > e+ ve QED^2=4 QCD^2=0 [QCD]'], 'loop_sm')
        self.assertEqual(cmd, os.getcwd())
        self.do('quit')
        card = open('%s/Cards/run_card_default.dat' % self.path).read()
        self.assertIn('10000 = nevents', card)
        card = card.replace('10000 = nevents', '100 = nevents')
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card)


 


    def test_amcantlo_script(self):
        """test that ./bin/aMCatNLO can be launched with some scripts.
        Check also that two runs run without border effects"""
        self.generate_production()
        script = "set notification_center False --no_save\n"
        script += "set automatic_html_opening False --no_save\n"
        script += "launch -p\n"
        script += "launch -p\n"
        open(pjoin(self.path, 'script.txt'), 'w').write(script)

        misc.call([pjoin('.','bin','aMCatNLO'), 'script.txt'], cwd='%s' % self.path,
                stdout = open(os.devnull, 'w'))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_02/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/run_02_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_02/alllogs_2.html' % self.path))


    def notest_eft_running_nlo(self):
        """check that  gives the correct result"""
        
        mg_cmd = MGCmd.MasterCmd()
        mg_cmd.no_notification()
        mg_cmd.run_cmd('set automatic_html_opening False --save')
        mg_cmd.run_cmd('import model %s/tests/input_files/SMEFTatNLO_running-NLO' % madgraph.MG5DIR)
        mg_cmd.run_cmd('generate p p > t t~ NP=2 NP^2==2 QCD=2 QED=0 [QCD]')
        mg_cmd.run_cmd('output %s/'% self.path)
        #self.cmd_line = MECmd.MadEventCmdShell(me_dir=  self.path)
        #self.cmd_line.no_notification()
        #self.cmd_line.exec_cmd('set automatic_html_opening False')
        
        #check validity of the default run_card
        run_card = banner.RunCardNLO(pjoin(self.path, 'Cards','run_card.dat'))

        #f = open(pjoin(self.path, 'Cards','run_card.dat'),'r')
        #print(f.read())
        self.assertTrue('fixed_extra_scale' not in run_card.user_set)
        self.assertTrue('mue_ref_fixed' in run_card.user_set)
        self.assertTrue('mue_over_ref' not in  run_card.user_set)
        self.assertTrue(run_card['fixed_extra_scale'])
        
        

        cwd = os.getcwd()
        import subprocess
        if logging.getLogger('madgraph').level <= 20:
            stdout=None
            stderr=None
        else:
            devnull =open(os.devnull,'w')
            stdout=devnull
            stderr=devnull

        if logging.getLogger('madgraph').level > 20:
            stdout = devnull
        else:
            stdout= None


        subprocess.call([pjoin(self.path, 'bin','generate_events'),'aMC@LO', '-p', '-f'],            
                         cwd=pjoin(self.path),
                         stdout=stdout,stderr=stdout)



        results = self.load_result('run_01_LO')[0]


        val1 = results['cross']
        err1 = results['error']

        target = 617.7542699925228 # THIS IS NOT PURE INTERFERENCE...
        self.assertTrue(abs(val1 - target) / err1 < 1., 'large diference between %s and %s +- %s'%
                        (target, val1, err1))


    def test_generate_events_lo_hw6_stdhep(self):
        """test the param_card created is correct"""
        
        self.generate_production()
        cmd = """generate_events aMC@LO
                 set nevents 100
                 """
        open('/tmp/mg5_cmd','w').write(cmd)
        self.cmd_line.import_command_file('/tmp/mg5_cmd')
        #self.do('import command %s/mg5_cmd')
        #self.do('generate_events LO -f')        
        
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/run_01_LO_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_2.html' % self.path))
        # test the hep event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/events_HERWIG6_0.hep.gz' % self.path))
        # sanity check on the size
        self.assertGreater(
            os.path.getsize('%s/Events/run_01_LO/events_HERWIG6_0.hep.gz' % self.path),
            os.path.getsize('%s/Events/run_01_LO/events.lhe.gz' % self.path)
        )
        


    def test_generate_events_lo_py6_stdhep(self):
        """test the param_card created is correct"""
        
        self.generate_production()

        #change to py6
        card = open('%s/Cards/run_card.dat' % self.path).read()
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card.replace('HERWIG6', 'PYTHIA6Q'))       
        self.do('generate_events aMC@LO -f')        
        
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/run_01_LO_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_2.html' % self.path))
        # test the hep event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/events_PYTHIA6Q_0.hep.gz' % self.path))
        # sanity check on the size
        self.assertGreater(
            os.path.getsize('%s/Events/run_01_LO/events_PYTHIA6Q_0.hep.gz' % self.path),
            os.path.getsize('%s/Events/run_01_LO/events.lhe.gz' % self.path)
        )



    def test_generate_events_nlo_hw6_split(self):
        """test the param_card created is correct"""
        
        cmd = os.getcwd()
        self.generate(['p p > e+ ve QED^2=4 QCD^2=0 [QCD]'], 'loop_sm')
        self.assertEqual(cmd, os.getcwd())
        #change splitevent generation
        card = open('%s/Cards/run_card.dat' % self.path).read()
        open('%s/Cards/run_card.dat' % self.path, 'w').write(card.replace(' -1 = nevt_job', ' 1000 = nevt_job'))
        self.do('generate_events aMC@NLO -fp')        
        
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/events.lhe.gz' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_2.html' % self.path))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))
        

    def test_calculate_xsect_nlo(self):
        """test the param_card created is correct"""
        
        self.generate_production()
        
        self.do('calculate_xsect NLO -f')        
        
        # test the plot file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/MADatNLO.HwU' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))


    def test_calculate_xsect_lo(self):
        """test the param_card created is correct"""
        
        self.generate_production()
        
        self.do('calculate_xsect LO -f')        
        
        # test the plot file exists
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/MADatNLO.HwU' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/run_01_LO_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/alllogs_1.html' % self.path))

    
    def test_amcatnlo_from_file(self):
        """ """
        
        cwd = os.getcwd()
        try:
            os.remove('%s/test.log' % self.tmpdir)
        except Exception as error:
            pass
        import subprocess
        
        stdout = open('%s/test.log' % self.tmpdir,'w')
        if logging.getLogger('madgraph').level <= 20:
            stderr=None
        else:
            devnull =open(os.devnull,'w')
            stderr=devnull

            
        subprocess.call([sys.executable, pjoin(_file_path, os.path.pardir,'bin','mg5_aMC'), 
                         pjoin(_file_path, 'input_files','test_amcatnlo')],
                         cwd=self.tmpdir,
                        stdout=stdout,stderr=stderr)

        stdout.close()
        text = open('%s/test.log' % self.tmpdir,'r').read()
        if logging.getLogger('madgraph').level <= 20:
            print(text)
        data = text.split('\n')
        for i,line in enumerate(data):
            if 'Summary:' in line:
                break
        #      Run at p-p collider (6500.0 + 6500.0 GeV)
        self.assertIn('Run at p-p collider (6500.0 + 6500.0 GeV)', data[i+2])
        #      Total cross-section: 1.249e+03 +- 3.2e+00 pb        
        cross_section = data[i+4]
        cross_section = float(cross_section.split(':')[1].split('+-')[0])
        try:
            self.assertAlmostEqual(6675.0, cross_section,delta=50)
        except TypeError:
            self.assertTrue(cross_section < 6750.0 and cross_section > 6650.0)

        #      Number of events generated: 10000        
        self.assertIn('Number of events generated: 100', data[i+3])


    def load_result(self, run_name='run_01'):

        import madgraph.iolibs.save_load_object as save_load_object
        import madgraph.madevent.gen_crossxhtml as gen_crossxhtml

        result = save_load_object.load_from_file('%s/HTML/results.pkl' % self.path)
        return result[run_name]


    def test_generate_taggedph_nloew(self):
        """test the param_card created is correct"""
        

        text = """
        import model loop_qcd_qed_sm_Gmu-a0
        generate u u~ > !a! !a! [QED]
        output %s
        launch NLO
        set lepphreco False
        set quarkphreco False
        """ % (self.path)
        
        interface = MGCmd.MasterCmd()
        interface.no_notification()
        
        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        
        
        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)

        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))
        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/run_01_tag_1_banner.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_0.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/res_1.txt' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_0.html' % self.path))
        self.assertTrue(os.path.exists('%s/Events/run_01/alllogs_1.html' % self.path))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))


    def test_generate_eeww_nlo_emela_noph(self):
        """ we will test the generation of NLO EW for w+w- production,
        using the gmu ren. scheme and the delta scheme for the factorisation 
        of IR singularities
        The expected generation/compilation/running time is about 5 mins with 8 cores
        """
        
        text = """
        import model loop_qcd_qed_sm_Gmu
        generate e+ e- > w+ w- [QED]
        output %s
        launch NLO
        set ebeam1 250
        set ebeam2 250
        set lpp1 -3
        set lpp2 3
        set fixed_ren_scale True
        set fixed_fac_scale True
        set req_acc_FO 0.0010
        set muf_ref_fixed 500
        set mur_ref_fixed 500
        set pdlabel emela
        set lhaid 137009
        set photons_from_lepton False
        set mw 80.379
        set mz 91.1876
        set wt 0
        set ww 0
        set wz 0
        set wh 0
        """ % (self.path)

        interface = MGCmd.MasterCmd()
        interface.no_notification()

        # skip if eMELA is not known to MG5_aMC
        if not interface.options['eMELA']:
            self.skipTest("Skipping test, eMELA not available")

        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        # read the cross section
        summary = open('%s/Events/run_01/summary.txt' % self.path).read()
        xsect = summary.split("Total cross section:")[1].split(" +-")[0]
        error = summary.split("Total cross section:")[1].split(" +-")[1].split()[0]

        # check within 3 sigma
        self.assertAlmostEqual(7.513, float(xsect), delta=3*float(error))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))


    def test_generate_eeww_nlo_emela_wph(self):
        """ we will test the generation of NLO EW for w+w- production,
        using the gmu ren. scheme and the delta scheme for the factorisation 
        of IR singularities.
        Photon in the initial state is included.
        The expected generation/compilation/running time is about 5 mins with 8 cores
        """
        
        text = """
        import model loop_qcd_qed_sm_Gmu
        define ep = e+ a
        define em = e- a
        generate ep em > w+ w- [QED]
        output %s
        launch NLO
        set ebeam1 250
        set ebeam2 250
        set lpp1 -3
        set lpp2 3
        set fixed_ren_scale True
        set fixed_fac_scale True
        set req_acc_FO 0.0010
        set muf_ref_fixed 500
        set mur_ref_fixed 500
        set pdlabel emela
        set lhaid 137009
        set photons_from_lepton True
        set mw 80.379
        set mz 91.1876
        set wt 0
        set ww 0
        set wz 0
        set wh 0
        """ % (self.path)

        interface = MGCmd.MasterCmd()
        interface.no_notification()

        # skip if eMELA is not known to MG5_aMC
        if not interface.options['eMELA']:
            self.skipTest("Skipping test, eMELA not available")

        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        # read the cross section
        summary = open('%s/Events/run_01/summary.txt' % self.path).read()
        xsect = summary.split("Total cross section:")[1].split(" +-")[0]
        error = summary.split("Total cross section:")[1].split(" +-")[1].split()[0]

        # check within 3 sigma
        self.assertAlmostEqual(7.694, float(xsect), delta=3*float(error))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))


    def test_generate_eett_nlo_emela_bs(self):
        """ we will test the generation of NLO EW for ttbar production,
        using the alphamz ren. scheme and the delta scheme for the factorisation 
        of IR singularities. (Actually, the amz scheme will be transformed 
        internally to the MSbar one)
        Beamstrahlung is included.
        The expected generation/compilation/running time is about 5 mins with 8 cores
        """
        
        text = """
        import model loop_qcd_qed_sm
        generate e+ e- > t t~ [QED]
        output %s
        launch NLO
        set ebeam1 250
        set ebeam2 250
        set lpp1 -3
        set lpp2 3
        set fixed_ren_scale True
        set fixed_fac_scale True
        set req_acc_FO 0.0010
        set muf_ref_fixed 500
        set mur_ref_fixed 500
        set pdlabel emela
        set lhaid 137010
        set photons_from_lepton False
        set mw 80.379
        set mz 91.1876
        set mt 173.3
        set wt 0
        set ww 0
        set wz 0
        set wh 0
        """ % (self.path)

        interface = MGCmd.MasterCmd()
        interface.no_notification()

        # skip if eMELA is not known to MG5_aMC
        if not interface.options['eMELA']:
            self.skipTest("Skipping test, eMELA not available")

        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        # read the cross section
        summary = open('%s/Events/run_01/summary.txt' % self.path).read()
        xsect = summary.split("Total cross section:")[1].split(" +-")[0]
        error = summary.split("Total cross section:")[1].split(" +-")[1].split()[0]

        # check within 3 sigma
        self.assertAlmostEqual(5.161e-1, float(xsect), delta=3*float(error))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))


    def test_generate_eett_lo_emela_clusterpath(self):
        """ we will test the generation of LO EW for ttbar production,
        using the alphamz ren. scheme and the delta scheme for the factorisation 
        of IR singularities. (Actually, the amz scheme will be transformed 
        internally to the MSbar one)
        We will set a cluster_temp_path 
        """

        
        text = """
        import model loop_qcd_qed_sm
        set cluster_temp_path /tmp/ --no_save
        generate e+ e- > t t~ [LOonly=QED]
        output %s
        launch LO --multicore
        set ebeam1 250
        set ebeam2 250
        set lpp1 -3
        set lpp2 3
        set fixed_ren_scale True
        set fixed_fac_scale True
        set req_acc_FO 0.010
        set muf_ref_fixed 500
        set mur_ref_fixed 500
        set pdlabel emela
        set lhaid 137010
        set photons_from_lepton False
        set mw 80.379
        set mz 91.1876
        set mt 173.3
        set wt 0
        set ww 0
        set wz 0
        set wh 0
        """ % (self.path)

        interface = MGCmd.MasterCmd()
        interface.no_notification()

        # skip if eMELA is not known to MG5_aMC
        if not interface.options['eMELA']:
            self.skipTest("Skipping test, eMELA not available")

        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01_LO/summary.txt' % self.path))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01_LO', 'results.html'))



    def test_generate_eett_nlo_qcd_noisr(self):
        """ we will test the generation of NLO QCD for ttbar production,
        (without ISR, fixed beam energy
        """
        
        text = """
        import model loop_sm-no_b_mass
        generate e+ e- > t t~ [QCD]
        output %s
        launch NLO
        set ebeam1 500
        set ebeam2 500
        set lpp1 0 
        set lpp2 0
        """ % (self.path)

        interface = MGCmd.MasterCmd()
        interface.no_notification()

        open(pjoin(self.tmpdir,'cmd'),'w').write(text)
        os.system('rm -rf %s/RunWeb' % self.path)
        os.system('rm -rf %s/Events/run_*' % self.path)
        interface.exec_cmd('import command %s' % pjoin(self.tmpdir, 'cmd'))

        # test the lhe event file exists
        self.assertTrue(os.path.exists('%s/Events/run_01/summary.txt' % self.path))
        # read the cross section
        summary = open('%s/Events/run_01/summary.txt' % self.path).read()
        xsect = summary.split("Total cross section:")[1].split(" +-")[0]
        error = summary.split("Total cross section:")[1].split(" +-")[1].split()[0]

        # check within 3 sigma
        self.assertAlmostEqual(1.745e-1, float(xsect), delta=3*float(error))

        check_html_page(self, pjoin(self.path, 'crossx.html'))
        check_html_page(self, pjoin(self.path, 'HTML', 'run_01', 'results.html'))
