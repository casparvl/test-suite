"""
This test is adapted from the BLAS test included in the BLIS v1.1 sources at
https://github.com/flame/blis/tree/1.1/test/3

Customizations to the original BLAS test:
- adapted and simplified Makefile for FlexiBLAS support
- custom simplified run.sh script

Notes:
- a buildenv module, which includes FlexiBLAS, and BLIS module must be loaded to run the test,
  even if BLIS or OpenBLAS are not used. the buildenv module is automatically added by eessi_mixin
  by setting "require_buildenv_module = True"
- by default OpenBLAS is already included as a dependency of FlexiBLAS.
  this means that, if multiple OpenBLAS modules are present in the same toolchain,
  the OpenBLAS versions not included in FlexiBLAS may fail to load due to a version conflict.
  to fix this, you may want to run: `export LMOD_DISABLE_SAME_NAME_AUTOSWAP=no` before running the test.
- BLAS modules with hyphens in the version string are not supported.

Supported tags in this ReFrame test (in addition to the common tags):
- BLAS implementation: `openblas`, `blis`, `aocl-blas`, `imkl`
- `CI` tag: runs only openblas
"""


import reframe as rfm
from reframe.core.builtins import parameter, run_after, run_before, sanity_function
from reframe.core.logging import getlogger
import reframe.utility.sanity as sn

from eessi.testsuite.constants import COMPUTE_UNITS, DEVICE_TYPES, SCALES
from eessi.testsuite.eessi_mixin import EESSI_Mixin
from eessi.testsuite.utils import find_modules, select_matching_modules, log


def multi_thread_scales():
    """Scales for multi-threaded BLAS tests"""
    return parameter([
        k for (k, v) in SCALES.items()
        if v['num_nodes'] == 1
    ])


def get_blas_modules(blas_name):
    """
    Find available blas_name module_infos with (most recent) matching BLIS module

    Returns: If blas_name is 'BLIS', returns the BLIS module_infos.
             Otherwise, returns a list of tuples (syspart, env, [blas, blis]):
             each inner list has the `blas_name` module as first item, and the
             matching BLIS module as second item.  The BLIS module must be
             second to avoid segmentation fault for AOCL-BLAS.
    """
    blas_module_infos = list(find_modules(rf'^{blas_name}$'))
    if blas_name == 'BLIS':
        return [(x, y, [z]) for x, y, z in blas_module_infos]

    ml_lists = []
    blis_module_infos = list(find_modules(r'^BLIS$'))

    for blas_mod_info in blas_module_infos:
        matching_blis_infos = select_matching_modules(blis_module_infos, blas_mod_info)
        if not matching_blis_infos:
            msg = f'Skipping BLAS module info {blas_mod_info}: no matching BLIS module found.'
            getlogger().warning(msg)
            continue
        # assume the last BLIS module is the most recent one (find_modules sorts them)
        blis = matching_blis_infos[-1][-1]
        syspart, env, blas = blas_mod_info
        ml_lists.append((syspart, env, [blas, blis]))

    return ml_lists


def get_imkl_modules():
    """
    Find available imkl modules and (latest) BLIS module
    Only imkl modules with SYSTEM toolchain are used

    Returns: a list of tuples (syspart, env, [imkl, blis]):
             each inner list has the imkl module as first item,
             and the most recent BLIS module as second item.
    """
    ml_lists = []

    blis_module_infos = list(find_modules(r'^BLIS$'))
    if not blis_module_infos:
        log('no BLIS module found')
        return ml_lists
    blis = blis_module_infos[-1][-1]

    # skip imkl modules with a toolchain other than SYSTEM (i.e. no toolchain in the module version)
    imkl_module_infos = list(find_modules(r'^imkl/[^-]*$', name_only=False))
    for imkl_mod_info in imkl_module_infos:
        syspart, env, imkl = imkl_mod_info
        ml_lists.append((syspart, env, [imkl, blis]))

    return ml_lists


