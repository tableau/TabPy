'''
Update version (VERSION file in the repository root)
with commit number:
major.minor.commit

The script is only to be used in Travis CI,
see .travis.yml for more details.

The script uses Travis enviroment variables, see
https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
for more details.
'''

import os


def main():
    if not os.environ.get('TRAVIS', False):
        print(__doc__)
        return 1

    branch = os.environ.get('TRAVIS_BRANCH')
    pr_branch = os.environ.get('TRAVIS_PULL_REQUEST_BRANCH')
    if not pr_branch or pr_branch == branch:
        new_ver = update_version()
        push_new_version_to_branch(branch, new_ver)

    return 0

def update_version():
    version = '0.0.0'
    with open('VERSION') as f:
        version = f.read()
    ver = version.split('.')
    commit = os.environ.get('TRAVIS_PULL_REQUEST_SHA')
    new_ver = f'{ver[0]}.{ver[1]}.{commit}'

    with open('VERSION', 'w') as f:
        f.write(new_ver)

    return new_ver


def push_new_version_to_branch(branch, new_ver):
    # configure git
    os.system(f'git config --global user.email "travis@travis-ci.org"')
    os.system(f'git config --global user.name "Travis CI"')
    gh_token = os.environ.get('GH_TOKEN')
    os.system(f'git remote set-url origin https://{gh_token}@github.com/tableau/TabPy.git > /dev/null 2>&1')

    # commit and push new version
    os.system(f'git add -u')
    os.system(f'git commit -m "[ci skip] increase version to {new_ver}"')
    os.system(f'git push origin HEAD:{branch}')


if __name__ == "__main__":
    main()
