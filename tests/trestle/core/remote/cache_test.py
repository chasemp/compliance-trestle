# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2020 IBM Corp. All rights reserved.
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
"""Testing for cache functionality."""

import pathlib
import random
import string
from unittest.mock import patch

import pytest

import trestle.core.err as err
from trestle.core import generators
from trestle.core.err import TrestleError
from trestle.core.remote import cache
from trestle.core.settings import Settings
from trestle.oscal.catalog import Catalog
from trestle.utils import fs


def test_fetcher_oscal(tmp_trestle_dir):
    """Test whether fetcher can get an object from the cache as an oscal model."""
    # Fetch from local content, expecting it to be cached and then fetched as an oscal model.
    rand_str = ''.join(random.choice(string.ascii_letters) for x in range(16))
    catalog_file = pathlib.Path(tmp_trestle_dir / f'{rand_str}.json').__str__()
    catalog_data = generators.generate_sample_model(Catalog)
    catalog_data.oscal_write(pathlib.Path(catalog_file))
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), catalog_file, False, False)
    # Create/update the cache copy
    fetcher._refresh = True
    fetcher._cache_only = False
    fetcher._update_cache()
    fetched_data = fetcher.get_oscal(Catalog)
    # Make last_modified identical then compare as this alone is expected to differ:
    fetched_data.metadata.last_modified = catalog_data.metadata.last_modified
    assert fetched_data == catalog_data


def test_fetcher_oscal_fails(tmp_trestle_dir):
    """Test whether fetcher can get an object from the cache as an oscal model."""
    # Fetch from local content, expecting it to be cached and then fetched as an oscal model.
    rand_str = ''.join(random.choice(string.ascii_letters) for x in range(16))
    catalog_file = pathlib.Path(tmp_trestle_dir / f'{rand_str}.json').__str__()
    catalog_data = generators.generate_sample_model(Catalog)
    catalog_data.oscal_write(pathlib.Path(catalog_file))
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), catalog_file, False, False)
    # Create/update the cache copy
    fetcher._refresh = True
    fetcher._cache_only = False
    fetcher._update_cache()
    # 1. What if cache file does not exist?
    with patch('pathlib.Path.exists') as path_exists_mock:
        path_exists_mock.return_value = False
        with pytest.raises(err.TrestleError):
            fetcher.get_oscal(Catalog)
        path_exists_mock.assert_called_once()
    # 2. What if oscal_read of cache file throws TrestleError?
    with patch('trestle.oscal.catalog.Catalog.oscal_read') as oscal_read_mock:
        oscal_read_mock.side_effect = err.TrestleError
        with pytest.raises(err.TrestleError):
            fetcher.get_oscal(Catalog)
        oscal_read_mock.assert_called_once()


def test_fetcher_base(tmp_trestle_dir):
    """Test whether fetcher can get an object from the cache."""
    # Fetch from local content, expecting it to be cached and then fetched.
    rand_str = ''.join(random.choice(string.ascii_letters) for x in range(16))
    catalog_file = pathlib.Path(tmp_trestle_dir / f'{rand_str}.json').__str__()
    catalog_data = generators.generate_sample_model(Catalog)
    catalog_data.oscal_write(pathlib.Path(catalog_file))
    saved_data = fs.load_file(pathlib.Path(catalog_file))
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), catalog_file, False, False)
    # Create/update the cache copy
    fetcher._refresh = True
    fetcher._cache_only = False
    fetched_data = fetcher.get_raw()
    assert fetched_data == saved_data


def test_github_fetcher():
    """Test the github fetcher."""
    pass


def test_local_fetcher_get_fails(tmp_trestle_dir):
    """Test the local fetcher."""
    rand_str = ''.join(random.choice(string.ascii_letters) for x in range(16))
    catalog_file = pathlib.Path(tmp_trestle_dir / f'{rand_str}.json').__str__()
    catalog_data = generators.generate_sample_model(Catalog)
    catalog_data.oscal_write(pathlib.Path(catalog_file))
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), catalog_file, False, False)
    fetcher._cache_only = True
    with pytest.raises(err.TrestleError):
        fetcher.get_raw()
    with pytest.raises(err.TrestleError):
        fetcher.get_oscal(Catalog)


