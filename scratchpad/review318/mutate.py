import hashlib, subprocess, sys, os, shutil
ROOT="/Users/omelnikova/PycharmProjects/PythonProject4-card-318"
PY_BIN="/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
def sweep():
    for dp,dn,fn in os.walk(ROOT):
        dn[:]=[d for d in dn if d!='.git']
        for d in list(dn):
            if d=='__pycache__': shutil.rmtree(os.path.join(dp,d),ignore_errors=True); dn.remove(d)
def run(nodes):
    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r=subprocess.run([PY_BIN,"-m","pytest","-o","addopts=","-p","no:randomly","-x","--no-header","-q",*nodes],
                     cwd=ROOT,capture_output=True,text=True,env=env)
    tail=[l for l in r.stdout.strip().splitlines() if l.strip()][-1:]
    return r.returncode, (tail[0] if tail else "NO OUTPUT")
def mutant(name, path, old, new, nodes):
    full=os.path.join(ROOT,path)
    orig=open(full,encoding="utf-8").read(); h0=sha(full)
    assert old in orig, f"{name}: anchor not found"
    assert orig.count(old)==1, f"{name}: anchor not unique ({orig.count(old)})"
    sweep()
    open(full,"w",encoding="utf-8").write(orig.replace(old,new))
    try:
        rc,line=run(nodes)
    finally:
        open(full,"w",encoding="utf-8").write(orig); sweep()
        h1=sha(full)
    assert h1==h0, f"{name}: RESTORE FAILED {h0}->{h1}"
    verdict = "KILLED (test red)" if rc!=0 else "SURVIVED (test still green)"
    print(f"{name}: {verdict}  rc={rc}  sha_pre={h0[:12]} sha_post={h1[:12]} restore=ok")
    print(f"    {line}")
    return rc
if __name__=="__main__":
    pass
