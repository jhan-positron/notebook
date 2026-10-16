import json, subprocess, sys
q = '''
query($owner:String!,$name:String!,$num:Int!,$after:String){
  repository(owner:$owner,name:$name){
    pullRequest(number:$num){
      headRefOid baseRefOid headRefName
      reviewThreads(first:100, after:$after){
        pageInfo{hasNextPage endCursor}
        nodes{
          id isResolved isOutdated isCollapsed path line startLine originalLine originalStartLine diffSide
          comments(first:50){
            nodes{ id databaseId author{login} body createdAt updatedAt replyTo{databaseId} pullRequestReview{databaseId} }
          }
        }
      }
    }
  }
}'''
after=None; threads=[]; meta=None
while True:
    args=['gh','api','graphql','-f',f'query={q}','-F','owner=positron-ai','-F','name=tron','-F','num=4868']
    if after: args += ['-F',f'after={after}']
    out=subprocess.run(args,capture_output=True,text=True)
    if out.returncode: print(out.stderr); sys.exit(1)
    d=json.loads(out.stdout)['data']['repository']['pullRequest']
    meta={k:d[k] for k in ('headRefOid','baseRefOid','headRefName')}
    rt=d['reviewThreads']; threads+=rt['nodes']
    if not rt['pageInfo']['hasNextPage']: break
    after=rt['pageInfo']['endCursor']
json.dump({'meta':meta,'threads':threads},open(sys.argv[1],'w'),indent=1)
print(meta, len(threads))