def test_local_fetcher(tmp_trestle_dir):
    """Test the local fetcher."""
    rand_str = ''.join(random.choice(string.ascii_letters) for x in range(16))
    catalog_file = pathlib.Path(tmp_trestle_dir / f'{rand_str}.json').__str__()
    catalog_data = generators.generate_sample_model(Catalog)
    catalog_data.oscal_write(pathlib.Path(catalog_file))
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), catalog_file, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    fetcher._update_cache()
    assert fetcher._inst_cache_path.exists()


def test_sftp_fetcher(tmp_trestle_dir):
    """Test the sftp fetcher."""
    uri = 'sftp://some.host//path/to/test.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    with patch('paramiko.SSHClient.load_system_host_keys') as ssh_load_keys_mock:
        with patch('paramiko.SSHClient.connect') as ssh_connect_mock:
            with patch('paramiko.SSHClient.open_sftp') as sftp_open_mock:
                with patch('paramiko.SFTPClient.get'):
                    try:
                        fetcher._update_cache()
                    except Exception:
                        AssertionError()
                    ssh_load_keys_mock.assert_called_once()
                    ssh_connect_mock.assert_called_once()
                    sftp_open_mock.assert_called_once()


def test_sftp_fetcher_cache_only(tmp_trestle_dir):
    """Test that sftp fetcher does not call update (_sync_cache) when _cache_only is true."""
    uri = 'sftp://some.host//path/to/test.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = True
    with patch('trestle.core.remote.cache.SFTPFetcher._sync_cache') as sync_cache_mock:
        fetcher._update_cache()
        sync_cache_mock.assert_not_called()


def test_sftp_fetcher_load_system_keys_fails(tmp_trestle_dir):
    """Test the sftp fetcher when SSHClient loading of system host keys fails."""
    uri = 'sftp://username:password@some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    with patch('paramiko.SSHClient.load_system_host_keys') as ssh_load_system_host_keys_mock:
        ssh_load_system_host_keys_mock.side_effect = OSError('stuff')
        with pytest.raises(err.TrestleError):
            fetcher._update_cache()


def test_sftp_fetcher_load_keys_fails(tmp_trestle_dir, monkeypatch):
    """Test the sftp fetcher when SSHClient load host keys specified in env var fails."""
    monkeypatch.setenv('SSH_KEY', 'some_key_file')
    uri = 'sftp://username:password@some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    with patch('paramiko.SSHClient.load_host_keys') as ssh_load_host_keys_mock:
        ssh_load_host_keys_mock.side_effect = OSError('stuff')
        with pytest.raises(err.TrestleError):
            fetcher._update_cache()
            ssh_load_host_keys_mock.assert_called_once()


def test_sftp_fetcher_connect_fails(tmp_trestle_dir):
    """Test sftp during SSHClient connect failure."""
    # Password given:
    uri = 'sftp://username:password@some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    with patch('paramiko.SSHClient.connect') as ssh_connect_mock:
        ssh_connect_mock.side_effect = err.TrestleError('stuff')
        with pytest.raises(err.TrestleError):
            fetcher._update_cache()
    # Password not given (assumes attempt to use ssh-agent):
    uri = 'sftp://username@some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    with patch('paramiko.SSHClient.connect') as ssh_connect_mock:
        ssh_connect_mock.side_effect = err.TrestleError('stuff')
        with pytest.raises(err.TrestleError):
            fetcher._update_cache()


def test_sftp_fetcher_open_sftp_fails(tmp_trestle_dir, monkeypatch):
    """Test the exception response during open_sftp failure."""
    uri = 'sftp://username:password@some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    monkeypatch.setenv('SSH_KEY', 'some_key_file')
    with patch('paramiko.SSHClient.load_host_keys') as load_host_keys_mock:
        with patch('paramiko.SSHClient.connect') as connect_mock:
            with patch('paramiko.SSHClient.open_sftp') as open_sftp_mock:
                open_sftp_mock.side_effect = err.TrestleError('stuff')
                with pytest.raises(err.TrestleError):
                    fetcher._update_cache()
                    load_host_keys_mock.assert_called_once()
                    connect_mock.assert_called_once()
                    open_sftp_mock.assert_called_once()


