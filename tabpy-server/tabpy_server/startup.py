import sys,subprocess,os
if sys.platform == 'win32':
    dir_path = os.path.dirname(os.path.realpath(__file__))
    if len(sys.argv) >= 2:
        subprocess.Popen(['startup.bat', sys.argv[1]],cwd=dir_path)
    else:
        subprocess.Popen(['startup.bat'],cwd=dir_path)
elif sys.platform  in ['darwin','linux2']:
    if len(sys.argv) >= 2:
        subprocess.Popen(['sh','./startup.sh', sys.argv[1]])
    else:
        subprocess.Popen(['sh','./startup.sh'])
else:
    print 'Operating system not recognized'
