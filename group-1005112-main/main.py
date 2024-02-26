import click
import logging
import paramiko
import yaml
import jinja2
from yaml.loader import SafeLoader

@click.command()
@click.option('-f', help='The playbook you want to run.')
@click.option('-i', help='The hosts you want your playbook to run on.')

def hello(f, i):
    """MyLittleAnsible -- Ansible copy for school project"""

    with open(i) as i:
        inventory = yaml.load(i, Loader=SafeLoader)
    
    hosts = inventory['hosts']
    
    with open(f) as f:
        playbook = yaml.load(f, Loader=SafeLoader)
    count = len(hosts) * len(playbook)
    print(list(hosts.values())[0]['ssh_address'])
    i = 0
    for command in playbook:
        if command["module"] == "apt":
            execute_module(hosts, apt_module, command)
            continue
        if command["module"] == "command":
            execute_module(hosts, command_module, command)
            continue
        if command["module"] == "copy":
            execute_module(hosts, copy_module, command)
            continue
        if command["module"] == "template":
            execute_module(hosts, template_module, command)
            continue
        if command["module"] == "service":
            execute_module(hosts, service_module, command)
            continue
        else:
            logging.warning("module not recognized")
            continue
        #logging.warning(f"[{i}] {log}")

def create_module_log(count, host, op, params):
    string = f"[{count}] host={host} op={op}"
    for key, value in params.items():
        string += ' ' + key + '=' + str(value)
    return string

def check_command_successful(stdout, stderr):
    logger = logging.getLogger("logging_tryout2")
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    if stdout.channel.recv_exit_status() != 0:
        logger.error(f"{stderr.read().decode('utf-8')}")

def execute_module(hosts, func, command):
    params = command["params"]
    for hostname, host_params in hosts.items():
        log = create_module_log('x', host_params['ssh_address'], command["module"], params)
        logging.warning(f"{log}")
        password = get_password(host_params['ssh_password'])
        client = ssh_connect(host_params['ssh_user'], password, host_params['ssh_address'])
        #print(create_module_log(hostname, command["module"], params))
        if client == -1:
            continue
        func(client, password, params)

        client.close()

def service_module(client, password, params):
    name = params["name"]
    state = params["state"]
    if state == 'started' :
        stdin, stdout, stderr = client.exec_command(f"sudo -S systemctl start {name}")
        stdin.write(f'{password}\n')
        stdin.flush()
        check_command_successful(stdout, stderr)
        return
    if state == 'restarted':
        stdin, stdout, stderr = client.exec_command(f"sudo -S systemctl restart {name}")
        stdin.write(f'{password}\n')
        stdin.flush()
        check_command_successful(stdout, stderr)
        return
    if state == 'stopped':
        stdin, stdout, stderr = client.exec_command(f"sudo -S systemctl stop {name}")
        stdin.write(f'{password}\n')
        stdin.flush()
        check_command_successful(stdout, stderr)
        return
    if state == 'enabled':
        stdin, stdout, stderr = client.exec_command(f"sudo -S systemctl enable {name}")
        stdin.write(f'{password}\n')
        stdin.flush()
        stderr.read().decode("utf-8")
        check_command_successful(stdout, stderr)
        return
    if state == 'disabled':
        stdin, stdout, stderr = client.exec_command(f"sudo -S systemctl disable {name}")
        stdin.write(f'{password}\n')
        stderr.read().decode("utf-8")
        check_command_successful(stdout, stderr)
        return
    

def template_module(client, password, params):
    src = params["src"]
    dest = params["dest"]
    template_vars = params["vars"]
    with open(src) as template_file:
        template_content = template_file.read()
        template = jinja2.Template(template_content)

    rendered_template = template.render(template_vars)
    stdin, stdout, stderr = client.exec_command(f"touch {dest} && echo \"{rendered_template}\" > {dest}")
    check_command_successful(stdout, stderr)

def apt_module(client, password, params):
    state = params["state"]
    name = params["name"]

    if state == "present":
        stdin, stdout, stderr = client.exec_command(f'sudo -S apt-get install {name} -y')
        stdin.write(f'{password}\n')
        stdin.flush()
        check_command_successful(stdout, stderr)
    if state == "absent":
        stdin, stdout, stderr = client.exec_command(f'sudo -S apt-get purge {name} -y')
        stdin.write(f'{password}\n')
        stdin.flush()
        check_command_successful(stdout, stderr)

def command_module(client, password, params):
    command = params["command"]
    shell = params.get('shell', False) or '/bin/bash'
    stdin, stdout, stderr = client.exec_command(f"{shell} -c '{command}'")
    logging.warning(stdout.read().decode("utf-8"))
    check_command_successful(stdout, stderr)

def copy_module(client, password, params):
    #TODO: Copy de dossier https://stackoverflow.com/questions/4409502/directory-transfers-with-paramiko
    src = params["src"]
    dest = params["dest"]
    backup = params.get('backup', False) or False
    if(backup):
        client.exec_command(f"mkdir -p /tmp/mla-copy && cp -R {dest} /tmp/mla-copy/")
    ftp_client = client.open_sftp()
    ftp_client.put(src, dest)
    ftp_client.close()

def ssh_connect(username, password, host_address):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host_address, username=username, password=password)
        return client
    except:
        logging.error(f"can't connect to {host_address}")
        return (-1)


def get_password(user_password):
    if user_password == "SSH_PASSWORD":
        with open('secret.yml') as f:
            secret_file = yaml.load(f, Loader=SafeLoader)
        return secret_file["SSH_PASSWORD"]
    return ''
   
if __name__ == '__main__':
    hello()