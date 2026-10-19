"""Detached helper launched by preview.py through systemd-run."""
import os,subprocess,sys,time
def run(kind,mode):
    if kind not in ('video','device'):raise ValueError('Invalid restart type')
    time.sleep(3)
    os.sync()
    command=['systemctl','restart','eyesypy'] if kind=='video' else ['/sbin/reboot']
    if os.geteuid()!=0:command=['sudo','-n']+command
    subprocess.run(command,check=True,timeout=40)
if __name__=='__main__':run(*sys.argv[1:])
