import os

from catkin_pkg.package import InvalidPackage
from catkin_pkg.packages import find_package_paths
from catkin_pkg.packages import find_packages
from catkin_pkg.packages import find_packages_allowing_duplicates

from .util import in_temporary_directory


test_data_dir = os.path.join(os.path.dirname(__file__), 'data', 'ignored_packages')


def _create_pkg_in_dir(path, version='0.1.0'):
    path = os.path.abspath(path)
    os.makedirs(path)

    template = """\
<?xml version="1.0"?>
<package>
  <name>{0}</name>
  <version>{1}</version>
  <description>Package {0}</description>
  <license>BSD</license>

  <maintainer email="foo@bar.com">Foo Bar</maintainer>
</package>
""".format(os.path.basename(path), version)

    with open(os.path.join(path, 'package.xml'), 'w+') as f:
        f.write(template)


@in_temporary_directory
def test_package_paths_with_hidden_directories():
    _create_pkg_in_dir('.test1')
    _create_pkg_in_dir('.test2')
    _create_pkg_in_dir('test3')  # not hidden
    _create_pkg_in_dir('.test4')

    res = find_package_paths('.')
    assert res == ['test3']


@in_temporary_directory
def test_find_packages_allowing_duplicates_with_no_packages():
    res = find_packages_allowing_duplicates('.')
    assert isinstance(res, dict)
    assert not res


def _create_broken_pkg_in_dir(path):
    # same as _create_pkg_in_dir but without a maintainer, which makes
    # the package invalid
    path = os.path.abspath(path)
    os.makedirs(path)

    template = """\
<?xml version="1.0"?>
<package>
  <name>{0}</name>
  <version>0.1.0</version>
  <description>Package {0}</description>
  <license>BSD</license>
</package>
""".format(os.path.basename(path))

    with open(os.path.join(path, 'package.xml'), 'w+') as f:
        f.write(template)


@in_temporary_directory
def test_find_packages_allowing_duplicates_collects_errors():
    _create_pkg_in_dir('good1')
    _create_pkg_in_dir('good2')
    _create_broken_pkg_in_dir('broken')

    # without an errors list the invalid package still raises
    try:
        find_packages_allowing_duplicates('.')
        assert False, 'Must raise'
    except InvalidPackage as e:
        assert 'broken' in str(e)

    # with an errors list the valid packages are returned and the
    # error of the invalid package is collected instead
    errors = []
    res = find_packages_allowing_duplicates('.', errors=errors)
    assert sorted(res.keys()) == ['good1', 'good2']
    assert len(errors) == 1
    assert 'broken' in errors[0]
    assert 'maintainer' in errors[0]


@in_temporary_directory
def test_find_packages_collects_errors():
    _create_pkg_in_dir('good')
    _create_broken_pkg_in_dir('broken')

    errors = []
    res = find_packages('.', errors=errors)
    assert list(res.keys()) == ['good']
    assert len(errors) == 1
    assert 'broken' in errors[0]


@in_temporary_directory
def test_find_packages_allowing_duplicates_collects_errors_in_parallel():
    # more than 100 packages trigger the multiprocessing code path
    for i in range(105):
        _create_pkg_in_dir('pkg%03d' % i)
    _create_broken_pkg_in_dir('broken')

    errors = []
    res = find_packages_allowing_duplicates('.', errors=errors)
    assert len(res) == 105
    assert 'broken' not in res
    assert len(errors) == 1
    assert 'broken' in errors[0]


@in_temporary_directory
def test_find_packages_invalid_version():
    version = ':{version}'
    path = os.path.join('src', 'foo')
    _create_pkg_in_dir(path, version)
    try:
        find_packages(os.path.dirname(path))
        assert False, 'Must raise'
    except InvalidPackage as e:
        exception_message = str(e)
        assert version in exception_message
        assert path in exception_message


def test_find_no_ignored_packages():
    result = find_packages(test_data_dir)
    assert 'catkin_ignore' not in result
    assert 'custom_ignore' in result


def test_find_no_ignored_packages_with_custom_ignore():
    custom_result = find_packages(test_data_dir, ignore_markers={'CUSTOM_IGNORE'})
    assert 'custom_ignore' not in custom_result
    assert 'catkin_ignore' in custom_result
