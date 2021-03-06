# Copyright 2016 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import sys

import mock
import testtools

from tripleo_repos import main


class TestTripleORepos(testtools.TestCase):
    @mock.patch('tripleo_repos.main._parse_args')
    @mock.patch('tripleo_repos.main._validate_args')
    @mock.patch('tripleo_repos.main._get_base_path')
    @mock.patch('tripleo_repos.main._install_priorities')
    @mock.patch('tripleo_repos.main._remove_existing')
    @mock.patch('tripleo_repos.main._install_repos')
    def test_main(self, mock_install, mock_remove, mock_ip, mock_gbp,
                  mock_validate, mock_parse):
        mock_args = mock.Mock()
        mock_parse.return_value = mock_args
        mock_path = mock.Mock()
        mock_gbp.return_value = mock_path
        main.main()
        mock_validate.assert_called_once_with(mock_args)
        mock_gbp.assert_called_once_with(mock_args)
        mock_ip.assert_called_once_with()
        mock_remove.assert_called_once_with(mock_args)
        mock_install.assert_called_once_with(mock_args, mock_path)

    @mock.patch('requests.get')
    def test_get_repo(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = '88MPH'
        mock_get.return_value = mock_response
        fake_addr = 'http://lone/pine/mall'
        content = main._get_repo(fake_addr, mock.Mock())
        self.assertEqual('88MPH', content)
        mock_get.assert_called_once_with(fake_addr)

    @mock.patch('requests.get')
    def test_get_repo_404(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        fake_addr = 'http://twin/pines/mall'
        main._get_repo(fake_addr, mock.Mock())
        mock_get.assert_called_once_with(fake_addr)
        mock_response.raise_for_status.assert_called_once_with()

    @mock.patch('os.listdir')
    @mock.patch('os.remove')
    def test_remove_existing(self, mock_remove, mock_listdir):
        fake_list = ['foo.repo', 'delorean.repo',
                     'delorean-current-tripleo.repo',
                     'tripleo-centos-opstools.repo']
        mock_listdir.return_value = fake_list
        mock_args = mock.Mock()
        mock_args.output_path = '/etc/yum.repos.d'
        main._remove_existing(mock_args)
        self.assertIn(mock.call('/etc/yum.repos.d/delorean.repo'),
                      mock_remove.mock_calls)
        self.assertIn(mock.call('/etc/yum.repos.d/'
                                'delorean-current-tripleo.repo'),
                      mock_remove.mock_calls)
        self.assertIn(
            mock.call('/etc/yum.repos.d/tripleo-centos-opstools.repo'),
            mock_remove.mock_calls)
        self.assertNotIn(mock.call('/etc/yum.repos.d/foo.repo'),
                         mock_remove.mock_calls)

    def test_get_base_path(self):
        args = mock.Mock()
        args.branch = 'master'
        args.distro = 'centos7'
        args.rdo_mirror = 'http://trunk.rdoproject.org'
        path = main._get_base_path(args)
        self.assertEqual('http://trunk.rdoproject.org/centos7/', path)

    def test_get_base_path_branch(self):
        args = mock.Mock()
        args.branch = 'liberty'
        args.distro = 'centos7'
        args.rdo_mirror = 'http://trunk.rdoproject.org'
        path = main._get_base_path(args)
        self.assertEqual('http://trunk.rdoproject.org/centos7-liberty/', path)

    @mock.patch('subprocess.check_call')
    def test_install_priorities(self, mock_check_call):
        main._install_priorities()
        mock_check_call.assert_called_once_with(['yum', 'install', '-y',
                                                 'yum-plugin-priorities'])

    @mock.patch('subprocess.check_call')
    def test_install_priorities_fails(self, mock_check_call):
        mock_check_call.side_effect = subprocess.CalledProcessError(88, '88')
        self.assertRaises(subprocess.CalledProcessError,
                          main._install_priorities)

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current_mitaka(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'mitaka'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current/delorean.repo', args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean-mitaka]\nMr. Fusion', 'test'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_deps(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['deps']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean-deps]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_called_once_with('roads/delorean-deps.repo', args)
        mock_write.assert_called_once_with('[delorean-deps]\nMr. Fusion',
                                           'test')

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current_tripleo(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-tripleo']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        self.assertEqual([mock.call('roads/current-tripleo/delorean.repo',
                                    args),
                          mock.call('roads/delorean-deps.repo', args),
                          ],
                         mock_get.mock_calls)
        self.assertEqual([mock.call('[delorean]\nMr. Fusion', 'test'),
                          mock.call('[delorean]\nMr. Fusion', 'test'),
                          ],
                         mock_write.mock_calls)

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current_tripleo_dev(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-tripleo-dev']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_any_call('roads/delorean-deps.repo', args)
        # This is the wrong name for the deps repo, but I'm not bothered
        # enough by that to mess with mocking multiple different calls.
        mock_write.assert_any_call('[delorean]\n'
                                   'Mr. Fusion', 'test')
        mock_get.assert_any_call('roads/current-tripleo/delorean.repo', args)
        mock_write.assert_any_call('[delorean-current-tripleo]\n'
                                   'Mr. Fusion\npriority=20', 'test')
        mock_get.assert_called_with('roads/current/delorean.repo', args)
        mock_write.assert_called_with('[delorean]\nMr. Fusion\n%s\n'
                                      'priority=10' %
                                      main.INCLUDE_PKGS, 'test')

    @mock.patch('tripleo_repos.main._write_repo')
    @mock.patch('tripleo_repos.main._create_ceph')
    def test_install_repos_ceph(self, mock_create_ceph, mock_write_repo):
        args = mock.Mock()
        args.repos = ['ceph']
        args.branch = 'master'
        args.output_path = 'test'
        mock_repo = '[centos-ceph-jewel]\nMr. Fusion'
        mock_create_ceph.return_value = mock_repo
        main._install_repos(args, 'roads/')
        mock_create_ceph.assert_called_once_with(args, 'jewel')
        mock_write_repo.assert_called_once_with(mock_repo, 'test')

    @mock.patch('tripleo_repos.main._write_repo')
    @mock.patch('tripleo_repos.main._create_ceph')
    def test_install_repos_ceph_mitaka(self, mock_create_ceph,
                                       mock_write_repo):
        args = mock.Mock()
        args.repos = ['ceph']
        args.branch = 'mitaka'
        args.output_path = 'test'
        mock_repo = '[centos-ceph-hammer]\nMr. Fusion'
        mock_create_ceph.return_value = mock_repo
        main._install_repos(args, 'roads/')
        mock_create_ceph.assert_called_once_with(args, 'hammer')
        mock_write_repo.assert_called_once_with(mock_repo, 'test')

    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_opstools(self, mock_write):
        args = mock.Mock()
        args.repos = ['opstools']
        args.branch = 'master'
        args.output_path = 'test'
        args.centos_mirror = 'http://foo'
        main._install_repos(args, 'roads/')
        expected_repo = ('\n[tripleo-centos-opstools]\n'
                         'name=tripleo-centos-opstools\n'
                         'baseurl=http://foo/centos/7/opstools/x86_64/\n'
                         'gpgcheck=0\n'
                         'enabled=1\n')
        mock_write.assert_called_once_with(expected_repo,
                                           'test')

    @mock.patch('requests.get')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_deps_mirror(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['deps']
        args.branch = 'master'
        args.output_path = 'test'
        args.centos_mirror = 'http://foo'
        args.rdo_mirror = 'http://bar'
        # Abbrevieated repos to verify the regex works
        fake_repo = '''
[delorean-current-tripleo]
name=test repo
baseurl=https://trunk.rdoproject.org/centos7/some-repo-hash
enabled=1

[rdo-qemu-ev]
name=test qemu-ev
baseurl=http://mirror.centos.org/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        expected_repo = '''
[delorean-current-tripleo]
name=test repo
baseurl=http://bar/centos7/some-repo-hash
enabled=1

[rdo-qemu-ev]
name=test qemu-ev
baseurl=http://foo/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        mock_get.return_value = mock.Mock(text=fake_repo,
                                          status_code=200)
        main._install_repos(args, 'roads/')
        mock_write.assert_called_once_with(expected_repo,
                                           'test')

    def test_install_repos_invalid(self):
        args = mock.Mock()
        args.repos = ['roads?']
        self.assertRaises(main.InvalidArguments, main._install_repos, args,
                          'roads/')

    def test_write_repo(self):
        m = mock.mock_open()
        with mock.patch('tripleo_repos.main.open', m, create=True):
            main._write_repo('#Doc\n[delorean]\nThis=Heavy', 'test')
        m.assert_called_once_with('test/delorean.repo', 'w')
        m().write.assert_called_once_with('#Doc\n[delorean]\nThis=Heavy')

    def test_write_repo_invalid(self):
        self.assertRaises(main.NoRepoTitle, main._write_repo, 'Great Scot!',
                          'test')

    def test_parse_args(self):
        with mock.patch.object(sys, 'argv', ['', 'current', 'deps', '-d',
                                             'centos7', '-b', 'liberty',
                                             '-o', 'test']):
            args = main._parse_args()
        self.assertEqual(['current', 'deps'], args.repos)
        self.assertEqual('centos7', args.distro)
        self.assertEqual('liberty', args.branch)
        self.assertEqual('test', args.output_path)

    def test_parse_args_long(self):
        with mock.patch.object(sys, 'argv', ['', 'current', '--distro',
                                             'centos7', '--branch',
                                             'mitaka', '--output-path',
                                             'test']):
            args = main._parse_args()
        self.assertEqual(['current'], args.repos)
        self.assertEqual('centos7', args.distro)
        self.assertEqual('mitaka', args.branch)
        self.assertEqual('test', args.output_path)

    def test_change_priority(self):
        result = main._change_priority('[delorean]\npriority=1', 10)
        self.assertEqual('[delorean]\npriority=10', result)

    def test_change_priority_none(self):
        result = main._change_priority('[delorean]', 10)
        self.assertEqual('[delorean]\npriority=10', result)

    def test_create_ceph(self):
        mock_args = mock.Mock(centos_mirror='http://foo')
        result = main._create_ceph(mock_args, 'jewel')
        expected_repo = '''
[tripleo-centos-ceph-jewel]
name=tripleo-centos-ceph-jewel
baseurl=http://foo/centos/7/storage/x86_64/ceph-jewel/
gpgcheck=0
enabled=1
'''
        self.assertEqual(expected_repo, result)

    def test_inject_mirrors(self):
        start_repo = '''
[delorean]
name=delorean
baseurl=https://trunk.rdoproject.org/centos7/some-repo-hash
enabled=1
[centos]
name=centos
baseurl=http://mirror.centos.org/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        expected = '''
[delorean]
name=delorean
baseurl=http://bar/centos7/some-repo-hash
enabled=1
[centos]
name=centos
baseurl=http://foo/centos/7/virt/$basearch/kvm-common
enabled=1
'''
        mock_args = mock.Mock(centos_mirror='http://foo',
                              rdo_mirror='http://bar')
        result = main._inject_mirrors(start_repo, mock_args)
        self.assertEqual(expected, result)

    def test_inject_mirrors_no_match(self):
        start_repo = '''
[delorean]
name=delorean
baseurl=https://some.mirror.com/centos7/some-repo-hash
enabled=1
'''
        mock_args = mock.Mock(rdo_mirror='http://some.mirror.com')
        # If a user has a mirror whose repos already point at itself then
        # the _inject_mirrors call should be a noop.
        self.assertEqual(start_repo, main._inject_mirrors(start_repo,
                                                          mock_args))


class TestValidate(testtools.TestCase):
    def setUp(self):
        super(TestValidate, self).setUp()
        self.args = mock.Mock()
        self.args.repos = ['current']
        self.args.branch = 'master'
        self.args.distro = 'centos7'

    def test_good(self):
        main._validate_args(self.args)

    def test_current_and_tripleo_dev(self):
        self.args.repos = ['current', 'current-tripleo-dev']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_ceph_and_tripleo_dev(self):
        self.args.repos = ['current-tripleo-dev', 'ceph']
        self.args.output_path = main.DEFAULT_OUTPUT_PATH
        main._validate_args(self.args)

    def test_deps_and_tripleo_dev(self):
        self.args.repos = ['deps', 'current-tripleo-dev']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_branch_and_tripleo_dev(self):
        self.args.repos = ['current-tripleo-dev']
        self.args.branch = 'liberty'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_current_and_tripleo(self):
        self.args.repos = ['current', 'current-tripleo']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_deps_and_tripleo_allowed(self):
        self.args.repos = ['deps', 'current-tripleo']
        main._validate_args(self.args)

    def test_branch_and_tripleo(self):
        self.args.repos = ['current-tripleo']
        self.args.branch = 'liberty'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_invalid_distro(self):
        self.args.distro = 'Jigawatts 1.21'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)
