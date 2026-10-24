import os
import shutil
import subprocess

import pytest

from catkin_pkg.changelog_generator_vcs import GitClient

from .util import in_temporary_directory


def _git(*args):
    subprocess.check_call(
        ['git'] + list(args),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _commit_file(filename, content, message):
    with open(filename, 'w') as f:
        f.write(content)
    _git('add', filename)
    _git('commit', '-m', message)


@pytest.mark.skipif(shutil.which('git') is None, reason='git is not available')
@in_temporary_directory
def test_git_client_with_ambiguous_refname():
    # a repository where a branch and a tag share the name '2.0.0',
    # which makes git print "warning: refname '2.0.0' is ambiguous"
    # whenever the plain name is used
    _git('init')
    _git('config', 'user.email', 'foo@bar.com')
    _git('config', 'user.name', 'Foo Bar')
    _commit_file('a.txt', 'a', 'first commit')
    _git('tag', '1.0.0')
    _commit_file('b.txt', 'b', 'second commit')
    _git('tag', '2.0.0')
    _git('branch', '2.0.0')
    _commit_file('c.txt', 'c', 'third commit')

    client = GitClient(os.getcwd())

    tags = client.get_tags()
    tag_names = [tag.name for tag in tags]
    assert '1.0.0' in tag_names
    assert '2.0.0' in tag_names
    for tag in tags:
        # the timestamp must be an actual date, not a git warning
        assert tag.timestamp.startswith('20')

    # log entries between the two tags: only the second commit
    entries = client.get_log_entries(from_tag='2.0.0', to_tag='1.0.0')
    messages = [entry.msg.strip() for entry in entries]
    assert messages == ['second commit']

    # log entries up to the latest tag
    entries = client.get_log_entries(from_tag='2.0.0', to_tag=None)
    messages = sorted(entry.msg.strip() for entry in entries)
    assert messages == ['first commit', 'second commit']
