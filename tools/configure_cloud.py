"""Write identical public settings for desktop/mobile; never accepts admin keys."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cloud_client import CloudClient

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--publishable-key',required=True)
    parser.add_argument('--github-enabled',action='store_true')
    args=parser.parse_args()
    config={'url':args.url.rstrip('/'),'publishableKey':args.publishable_key,'githubEnabled':args.github_enabled}
    CloudClient(config)
    for relative in ['assets/cloud.json','mobile/assets/cloud.json']:
        (ROOT/relative).write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n','utf-8')
    print('Public client configuration written for desktop and Android. Rebuild both installers; deploy SQL and verify auth separately.')

if __name__=='__main__':main()
