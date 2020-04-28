import json
import copy
import os
from ruamel.yaml import YAML
from Tests.scripts.configure_tests import get_test_list, get_modified_files, RANDOM_TESTS_NUM, TestConf, \
    create_filter_envs_file
import demisto_sdk.commands.common.tools as demisto_sdk_tools

with open('Tests/scripts/infrastructure_tests/tests_data/mock_id_set.json', 'r') as mock_id_set_f:
    MOCK_ID_SET = json.load(mock_id_set_f)
with open('Tests/scripts/infrastructure_tests/tests_data/mock_conf.json', 'r') as mock_conf_f:
    MOCK_CONF = json.load(mock_conf_f)


class TestUtils(object):
    __test__ = False

    @staticmethod
    def save_yaml(path, data):
        ryaml = YAML()
        ryaml.allow_duplicate_keys = True

        with open(path, 'w') as f:
            ryaml.dump(data, f)

    @staticmethod
    def create_integration(name, with_commands=None):
        mock_integration = demisto_sdk_tools.get_yaml(
            'Tests/scripts/infrastructure_tests/tests_data/mock_integrations/fake_integration.yml')

        mock_integration['commonfields']['id'] = name
        mock_integration['name'] = name
        mock_integration['display'] = name

        save_path = os.path.join('Tests/scripts/infrastructure_tests/tests_data/mock_integrations', name + '.yml')
        TestUtils.save_yaml(save_path, mock_integration)

        commands = [
            "fake-command"
        ]
        if with_commands:
            commands = with_commands

        integration = {
            'path': save_path,
            'id_set': {
                name: {
                    "name": name,
                    "fromversion": "4.1.0",
                    "toversion": "5.4.9",
                    "file_path": save_path,
                    "commands": commands
                }
            }
        }

        return integration

    @staticmethod
    def create_test_playbook(name, with_scripts=None, with_integration_commands=None):
        test_playbook_default = demisto_sdk_tools.get_yaml(
            'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/fake_test_playbook.yml')

        test_playbook_default['id'] = name
        test_playbook_default['name'] = name

        file_path = os.path.join('Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks', name + '.yml')
        TestUtils.save_yaml(file_path, test_playbook_default)

        playbook_id_set = {
            name: {
                "name": name,
                "file_path": file_path
            }
        }
        if with_scripts:
            playbook_id_set[name]['implementing_scripts'] = with_scripts

        if with_integration_commands:
            playbook_id_set[name]['command_to_integration'] = with_integration_commands

        test_playbook = {
            'path': file_path,
            'id_set': playbook_id_set
        }
        return test_playbook

    @staticmethod
    def mock_get_modified_files(mocker, modified_files_list, is_conf_json=False):
        return mocker.patch('Tests.scripts.configure_tests.get_modified_files',
                            return_value=create_get_modified_files_ret(
                                modified_files_list=modified_files_list,
                                is_conf_json=is_conf_json
                            ))

    @staticmethod
    def mock_run_command(mocker, on_command, return_value):
        def on_run_command(*args):
            command = args[0]
            if command == on_command:
                return return_value

            return ''

        mock = mocker.patch('demisto_sdk.commands.common.tools.run_command')
        mock.side_effect = on_run_command
        return mock

    @staticmethod
    def create_tests_conf(with_test_configuration=None):
        with open('Tests/scripts/infrastructure_tests/tests_data/mock_conf.json', 'r') as mock_conf_f:
            conf = json.load(mock_conf_f)

        if with_test_configuration:
            conf['tests'].append(with_test_configuration)

        return TestConf(conf)

    @staticmethod
    def create_id_set(with_integration=None, with_test_playbook=None):
        with open('Tests/scripts/infrastructure_tests/tests_data/mock_id_set.json', 'r') as mock_id_set_f:
            id_set = json.load(mock_id_set_f)

        if with_integration:
            id_set['integrations'].append(with_integration)

        if with_test_playbook:
            id_set['TestPlaybooks'].append(with_test_playbook)

        return id_set

    @staticmethod
    def delete_files(files):
        for f in files:
            if isinstance(f, dict) and 'path' in f:
                file_path = f['path']
            else:
                file_path = f

            if os.path.exists(file_path):
                os.remove(file_path)


