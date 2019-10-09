import sys
from pathlib import Path
from itertools import cycle

import paramiko
from git import Repo


class SFTP:
    """
    Do:
    |with SFTP('localhost', 'root', '123456') as sftp:|
    |     ...                                         |
    for return object paramiko.sftp_client.SFTPClient
    """
    def __init__(self, host:str, user:str, password:str, port:[int,str]=22):
        self.transport = paramiko.Transport((host, int(port)))
        self.transport.connect(username=user, password=password)

    def __enter__(self)-> paramiko.sftp_client.SFTPClient:
        return paramiko.SFTPClient.from_transport(self.transport)

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('connection is close')
        self.transport.close()

    def __getattr__(self, item):
        raise AttributeError

class DiffGenerator:
    """
    generate old_file_name :str, new _file_name: str
    and what with him to do.
    variant to do:
       add -
       delete -
       add-delete -
    """
    def __init__(self, repo_path:str):
        self.repo = Repo(repo_path)

    def _iter(self, commit):
        change_type = {"A":"delete", "D":"add", "M":"add", "T":"add"}
        for name, value in change_type.items():
            yield zip(commit.diff('HEAD~1').iter_change_type(name), cycle([value]))
        change_type = {"R":"move",}
        for name, value in change_type.items():
            yield zip(commit.diff('HEAD~1').iter_change_type(name), cycle([value]))

    def __iter__(self):
        head_commit_datatime = self.repo.head.commit.committed_datetime
        for commit in list(self.repo.iter_commits()):
            if commit.committed_datetime != head_commit_datatime:
                break
            for iterator in self._iter(commit):
                for item, do in iterator:
                    yield item.b_path, item.a_path, do

def recursive_create_dir(sftp, path):
    try:
        print(str(path))
        sftp.mkdir(str(path))
    except OSError:
        if str(path) == '.':
            print('error')
            exit(0)
        print(f'Exception! Not found file {str(path)}')
        recursive_create_dir(sftp, path.parent)


if __name__ == '__main__':
    if  len(sys.argv) != 6 or sys.argv in ['-h', '--help', '?']:
        print('    python3 deploy.py {host} {user} {password} {port} {dir_on_server}\n',
              'where:\n',
              '   host = address server, example 123.456.788.90 or localhost\n',
              '   port = port server, example 22\n',
              '   user = user on server, example root or administrator\n',
              '   password = password of user, example Qwerty\n',
              '   dir_on_server = path for dir with edit data, example /var/www/html/site_dir',)
        exit(1)
    print("")
    repo_path = str(Path(__file__).parent.absolute())
    remote_dir = sys.argv[-1]
    with SFTP(*sys.argv[1:-1]) as sftp:
        sftp.chdir(remote_dir)
        delete = lambda old, new:sftp.remove(old)
        move = lambda old, new: sftp.rename(old, new)
        add = lambda old, new: sftp.put(old, new)
        S = {'delete':delete, 'move':move, 'add':add}
        for old_path, new_path, what_do in DiffGenerator(repo_path):
            print(old_path, new_path, what_do)
            try:
                S.get(what_do)(old_path, new_path)
            except:
                if what_do == 'delete':
                    continue
                print(f'Exception! Not found file {old_path} > {new_path}')
                recursive_create_dir(sftp, Path(new_path).parent)
                S.get(what_do)(old_path, new_path)
                print(old_path, new_path, what_do)