class EESSI_BLAS_base(rfm.RunOnlyRegressionTest):
    "base BLAS test"
    device_type = DEVICE_TYPES.CPU
    compute_unit = COMPUTE_UNITS.NODE
    time_limit = '10m'
    readonly_files = ['Makefile', 'run.sh', 'test_gemm.c', 'test_hemm.c', 'test_herk.c', 'test_trmm.c', 'test_trsm.c',
                      'test_utils.c', 'test_utils.h']
    env_vars = {
        'CFLAGS': '"-O2 -ftree-vectorize -march=native -fno-math-errno -g"',  # default CFLAGS used by EasyBuild
    }
    executable = './run.sh'
    nrepeats = '5'
    dts = ['s', 'd', 'c', 'z']
    ops = ['gemm_nn', 'hemm_ll', 'herk_ln', 'trmm_llnn', 'trsm_runn']
    size = ['200', '2000', '200']
    require_buildenv_module = True
    threading = 'mt'
    launcher = 'local'  # No MPI module is loaded in this test

    def required_mem_per_node(self):
        return self.num_cpus_per_task * 100 + 250

    @run_after('init')
    def set_prerun_cmds(self):
        """Set prerun_cmds"""
        self.prerun_cmds = [f'make flexiblas-{self.threading}']

    @run_after('init')
    def set_executable_opts(self):
        """Set executable_opts"""
        self.executable_opts = [
            self.threading,
            self.nrepeats,
            '"{}"'.format(' '.join(self.size)),
            '"{}"'.format(' '.join(self.dts)),
            '"{}"'.format(' '.join(self.ops)),
        ]

    @run_after('init')
    def set_flexiblas_blas_lib(self):
        """Set FLEXIBLAS environment variable to selected BLAS lib"""
        self.env_vars.update({
            'FLEXIBLAS': self.flexiblas_blas_lib,
        })

    @sanity_function
    def assert_sanity(self):
        assert_backend = sn.assert_not_found(
            r'BLAS backend\s+\S+\s+not found',
            self.stderr,
            f'FlexiBLAS BLAS backend not found ({self.flexiblas_blas_lib})'
        )
        asserts_result = [
            sn.assert_found(r"data\S+_flexiblas", f'output/{x}{y}_flexiblas.m', f'output/{x}{y}_flexiblas.m')
            for x in self.dts for y in self.ops
        ]
        return sn.all([assert_backend] + asserts_result)

    def _extract_perf(self, dt, op):
        return sn.extractsingle(
            rf'^data\S+_flexiblas.*{self.size[1]}\s+(?P<perf>\S+)\s+\];',
            f'output/{dt}{op}_flexiblas.m',
            1, float
        )

    @run_before('performance')
    def set_perf_vars(self):
        """Set performance variables"""
        self.perf_variables.update({
            f'{x}{y.split("_")[0]}': sn.make_performance_function(self._extract_perf(x, y), 'GFLOPS')
            for x in self.dts for y in self.ops
        })


@rfm.simple_test
class EESSI_BLAS_OpenBLAS_mt(EESSI_BLAS_base, EESSI_Mixin):
    "multi-threaded OpenBLAS test"

    scale = multi_thread_scales()
    module_info = parameter(get_blas_modules('OpenBLAS'))
    flexiblas_blas_lib = 'openblas'
    tags = {'openblas'}
    is_ci_test = True
    thread_binding = 'compact'


@rfm.simple_test
class EESSI_BLAS_AOCLBLAS_mt(EESSI_BLAS_base, EESSI_Mixin):
    "multi-threaded AOCL-BLAS test"

    scale = multi_thread_scales()
    module_info = parameter(get_blas_modules('AOCL-BLAS'))
    flexiblas_blas_lib = 'aocl_mt'
    tags = {'aocl-blas'}
    thread_binding = 'compact'


@rfm.simple_test
class EESSI_BLAS_imkl_mt(EESSI_BLAS_base, EESSI_Mixin):
    "multi-threaded imkl test"

    scale = multi_thread_scales()
    module_info = parameter(get_imkl_modules())
    flexiblas_blas_lib = 'imkl'
    tags = {'imkl'}
    thread_binding = 'compact'


@rfm.simple_test
class EESSI_BLAS_BLIS_mt(EESSI_BLAS_base, EESSI_Mixin):
    "multi-threaded BLIS test"

    scale = multi_thread_scales()
    module_info = parameter(get_blas_modules('BLIS'))
    flexiblas_blas_lib = 'blis'
    tags = {'blis'}
    thread_binding = 'compact'