class TestChangedPlaybook:
    TEST_ID = 'Calculate Severity - Standard - Test'
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = "M Packs/Legacy/Playbooks/playbook-Calculate_Severity_By_Highest_DBotScore.yml"

    def test_changed_runnable_test__unmocked_get_modified_files(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert filterd_tests == {self.TEST_ID}


class TestChangedTestPlaybook:
    TEST_ID = 'EWSv2_empty_attachment_test'
    # points at a real file. if that file will change path the test should fail
    GIT_DIFF_RET = "M TestPlaybooks/playbook-EWSv2_empty_attachment_test.yml"

    def test_changed_runnable_test__unmocked_get_modified_files(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert filterd_tests == {self.TEST_ID}

    def test_changed_runnable_test__mocked_get_modified_files(self, mocker):
        # fake_test_playbook is fromversion 4.1.0 in playbook file
        test_id = 'fake_test_playbook'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/fake_test_playbook.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('4.1.0', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1

    def test_changed_unrunnable_test__integration_fromversion(self, mocker):
        """
        Given:
            - fake_test_playbook integration is fromversion 4.1.0 in integration file
            - two_before_ga is '4.0.0'
            - one_before_ga is '4.1.0'
            - ga is '4.5.0'
        When:
            - running get_test_list
            - running create_filter_envs_file
        Then:
            - Create test list with fake_test_playbook
            - Create filter_envs.json file with Demisto two before GA False

        """
        two_before_ga = '4.0.0'
        one_before_ga = '4.1.0'
        ga = '4.5.0'
        test_id = 'fake_test_playbook'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/fake_test_playbook.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list(two_before_ga, get_modified_files_ret, mocker)
        assert test_id in filterd_tests
        assert len(filterd_tests) == 1

        create_filter_envs_file(filterd_tests, two_before_ga, one_before_ga, ga, TestConf(MOCK_CONF), MOCK_ID_SET)
        with open("./Tests/filter_envs.json", "r") as filter_envs_file:
            filter_envs = json.load(filter_envs_file)
        assert filter_envs.get('Server Master') is True
        assert filter_envs.get('Demisto PreGA') is True
        assert filter_envs.get('Demisto two before GA') is False
        assert filter_envs.get('Demisto one before GA') is True
        assert filter_envs.get('Demisto GA') is True

    def test_changed_unrunnable_test__playbook_fromversion_1(self, mocker):
        """
        Given:
            - fake_test_playbook is fromversion 4.1.0 in integration file
            - two_before_ga is '4.0.0'
            - one_before_ga is '4.0.1'
            - ga is '4.1.0'
        When:
            - running get_test_list
            - running create_filter_envs_file
        Then:
            - Create test list with fake_test_playbook
            - Create filter_envs.json file with Demisto two before GA False and Demisto one before GA False

        """
        two_before_ga = '4.0.0'
        one_before_ga = '4.0.1'
        ga = '4.1.0'
        test_id = 'fake_test_playbook'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/fake_test_playbook.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list(two_before_ga, get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1

        create_filter_envs_file(filterd_tests, two_before_ga, one_before_ga, ga, TestConf(MOCK_CONF), MOCK_ID_SET)
        with open("./Tests/filter_envs.json", "r") as filter_envs_file:
            filter_envs = json.load(filter_envs_file)
        assert filter_envs.get('Server Master') is True
        assert filter_envs.get('Demisto PreGA') is True
        assert filter_envs.get('Demisto two before GA') is False
        assert filter_envs.get('Demisto one before GA') is False
        assert filter_envs.get('Demisto GA') is True

    def test_changed_unrunnable_test__playbook_fromvesion_2(self, mocker):
        # future_playbook_1 is fromversion 99.99.99 in conf file
        test_id = 'future_test_playbook_1'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/future_test_playbook_1.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('4.0.0', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1

    def test_changed_runnable_test__playbook_fromversion(self, mocker):
        # future_playbook_1 is toversion 99.99.99 in conf file
        test_id = 'future_test_playbook_1'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/future_test_playbook_1.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('99.99.99', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1

    def test_changed_unrunnable_test__skipped_test(self, mocker):
        test_id = 'skipped_integration_test_playbook_1'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/skipped_integration_test_playbook_1.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('4.0.0', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1

    def test_changed_unrunnable_test__skipped_integration(self, mocker):
        test_id = 'skipped_test_playbook_1'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/skipped_test_playbook_1.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[test_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('4.0.0', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1


class TestChangedIntegration:
    TEST_ID = 'PagerDuty Test'
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = "M Packs/PagerDuty/Integrations/PagerDuty/PagerDuty.yml"

    def test_changed_runnable_test__unmocked_get_modified_files(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert filterd_tests == {self.TEST_ID}

    def test_changed_unrunnable_test__integration_toversion(self, mocker):
        test_id = 'past_test_playbook_1'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/past_test_playbook_1.yml'
        file_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_integrations/past_integration_1.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[file_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('4.0.0', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1


class TestChangedIntegrationAndPlaybook:
    TEST_ID = 'PagerDuty Test\nCalculate Severity - Standard - Test'
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = "M Packs/PagerDuty/Integrations/PagerDuty/PagerDuty.py\n" \
                   "M Packs/Legacy/Playbooks/playbook-Calculate_Severity_By_Highest_DBotScore.yml"

    def test_changed_runnable_test__unmocked_get_modified_files(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert filterd_tests == set(self.TEST_ID.split('\n'))


class TestChangedScript:
    TEST_ID = 'Extract Indicators From File - test'
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = "M Packs/Legacy/Scripts/ExtractIndicatorsFromTextFile/ExtractIndicatorsFromTextFile.yml"

    def test_changed_runnable_test__unmocked_get_modified_files(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert filterd_tests == {self.TEST_ID}

    def test_changed_unrunnable_test__integration_toversion(self, mocker):
        test_id = 'past_test_playbook_2'
        test_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_test_playbooks/past_test_playbook_2.yml'
        file_path = 'Tests/scripts/infrastructure_tests/tests_data/mock_scripts/past_script_1.yml'
        get_modified_files_ret = create_get_modified_files_ret(modified_files_list=[file_path],
                                                               modified_tests_list=[test_path])
        filterd_tests = get_mock_test_list('4.0.0', get_modified_files_ret, mocker)

        assert test_id in filterd_tests
        assert len(filterd_tests) == 1


class TestSampleTesting:
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = "M Tests/scripts/integration-test.yml"

    def test_sample_tests(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert len(filterd_tests) == RANDOM_TESTS_NUM


class TestChangedCommonTesting:
    TEST_ID = 'TestCommonPython'
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = "M Packs/Base/Scripts/CommonServerPython/CommonServerPython.yml"

    def test_all_tests(self):
        filterd_tests = get_mock_test_list(git_diff_ret=self.GIT_DIFF_RET)

        assert len(filterd_tests) >= RANDOM_TESTS_NUM


class TestPackageFilesModified:
    TEST_ID = 'PagerDuty Test\nCalculate Severity - Standard - Test'
    # points at a real file. if that file changes path the test should fail
    GIT_DIFF_RET = """M Packs/Active_Directory_Query/Integrations/Active_Directory_Query/Active_Directory_Query.py
A       Packs/Active_Directory_Query/Integrations/Active_Directory_Query/cert.pem
M       Packs/Active_Directory_Query/Integrations/Active_Directory_Query/connection_test.py
A       Packs/Active_Directory_Query/Integrations/Active_Directory_Query/key.pem
"""

    def test_changed_runnable_test__unmocked_get_modified_files(self):
        files_list, tests_list, all_tests, is_conf_json, sample_tests, is_reputations_json, is_indicator_json = \
            get_modified_files(self.GIT_DIFF_RET)
        assert len(sample_tests) == 0
        assert 'Packs/Active_Directory_Query/Integrations/Active_Directory_Query/Active_Directory_Query.yml' in files_list


class TestNoChange:
    def test_no_change(self, mocker):
        # fake_test_playbook is fromversion 4.1.0 in playbook file
        get_modified_files_ret = create_get_modified_files_ret()
        filterd_tests = get_mock_test_list('4.1.0', get_modified_files_ret, mocker)

        assert len(filterd_tests) >= RANDOM_TESTS_NUM


def create_get_modified_files_ret(modified_files_list=[], modified_tests_list=[], changed_common=[], is_conf_json=False,
                                  sample_tests=[], is_reputations_json=[], is_indicator_json=[]):
    """
    Returns return value for get_modified_files() to be used with a mocker patch
    """
    return (
        modified_files_list,
        modified_tests_list,
        changed_common,
        is_conf_json,
        sample_tests,
        is_reputations_json,
        is_indicator_json
    )


TWO_BEFORE_GA_VERSION = '4.5.0'


def get_mock_test_list(two_before_ga=TWO_BEFORE_GA_VERSION, get_modified_files_ret=None, mocker=None, git_diff_ret=''):
    branch_name = 'BranchA'
    if get_modified_files_ret is not None:
        mocker.patch('Tests.scripts.configure_tests.get_modified_files', return_value=get_modified_files_ret)

    tests = get_test_list(git_diff_ret, branch_name, two_before_ga, id_set=MOCK_ID_SET, conf=TestConf(MOCK_CONF))
    return tests


def test_skipped_integration_should_not_be_tested(mocker):
    """
    Given
    - conf.json file with IntegrationA is skipped
    - no tests provided for IntegrationA

    When
    - filtering tests to run

    Then
    - ensure IntegrationA is skipped
    - ensure the validation not failing
    """
    from Tests.scripts import configure_tests
    configure_tests._FAILED = False  # reset the FAILED flag

    # Given
    # - conf.json file with IntegrationA is skipped
    # - no tests provided for IntegrationA
    fake_integration = TestUtils.create_integration(name='integration_a', with_commands=['a-command'])

    # mark as modified
    TestUtils.mock_get_modified_files(mocker,
                                      modified_files_list=[
                                          fake_integration['path']
                                      ])

    mock_conf_dict = copy.deepcopy(MOCK_CONF)
    mock_conf_dict['skipped_integrations']['integration_a'] = 'comment'

    fake_id_set = TestUtils.create_id_set()

    # When
    # - filtering tests to run
    filtered_tests = get_test_list(
        files_string='',
        branch_name='dummy_branch',
        two_before_ga_ver=TWO_BEFORE_GA_VERSION,
        conf=TestConf(mock_conf_dict),
        id_set=fake_id_set
    )

    # Then
    # - ensure IntegrationA is skipped
    assert 'integration_a' not in filtered_tests

    # - ensure the validation not failing
    assert not configure_tests._FAILED


def test_integration_has_no_test_playbook_should_fail_on_validation(mocker):
    """
    Given
    - integration_a was modified
    - no tests provided for integration_a

    When
    - filtering tests to run

    Then
    - ensure the validation is failing
    """
    from Tests.scripts import configure_tests
    configure_tests._FAILED = False  # reset the FAILED flag

    try:
        # Given
        # - integration_a was modified
        # - no tests provided for integration_a
        fake_integration = TestUtils.create_integration(name='integration_a', with_commands=['a-command'])

        # mark as modified
        TestUtils.mock_get_modified_files(mocker,
                                          modified_files_list=[
                                              fake_integration['path']
                                          ])

        # - both in conf.json
        fake_conf = TestUtils.create_tests_conf()

        fake_id_set = TestUtils.create_id_set(
            with_integration=fake_integration['id_set']
        )

        # When
        # - filtering tests to run
        get_test_list(
            files_string='',
            branch_name='dummy_branch',
            two_before_ga_ver=TWO_BEFORE_GA_VERSION,
            conf=fake_conf,
            id_set=fake_id_set
        )

        # Then
        # - ensure the validation is failing
        assert configure_tests._FAILED
    finally:
        # delete the mocked files
        TestUtils.delete_files([
            fake_integration['path']
        ])

        # reset _FAILED flag
        configure_tests._FAILED = False


def test_conf_has_modified(mocker):
    """
    Given
    - Tests/conf.json has been modified

    When
    - filtering tests to run

    Then
    - ensure the validation not failing
    """
    from Tests.scripts import configure_tests
    configure_tests._FAILED = False  # reset the FAILED flag

    try:
        # Given
        # - Tests/conf.json has been modified
        TestUtils.mock_get_modified_files(mocker,
                                          modified_files_list=[],
                                          is_conf_json=True)

        TestUtils.mock_run_command(
            mocker,
            on_command='git diff origin/master...dummy_branch Tests/conf.json',
            return_value='something'
        )
        # - both in conf.json
        fake_conf = TestUtils.create_tests_conf()

        fake_id_set = TestUtils.create_id_set()

        # When
        # - filtering tests to run
        get_test_list(
            files_string='',
            branch_name='dummy_branch',
            two_before_ga_ver=TWO_BEFORE_GA_VERSION,
            conf=fake_conf,
            id_set=fake_id_set
        )

        # Then
        # - ensure the validation not failing
        assert not configure_tests._FAILED
    finally:
        # reset _FAILED flag
        configure_tests._FAILED = False


def test_dont_fail_integration_on_no_tests_if_it_has_test_playbook_in_conf(mocker):
    """
    If there is an integration in conf.json configured with test playbook
    Ensure that this integration don't fails on validation.

    Given
    - integration_a that fetches incidents
    - test_playbook_a exists that should test FetchFromInstance of integration_a
    - both in conf.json

    When
    - filtering tests to run

    Then
    - ensure test_playbook_a will run/returned
    - ensure the validation not failing
    """
    from Tests.scripts import configure_tests
    configure_tests._FAILED = False  # reset the FAILED flag

    # Given
    # - integration_a exists
    fake_integration = TestUtils.create_integration(name='integration_a', with_commands=['a-command'])

    # mark as modified
    TestUtils.mock_get_modified_files(mocker,
                                      modified_files_list=[
                                          fake_integration['path']
                                      ])

    # - test_playbook_a exists that should test FetchFromInstance of integration_a
    fake_test_playbook = TestUtils.create_test_playbook(name='test_playbook_a',
                                                        with_scripts=['FetchFromInstance'])

    try:
        # - both in conf.json
        fake_conf = TestUtils.create_tests_conf(
            with_test_configuration={
                'integrations': 'integration_a',
                'playbookID': 'test_playbook_a'
            }
        )

        fake_id_set = TestUtils.create_id_set(
            with_integration=fake_integration['id_set'],
            with_test_playbook=fake_test_playbook['id_set']
        )

        # When
        # - filtering tests to run
        filtered_tests = get_test_list(
            files_string='',
            branch_name='dummy_branch',
            two_before_ga_ver=TWO_BEFORE_GA_VERSION,
            conf=fake_conf,
            id_set=fake_id_set
        )

        # Then
        # - ensure test_playbook_a will run/returned
        assert 'test_playbook_a' in filtered_tests

        # - ensure the validation not failing
        assert not configure_tests._FAILED
    finally:
        # delete the mocked files
        TestUtils.delete_files([
            fake_integration['path'],
            fake_test_playbook['path']
        ])

        # reset _FAILED flag
        configure_tests._FAILED = False
