"""
This test was adapted from https://github.com/vscentrum/vsc-test-suite/tree/main/tests/apps/python,
originally created by Michele Pugno (UAntwerpen)

Tested matrix operations with NumPy:
- dot product
- singular value decompostion (SVD)
- cholesky decomposition
- eigen decomposition
- inversion
"""
import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.builtins import parameter, run_after, run_before, sanity_function, variable
from reframe.core.runtime import valid_sysenv_comb

from eessi.testsuite.constants import COMPUTE_UNITS, DEVICE_TYPES, SCALES
from eessi.testsuite.eessi_mixin import EESSI_Mixin
# from eessi.testsuite.utils import find_modules
from reframe.utility import find_modules
from eessi.testsuite.constants import *


@rfm.simple_test
class EESSI_ModuleFinder2(rfm.RunOnlyRegressionTest):
    descr = 'Test matrix operations with NumPy'
    executable = './np_ops.py'
    time_limit = '30m'
    readonly_files = ['np_ops.py']
    # module_name = parameter(find_modules('SciPy-bundle'))
    module_info = parameter(find_modules('SciPy-bundle'))
    device_type = DEVICE_TYPES.CPU
    compute_unit = COMPUTE_UNITS.NODE
    scale = parameter([
        k for (k, v) in SCALES.items()
        if v['num_nodes'] == 1
    ])
    thread_binding = 'compact'
    launcher = 'local'  # no MPI module is loaded in this test

    matrix_size = variable(str, value='8192')
    iterations = variable(str, value='4')
    iterations_eigen = variable(str, value='1')

    is_ci_test = True

    @run_after('init', always_last=True)
    def apply_module_info(self):
        s, e, m = self.module_info
        print(f"SYSTEM {s}")
        # valid_partitions = [part.fullname for part in valid_sysenv_comb(['+gpu'], e)]
        # print(f"valid_partitions: {valid_partitions}")
        # if s in valid_partitions:
        #     self.valid_systems = [s]
        # else:
        #     self.valid_systems = []
        self.valid_systems = [s + ' +gpu']
        # self.valid_systems = [s + ' +cpu']
        # self.valid_systems = ['+cpu']
        # self.valid_systems = ['foo:bar']
        # self.valid_systems = [s + ' +%s' % FEATURES.GPU]
        # self.valid_systems = ['+%s ' % FEATURES.CPU + s]
        # self.valid_systems = ['snellius:rome +1_node +cpu']
        # self.valid_systems = ['snellius:* +bar +foo']
        # self.valid_systems = ['snellius:* +bar']
        # self.valid_systems = ['snellius:* +foo']
        # self.valid_systems = [f"+{s.replace(':','')} +gpu"]
        self.valid_prog_environs = [e]
        self.modules = [m]
        self.tags = {self.scale}

    def required_mem_per_node(self):
        """
        Minimum required memory for this test
        This value is based on the default matrix size, and may have to be adapted for non-default matrix sizes.
        """
        return self.num_cpus_per_task * 100 + 2500

    def perf_func(self, perf_name, perf_regex):
        return perf_name, sn.make_performance_function(sn.extractsingle(perf_regex, self.stdout, 1, float), 's')

    @run_after('init')
    def set_executable_opts(self):
        """Set executable_opts"""
        self.executable_opts = [
            '--matrix-size', self.matrix_size,
            '--iterations', self.iterations,
            '--iterations-eigen', self.iterations_eigen,
        ]

    @sanity_function
    def assert_numpy_found(self):
        """Assert that NumPy is found"""
        return sn.assert_found(r'NumPy version:\s+\S+', self.stdout)

    @run_before('performance')
    def set_perf_vars(self):
        """Set performance variables"""
        self.perf_variables.update([
            self.perf_func('dot', r'^Dotted two \S* matrices in\s+(?P<dot>\S+)\s+s'),
            self.perf_func('svd', r'^SVD of a \S* matrix in\s+(?P<svd>\S+)\s+s'),
            self.perf_func('cholesky', r'^Cholesky decomposition of a \S* matrix in\s+(?P<cholesky>\S+)\s+s'),
            self.perf_func('eigendec', r'^Eigendecomposition of a \S* matrix in\s+(?P<eigendec>\S+)\s+s'),
            self.perf_func('inv', r'^Inversion of a \S* matrix in\s+(?P<inv>\S+)\s+s'),
        ])
