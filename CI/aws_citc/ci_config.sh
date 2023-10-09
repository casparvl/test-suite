# Configurable items
TEMPDIR=$(mktemp --directory --tmpdir=/tmp  -t rfm.XXXXXXXXXX)
TAGS="--tag CI --tag 1_node|2_nodes"
# The hpctestlib as well as the reframe command will be based on this version
# May be adapted later to simply use reframe from the EESSI software stack
REFRAME_VERSION=4.3.2
EESSI_VERSION=2023.06

# ReFrame configuration
export RFM_CONFIG_FILES="${TEMPDIR}/test-suite/config/aws_citc.py"
export RFM_CHECK_SEARCH_PATH="${TEMPDIR}/test-suite/eessi/testsuite/tests/"
export RFM_CHECK_SEARCH_RECURSIVE=1
export RFM_PREFIX="${HOME}/reframe_CI_runs"
