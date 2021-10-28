#!/bin/python3

import sys, getopt, tempfile, os
import subprocess
import time
import gitlab
from urllib.parse import urlparse

def PrintUsage():
    print('Usage ./svn2gitlab.py -i <svn repo> -o <git path> -k <gitlab api key>')

def ParseGitlabRepo(fullUrl):
    group = ''
    apiUrl = ''
    project = ''
    parsedUrl = urlparse(fullUrl)
    apiUrl = parsedUrl.scheme + "://"+ parsedUrl.netloc
    group = os.path.dirname(parsedUrl.path)[1:]
    project = os.path.basename(parsedUrl.path)
    print(apiUrl)
    print(group)
    print(project)
    return apiUrl, group, project

def main(argv):
    inputRepo = ''
    outputRepo = ''
    apiKey = ''
    
    try:
        opts, args = getopt.getopt(argv, 'hi:o:k:')
    except:
        PrintUsage()
        sys.exit(1)
    for opt, arg in opts:
        if opt == '-h':
            PrintUsage()
            sys.exit()
        elif opt == '-i':
            inputRepo = arg
        elif opt == '-o':
            outputRepo = arg
        elif opt == '-k':
            apiKey = arg

    print(inputRepo)
    print(outputRepo)
    print(apiKey)

    url, group, project = ParseGitlabRepo(outputRepo)

    with tempfile.TemporaryDirectory(prefix='svn2gitlab_') as tmpdirname:
        print(tmpdirname)
        os.chdir(tmpdirname)
        os.mkdir('svn')
        os.chdir('svn')
        checkoutCommand = 'svn checkout ' + inputRepo + ' .'
        checkout = subprocess.Popen(checkoutCommand, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (output, err) = checkout.communicate()
        
        logCommand = r'''svn log --quiet | grep -E "r[0-9]+ \| .+ \|" | cut -d'|' -f2 | sed 's/ //g' | sort | uniq'''
        log = subprocess.Popen(logCommand, shell=True, stdout=subprocess.PIPE, text=True)
        (output, err) = log.communicate()

        gl = gitlab.Gitlab(url, private_token=apiKey)
        gl.auth()

        os.chdir('..')
        with open('authors.txt', 'w') as f:
            for line in output.splitlines():
                try:
                    user = gl.users.list(username=line)[0]
                    # user = gl.users.get(line)
                    f.write(line + ' = ' + user.name + ' <' + line + '@protei.ru' + '>\n')
                except:
                    f.write(line + ' = ' + line + ' <' + line + '@protei.ru' + '>\n')

        os.mkdir('git')
        os.chdir('git')

        migrationCommand = r'''svn2git ''' + inputRepo +  r''' --authors ../authors.txt --no-minimize-url -m --trunk trunk --tags tags --branches branches'''
        migration = subprocess.Popen(migrationCommand, shell=True)
        (output, err) = migration.communicate()
        print(output)
        print(err)

        group_id = gl.groups.get(group).id
        gl.projects.create({'name': project, 'namespace_id': group_id})

        remoteAddCommand = r'''git remote add origin git@git.protei.ru:''' + group + '/' + project
        remoteAdd = subprocess.Popen(remoteAddCommand, shell=True)
        (output, err) = remoteAdd.communicate()
        print(output)
        print(err)

        pushCommand = r'''git push --all origin'''
        push = subprocess.Popen(pushCommand, shell=True)
        (output, err) = push.communicate()
        print(output)
        print(err)

        pushTagsCommand = r'''git push --tags origin'''
        pushTags = subprocess.Popen(pushTagsCommand, shell=True)
        (output, err) = pushTags.communicate()
        print(output)
        print(err)

if __name__ == "__main__":
    main(sys.argv[1:])
