import os
import glob

base = r'E:\08_Bug'
for d in os.listdir(base):
    if '3528294' in d:
        ws = os.path.join(base, d)
        print('Workspace:', ws)
        print('Exists:', os.path.isdir(ws))
        for f in os.listdir(ws):
            print(' ', f)
        break