def test_sftp_fetcher_getuser_fails(tmp_trestle_dir, monkeypatch):
    """Test the sftp call to getpass.getuser."""
    uri = 'sftp://some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    # Force call to paramiko.SSHClient.load_host_keys
    monkeypatch.setenv('SSH_KEY', 'some_key_file')
    with patch('getpass.getuser') as getuser_mock:
        with pytest.raises(err.TrestleError):
            fetcher._update_cache()
            getuser_mock.assert_called_once()


def test_sftp_fetcher_get_fails(tmp_trestle_dir, monkeypatch):
    """Test the sftp fetcher SFTPClient.get() failing."""
    uri = 'sftp://username:password@some.host/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)
    fetcher._refresh = True
    fetcher._cache_only = False
    # Force call to paramiko.SSHClient.load_host_keys
    monkeypatch.setenv('SSH_KEY', 'some_key_file')
    with patch('paramiko.SSHClient.load_host_keys') as load_host_keys_mock:
        with patch('paramiko.SSHClient.connect') as connect_mock:
            with patch('paramiko.SFTPClient.get') as get_mock:
                get_mock.side_effect = err.TrestleError('get fails')
                with pytest.raises(TrestleError):
                    fetcher._update_cache()
                    load_host_keys_mock.assert_called_once()
                    connect_mock.assert_called_once()
                    get_mock.assert_called_once()


def test_sftp_fetcher_bad_uri(tmp_trestle_dir):
    """Test get_fetcher handling of bad SFTP URI."""
    for uri in ['sftp://blah.com',
                'sftp:///path/to/file.json',
                'sftp://user:pass@hostname.com\\path\\to\\file.json',
                'sftp://:pass@hostname.com/path/to/file.json']:
        with pytest.raises(TrestleError):
            cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)


def test_fetcher_bad_uri(tmp_trestle_dir):
    """Test fetcher factory with bad URI."""
    for uri in ['', 'https://', 'https:///blah.com', 'sftp://', '..']:
        with pytest.raises(TrestleError):
            cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), uri, False, False)


def test_fetcher_factory(tmp_trestle_dir: pathlib.Path) -> None:
    """Test that the fetcher factory correctly resolves functionality."""
    settings = Settings()

    local_uri_1 = 'file:///home/user/oscal_file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), local_uri_1, settings, False, False)
    assert type(fetcher) == cache.LocalFetcher

    local_uri_2 = '/home/user/oscal_file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), local_uri_2, settings, False, False)
    assert type(fetcher) == cache.LocalFetcher

    local_uri_3 = '../../file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), local_uri_3, settings, False, False)
    assert type(fetcher) == cache.LocalFetcher

    sftp_uri = 'sftp://user@hostname:/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), sftp_uri, settings, False, False)
    assert type(fetcher) == cache.SFTPFetcher

    sftp_uri_2 = 'sftp://user@hostname:2000/path/to/file.json'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), sftp_uri_2, settings, False, False)
    assert type(fetcher) == cache.SFTPFetcher

    # https_uri = 'https://placekitten.com/200/300'
    # fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), https_uri, settings, False, False)
    # assert type(fetcher) == cache.HTTPSFetcher

    https_basic_auth = 'https://{{USERNAME}}:{{PASSWORD}}@placekitten.com/200/300'
    fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), https_basic_auth, settings, False, False)
    assert type(fetcher) == cache.HTTPSFetcher

    # github_url_1 = 'https://github.com/DrJohnWagner/recipes/blob/master/README.md'
    # fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), github_url_1, settings, False, False)
    # assert type(fetcher) == cache.GithubFetcher
    # fetcher._sync_cache()

    # github_url_2 = 'https://github.ibm.com/aur-mma/ai-for-the-eye/blob/master/README.md'
    # fetcher = cache.FetcherFactory.get_fetcher(pathlib.Path(tmp_trestle_dir), github_url_2, settings, False, False)
    # assert type(fetcher) == cache.GithubFetcher
    # fetcher._sync_cache()