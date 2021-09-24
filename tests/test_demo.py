# Copyright 2021 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess
import sys
import unittest
import math

import dimod

import demo

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestSmoke(unittest.TestCase):
    @unittest.skipIf(os.getenv('SKIP_INT_TESTS'), "Skipping integration test.")
    def test_smoke(self):
        """Run demo.py and check that nothing crashes"""

        demo_file = os.path.join(project_dir, 'demo.py')
        subprocess.check_output([sys.executable, demo_file])

class TestDemo(unittest.TestCase):
    def test_num_vars(self):
        """Test BQM characteristics for demo instance"""

        num_pumps = 7
        time = list(range(24))
        power = [15, 37, 33, 33, 22, 33, 22]
        costs = [169]*7 + [283]*6 + [169]*3 + [336]*5 + [169]*3
        flow = [75, 133, 157, 176, 59, 69, 120]
        demand = [44.62, 31.27, 26.22, 27.51, 31.50, 46.18, 69.47, 100.36, 131.85, 
                    148.51, 149.89, 142.21, 132.09, 129.29, 124.06, 114.68, 109.33, 
                    115.76, 126.95, 131.48, 138.86, 131.91, 111.53, 70.43]
        v_init = 550
        v_min = 523.5
        v_max = 1500 
        c3_gamma = 0.00052   

        bqm, _ = demo.build_bqm(num_pumps, time, power, costs, flow, demand, v_init, v_min, v_max, c3_gamma)
        bin_vars = num_pumps*len(time)
        c1_vars = num_pumps*math.ceil(math.log(len(time), 2))
        c2_vars = len(time)*math.ceil(math.log(num_pumps, 2))
        c3_vars = len(time)*math.ceil(math.log(v_max*100 - v_min*100 + 1, 2))

        self.assertEqual(bqm.num_variables, bin_vars+c1_vars+c2_vars+c3_vars)
    
    def test_small_case(self):
        """Test solution quality of small case with exact solver"""

        num_pumps = 2
        time = list(range(2))
        power = [1, 2]
        costs = [1, 2]
        flow = [2, 4]
        demand = [2, 2]
        v_init = 1
        v_min = 0.5
        v_max = 1.5
        c3_gamma = 0.01

        bqm, x = demo.build_bqm(num_pumps, time, power, costs, flow, demand, v_init, v_min, v_max, c3_gamma)

        sampler = dimod.ExactSolver()
        sampleset = sampler.sample(bqm)
        sample = sampleset.first.sample

        self.assertEqual(sample[x[0][0]], 1)
        self.assertEqual(sample[x[0][1]], 1)
        self.assertEqual(sample[x[1][0]], 0)
        self.assertEqual(sample[x[1][1]], 0)

